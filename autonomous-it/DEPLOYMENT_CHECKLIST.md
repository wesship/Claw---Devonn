# Devonn Autopilot - Deployment Checklist

## Pre-Deployment

### Infrastructure Requirements
- [ ] Kubernetes cluster (1.24+)
- [ ] Prometheus + Alertmanager installed
- [ ] Container registry access (GHCR, ECR, or private)
- [ ] Telegram bot created (@BotFather)
- [ ] Chat ID identified for notifications

### Security Review
- [ ] RBAC policies reviewed (restart/scale only)
- [ ] Network policies configured
- [ ] Secrets management validated
- [ ] Image scanning enabled in CI/CD

## Phase 1: Build & Push Image

```bash
# Login to registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin

# Build
docker build -t ghcr.io/YOUR_ORG/devonn-autopilot:0.1.0 .

# Push
docker push ghcr.io/YOUR_ORG/devonn-autopilot:0.1.0
```

- [ ] Image builds successfully
- [ ] Image pushed to registry
- [ ] Image pullable from cluster

## Phase 2: Namespace & Secrets

```bash
kubectl create namespace devonn-autopilot
kubectl apply -f devonn-autopilot-secret.yaml
kubectl apply -f devonn-autopilot-config.yaml
```

- [ ] Namespace created
- [ ] Secrets applied (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID set)
- [ ] ConfigMap applied (AUTOPILOT_MODE=mode0 initially)

## Phase 3: RBAC & Deployment

```bash
kubectl apply -f devonn-autopilot-rbac.yaml
kubectl apply -f devonn-autopilot-deploy.yaml
```

- [ ] ServiceAccount created
- [ ] Role/RoleBinding applied
- [ ] Deployment running
- [ ] Pod status: Running
- [ ] Service accessible

## Phase 4: Health Verification

```bash
# Port forward for testing
kubectl -n devonn-autopilot port-forward svc/devonn-autopilot 8000:8000

# Test health endpoint
curl http://localhost:8000/healthz

# Expected: {"status": "healthy", "mode": "mode0"}
```

- [ ] /healthz returns 200
- [ ] Logs show successful startup
- [ ] No error messages in logs

## Phase 5: Telegram Integration

```bash
# Test notification manually
curl -X POST http://localhost:8000/webhook/alertmanager \
  -H "Content-Type: application/json" \
  -d '{
    "alerts": [{
      "labels": {
        "alertname": "TestAlert",
        "severity": "warning",
        "namespace": "default",
        "deployment": "test"
      },
      "annotations": {
        "summary": "Test alert for Telegram integration"
      }
    }]
  }'
```

- [ ] Telegram message received
- [ ] Message format correct
- [ ] No delivery errors in logs

## Phase 6: Alertmanager Integration

Add to Alertmanager config:
```yaml
receivers:
  - name: devonn-autopilot
    webhook_configs:
      - url: http://devonn-autopilot.devonn-autopilot.svc.cluster.local:8000/webhook/alertmanager
        send_resolved: true
```

- [ ] Alertmanager config updated
- [ ] Config reloaded successfully
- [ ] Webhook reachable from Alertmanager

## Phase 7: Prometheus Rules

```bash
kubectl apply -f prometheus-rules.yaml
```

- [ ] Rules loaded in Prometheus
- [ ] Alerts visible in Prometheus UI
- [ ] No rule syntax errors

## Phase 8: Staging Test (Mode 0)

Set `AUTOPILOT_MODE: "mode0"` (observe only)

Trigger test alerts:
- [ ] CrashLoopBackOff simulation
- [ ] High latency simulation
- [ ] Verify notifications received
- [ ] Verify NO automatic actions taken
- [ ] Incident log populated

## Phase 9: Enable Mode 1 (Safe Auto-Remediate)

```bash
kubectl edit configmap devonn-autopilot-config -n devonn-autopilot
# Change AUTOPILOT_MODE to "mode1"
kubectl rollout restart deployment/devonn-autopilot -n devonn-autopilot
```

- [ ] ConfigMap updated
- [ ] Deployment restarted
- [ ] Health check passes

## Phase 10: Production Validation

Controlled chaos tests:
- [ ] Induce pod crash → verify restart
- [ ] Simulate high load → verify scale
- [ ] Verify cooldown periods work
- [ ] Verify rate limiting active
- [ ] Check incident log accuracy

## Post-Deployment

### Documentation
- [ ] Runbooks updated with actual procedures
- [ ] On-call rotation informed
- [ ] Escalation paths documented

### Monitoring
- [ ] Autopilot metrics exposed
- [ ] Dashboard created in Grafana
- [ ] Alerts for Autopilot itself configured

### MyClaw Integration
- [ ] Monitoring agent can query incidents
- [ ] Main agent can spawn remediation
- [ ] Policy validation working

## Rollback Plan

If issues detected:
```bash
# Immediate rollback to mode0
kubectl patch configmap devonn-autopilot-config -n devonn-autopilot \
  --type merge -p '{"data":{"AUTOPILOT_MODE":"mode0"}}'
kubectl rollout restart deployment/devonn-autopilot -n devonn-autopilot

# Or full removal
kubectl delete namespace devonn-autopilot
```

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| DevOps Lead | | | |
| Security Reviewer | | | |
| SRE On-call | | | |
