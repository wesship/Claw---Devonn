# Incident Log Template

## Format

Each incident should be logged with:

```yaml
incident_id: INC-YYYY-MM-DD-NNN
timestamp: ISO8601
alert_name: Prometheus alert that triggered
severity: warning/critical/info
namespace: affected namespace
deployment: affected deployment
labels: {}  # All alert labels
actions_taken: []
result: success/failure/pending
human_involved: true/false
resolution_time_seconds: 
lessons_learned: ""
runbook_updated: false
```

## Recent Incidents

<!-- Autopilot will append incidents here -->

---

## Incident Analysis Summary

### Weekly Metrics
- Total incidents:
- Auto-remediated:
- Required human approval:
- Failed remediation:
- Average resolution time:

### Common Patterns
<!-- Track recurring issues for proactive fixes -->

### Runbook Gaps
<!-- Identify missing runbooks from novel incidents -->
