# Autonomous IT Runbooks

## Day-One Automated Runbooks (Mode 1)

### RB-001: CrashLoopBackOff
**Trigger:** `KubePodCrashLooping` alert
**Severity:** warning
**Autonomous Action:** ✅ YES

```
Detection: Pod in CrashLoopBackOff state > 2 minutes
Decision: Transient error likely
Action: kubectl rollout restart deployment/<name>
Verification: Check pod status after 60s
Escalation: If still failing after 3 restarts → Page on-call
```

### RB-002: OOMKilled
**Trigger:** `KubePodOOMKilled` alert
**Severity:** warning
**Autonomous Action:** ✅ YES (with notification)

```
Detection: Container terminated with OOMKilled reason
Decision: Memory limit too low
Action: Restart deployment + notify "increase memory limits"
Follow-up: Recommend new limit based on usage metrics
```

### RB-003: High Latency P95
**Trigger:** `HTTPLatencyHighP95` alert
**Severity:** warning
**Autonomous Action:** ✅ YES

```
Detection: p95 latency > 1s for 3 minutes
Decision: Load-related slowdown
Action: Scale deployment +2 replicas
Verification: Monitor latency for 5 minutes post-scale
Rollback: If no improvement, scale back down
```

### RB-004: High CPU Saturation
**Trigger:** Custom CPU threshold alert
**Severity:** warning
**Autonomous Action:** ✅ YES

```
Detection: CPU utilization > 80% for 5 minutes
Decision: Capacity constraint
Action: Scale deployment +2 replicas
Limit: Max 20 replicas per deployment
```

---

## Approval-Required Runbooks (Mode 1)

### RB-005: High 5xx Error Rate
**Trigger:** `HTTP5xxHigh` alert
**Severity:** critical
**Autonomous Action:** ❌ NO (dry-run only)

```
Detection: > 5 errors/second for 2 minutes
Decision: Application-level failure
Suggested Action: Rollback to previous version
Human Required: Approve rollback via Telegram/command
Safety: Show current vs previous version diff
```

### RB-006: Node Memory Pressure
**Trigger:** `NodeMemoryPressure` alert
**Severity:** critical
**Autonomous Action:** ❌ NO

```
Detection: Node reporting MemoryPressure condition
Suggested Actions:
  1. Cordon node (prevent new pods)
  2. Drain workloads to other nodes
  3. Investigate memory leaks
Human Required: Approve cordon/drain
Risk: Workload disruption during drain
```

### RB-007: Node Disk Pressure
**Trigger:** `NodeDiskPressure` alert
**Severity:** critical
**Autonomous Action:** ❌ NO

```
Detection: Node disk > 85% full
Suggested Actions:
  1. Clean old container logs/images
  2. Expand EBS volume
  3. Add new node and migrate
Human Required: Choose and approve action
```

### RB-008: Security Anomaly
**Trigger:** Falco/Wazuh alert
**Severity:** critical
**Autonomous Action:** ❌ NO

```
Detection: Suspicious container activity
Suggested Actions:
  1. Isolate container (network policy)
  2. Capture forensic snapshot
  3. Alert security team
Human Required: All actions
Compliance: Document all containment steps
```

### RB-009: Terraform Drift
**Trigger:** Scheduled drift detection
**Severity:** warning
**Autonomous Action:** ❌ NO

```
Detection: Infrastructure differs from Terraform state
Suggested Action: terraform plan (show changes)
Human Required: Review and approve apply
Safety: Never auto-apply infrastructure changes
```

---

## Incident Response Flowchart

```
Alert Received
     ↓
Classify Severity
     ↓
Check Runbook Exists?
     ↓
   YES → Check Mode
   NO  → Notify + Log (no action)
     ↓
Mode 0 (Observe) → Notify Only
Mode 1 (Remediate) → Check Allowlist
     ↓
In Allowlist? → Execute Action
Not Allowed? → Suggest + Request Approval
     ↓
Verify Result → Update Incident Log
     ↓
Notify via Telegram
```

---

## Escalation Matrix

| Scenario | First Response | Escalation Timer | Escalation Target |
|----------|---------------|------------------|-------------------|
| Auto-remediation fails | Retry 2x | 10 minutes | On-call engineer |
| Unknown alert type | Log + notify | Immediate | Platform team |
| Security event | Contain (if approved) | 5 minutes | Security team |
| Multiple simultaneous alerts | Prioritize by severity | 15 minutes | Incident commander |
