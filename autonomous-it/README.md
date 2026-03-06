# Devonn Autonomous IT v1

Self-healing Kubernetes infrastructure with AI-driven incident response.

## Architecture

```
┌─────────────────────────────────────────┐
│  Prometheus (Metrics + Alerts)          │
└──────────────┬──────────────────────────┘
               │ webhook
┌──────────────▼──────────────────────────┐
│  Alertmanager                           │
└──────────────┬──────────────────────────┘
               │ POST /webhook/alertmanager
┌──────────────▼──────────────────────────┐
│  Devonn Autopilot (FastAPI)             │
│  ├─ Decision engine                     │
│  ├─ K8s API client                      │
│  └─ Telegram notifier                   │
└──────────────┬──────────────────────────┘
               │ kubectl / API
┌──────────────▼──────────────────────────┐
│  Kubernetes (Remediation actions)       │
└─────────────────────────────────────────┘
```

## Quick Start

### 1. Configure Secrets
Edit `devonn-autopilot-secret.yaml`:
```yaml
TELEGRAM_BOT_TOKEN: "your-bot-token"
TELEGRAM_CHAT_ID: "your-chat-id"
```

Get these from @BotFather (token) and your Telegram chat (ID).

### 2. Deploy
```bash
# Create namespace
kubectl create namespace devonn-autopilot

# Apply manifests
kubectl apply -f devonn-autopilot-secret.yaml
kubectl apply -f devonn-autopilot-config.yaml
kubectl apply -f devonn-autopilot-rbac.yaml
kubectl apply -f devonn-autopilot-deploy.yaml

# Verify
kubectl -n devonn-autopilot get pods
kubectl -n devonn-autopilot logs -f deploy/devonn-autopilot
```

### 3. Configure Alertmanager
Add to your Alertmanager config:
```yaml
receivers:
  - name: devonn-autopilot
    webhook_configs:
      - url: http://devonn-autopilot.devonn-autopilot.svc.cluster.local:8000/webhook/alertmanager
        send_resolved: true

route:
  routes:
    - matchers:
        - severity=~"warning|critical"
      receiver: devonn-autopilot
```

### 4. Add Prometheus Rules
```bash
kubectl apply -f prometheus-rules.yaml
```

## Modes of Operation

| Mode | Description | Actions |
|------|-------------|---------|
| mode0 | Observe only | Notify only, no remediation |
| mode1 | Safe auto-remediate | Restart, scale (with guardrails) |
| mode2+ | Approval required | Human in loop for destructive actions |

Set via ConfigMap: `AUTOPILOT_MODE: "mode1"`

## Day-One Runbooks

See [RUNBOOKS.md](RUNBOOKS.md) for detailed procedures.

### Autonomous (Mode 1)
1. CrashLoopBackOff → restart deployment
2. OOMKilled → restart + notify
3. High latency → scale +2
4. High CPU → scale +2

### Approval Required
5. High 5xx → suggest rollback
6. Node pressure → suggest cordon/drain
7. Disk pressure → suggest cleanup
8. Security anomaly → suggest isolate
9. Terraform changes → never autonomous

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/healthz` | GET | Health probe |
| `/webhook/alertmanager` | POST | Receive alerts |
| `/act` | POST | Manual action |
| `/incidents` | GET | List incidents |

## Monitoring Integration

The Monitoring Agent (MyClaw) connects to this system via:
- Incident log queries (`/incidents`)
- Manual remediation triggers (`/act`)
- Policy validation and escalation

## Security Considerations

1. **RBAC**: Least-privilege ServiceAccount (restart/scale only)
2. **Network**: Internal cluster communication only
3. **Secrets**: Kubernetes Secrets for sensitive data
4. **Validation**: All actions logged, rate-limited
5. **Policy**: See `policy.yaml` for allowlists

## Cost Optimization

Integrated with Kubecost and Cloud Custodian:
- Detect idle resources
- Auto-stop non-production workloads
- Right-sizing recommendations

## Next Steps

1. Build and push image: `docker build -t ghcr.io/your-org/devonn-autopilot:0.1.0 .`
2. Configure deployment-specific alerts with labels
3. Test in staging environment
4. Gradually enable Mode 1 for safe runbooks
5. Integrate with MyClaw agent team for complex incidents
