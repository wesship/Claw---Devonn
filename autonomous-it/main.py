"""
Devonn Autopilot - Autonomous IT Controller
Kubernetes self-healing with AI-driven decisions
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from kubernetes import client, config
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure structured logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("autopilot")

app = FastAPI(title="Devonn Autopilot", version="0.1.0")

# Load K8s config (in-cluster or local)
try:
    config.load_incluster_config()
    logger.info("Loaded in-cluster Kubernetes config")
except:
    config.load_kube_config()
    logger.info("Loaded local Kubernetes config")

k8s_apps = client.AppsV1Api()
k8s_core = client.CoreV1Api()

# Configuration
AUTOPILOT_MODE = os.getenv("AUTOPILOT_MODE", "mode0")  # mode0=observe, mode1=remediate
ALLOWED_ACTIONS = os.getenv("ALLOW_ALLOWED_ACTIONS", "restart,scale").split(",")
DEFAULT_NAMESPACE = os.getenv("DEFAULT_NAMESPACE", "default")
SCALE_DELTA = int(os.getenv("SCALE_DELTA_DEFAULT", "2"))
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Incident memory (would connect to OpenClaw workspace in production)
INCIDENT_LOG: List[Dict[str, Any]] = []

class Alert(BaseModel):
    """Prometheus Alertmanager alert format"""
    labels: Dict[str, str]
    annotations: Dict[str, str]
    startsAt: Optional[str] = None
    endsAt: Optional[str] = None

class AlertPayload(BaseModel):
    """Webhook payload from Alertmanager"""
    alerts: List[Alert]
    status: Optional[str] = "firing"

class ActionRequest(BaseModel):
    """Manual action request"""
    action: str = Field(..., regex="^(restart|scale)$")
    namespace: str = DEFAULT_NAMESPACE
    deployment: str
    replicas: Optional[int] = None

@app.get("/healthz")
async def health_check():
    """Kubernetes health probe"""
    return {"status": "healthy", "mode": AUTOPILOT_MODE}

@app.post("/webhook/alertmanager")
async def receive_alert(payload: AlertPayload, background_tasks: BackgroundTasks):
    """Receive alerts from Prometheus Alertmanager"""
    logger.info(f"Received {len(payload.alerts)} alerts")
    
    for alert in payload.alerts:
        background_tasks.add_task(process_alert, alert)
    
    return {"received": len(payload.alerts), "mode": AUTOPILOT_MODE}

async def process_alert(alert: Alert):
    """Process individual alert and decide action"""
    alert_name = alert.labels.get("alertname", "unknown")
    severity = alert.labels.get("severity", "warning")
    namespace = alert.labels.get("namespace", DEFAULT_NAMESPACE)
    deployment = alert.labels.get("deployment")
    
    logger.info(f"Processing alert: {alert_name} ({severity})")
    
    # Log incident
    incident = {
        "timestamp": datetime.utcnow().isoformat(),
        "alert": alert_name,
        "severity": severity,
        "namespace": namespace,
        "deployment": deployment,
        "labels": alert.labels,
        "action_taken": None
    }
    
    # Decision logic based on alert type
    if alert_name == "KubePodCrashLooping" and deployment:
        if AUTOPILOT_MODE == "mode1" and "restart" in ALLOWED_ACTIONS:
            result = await restart_deployment(namespace, deployment)
            incident["action_taken"] = f"restart: {result}"
            await notify_telegram(f"⚠️ CrashLoopBackOff in {namespace}/{deployment}\n→ Action: rollout restart\nResult: {result}")
        else:
            await notify_telegram(f"⚠️ CrashLoopBackOff in {namespace}/{deployment}\n→ Mode: {AUTOPILOT_MODE} (no auto-action)")
    
    elif alert_name == "KubePodOOMKilled" and deployment:
        if AUTOPILOT_MODE == "mode1" and "restart" in ALLOWED_ACTIONS:
            result = await restart_deployment(namespace, deployment)
            incident["action_taken"] = f"restart (OOM): {result}"
            await notify_telegram(f"💥 OOMKilled in {namespace}/{deployment}\n→ Action: restart + recommend limit increase\nResult: {result}")
        else:
            await notify_telegram(f"💥 OOMKilled in {namespace}/{deployment}\n→ Recommend: Increase memory limits")
    
    elif alert_name in ["HTTPLatencyHighP95", "HighCPUSaturation"] and deployment:
        if AUTOPILOT_MODE == "mode1" and "scale" in ALLOWED_ACTIONS:
            result = await scale_deployment(namespace, deployment, SCALE_DELTA)
            incident["action_taken"] = f"scale +{SCALE_DELTA}: {result}"
            await notify_telegram(f"📈 High load in {namespace}/{deployment}\n→ Action: scale +{SCALE_DELTA}\nResult: {result}")
        else:
            await notify_telegram(f"📈 High load in {namespace}/{deployment}\n→ Mode: {AUTOPILOT_MODE} (no auto-action)")
    
    else:
        # Unknown alert - just notify
        await notify_telegram(f"🔔 Alert: {alert_name} in {namespace}\nSeverity: {severity}\nNo automated action defined.")
    
    INCIDENT_LOG.append(incident)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def restart_deployment(namespace: str, name: str) -> str:
    """Perform rolling restart of deployment"""
    try:
        now = datetime.utcnow().isoformat()
        patch = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": now
                        }
                    }
                }
            }
        }
        k8s_apps.patch_namespaced_deployment(name=name, namespace=namespace, body=patch)
        logger.info(f"Restarted deployment {namespace}/{name}")
        return "success"
    except Exception as e:
        logger.error(f"Failed to restart {namespace}/{name}: {e}")
        return f"failed: {str(e)}"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def scale_deployment(namespace: str, name: str, delta: int) -> str:
    """Scale deployment by delta replicas"""
    try:
        # Get current replicas
        dep = k8s_apps.read_namespaced_deployment(name=name, namespace=namespace)
        current = dep.spec.replicas or 1
        new_replicas = current + delta
        
        patch = {"spec": {"replicas": new_replicas}}
        k8s_apps.patch_namespaced_deployment_scale(name=name, namespace=namespace, body=patch)
        logger.info(f"Scaled {namespace}/{name}: {current} → {new_replicas}")
        return f"scaled {current} → {new_replicas}"
    except Exception as e:
        logger.error(f"Failed to scale {namespace}/{name}: {e}")
        return f"failed: {str(e)}"

async def notify_telegram(message: str):
    """Send notification via Telegram"""
    if not TELEGRAM_ENABLED or not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.info(f"Telegram disabled. Would send: {message[:100]}...")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
            response.raise_for_status()
        logger.info("Telegram notification sent")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")

@app.post("/act")
async def manual_action(request: ActionRequest):
    """Execute manual remediation action"""
    if request.action == "restart":
        result = await restart_deployment(request.namespace, request.deployment)
    elif request.action == "scale":
        delta = request.replicas or SCALE_DELTA
        result = await scale_deployment(request.namespace, request.deployment, delta)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")
    
    return {
        "action": request.action,
        "namespace": request.namespace,
        "deployment": request.deployment,
        "result": result
    }

@app.get("/incidents")
async def list_incidents(limit: int = 50):
    """List recent incidents"""
    return {"incidents": INCIDENT_LOG[-limit:], "total": len(INCIDENT_LOG)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
