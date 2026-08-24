# Vigilo — Test Cases

## How to Run Tests

```bash
# Prerequisites
export AWS_ACCESS_KEY_ID="<cloud-migration-key>"       # 880335327306
export AWS_SECRET_ACCESS_KEY="<cloud-migration-secret>"
export AWS_SESSION_TOKEN="<cloud-migration-token>"
export BEDROCK_AWS_ACCESS_KEY_ID="<bedrock-key>"       # 283744739430
export BEDROCK_AWS_SECRET_ACCESS_KEY="<bedrock-secret>"
export BEDROCK_AWS_SESSION_TOKEN="<bedrock-token>"
export TEAMS_WEBHOOK="<your-teams-webhook-url>"

# Bring cluster up
./setup.sh

# Run tests
python3 main.py scan                              # real cluster
python3 main.py scan --mock                       # mock data
python3 main.py report --teams-webhook $TEAMS_WEBHOOK  # real + Teams
python3 main.py status                            # cluster inventory
```

---

## Test Case 1: Healthy Cluster Scan (Real)

**Scenario:** Fresh cluster with nginx pods, no real load, no issues.

**Command:**
```bash
python3 main.py scan
```

**Expected Output:**
```
📊 Cluster Score: 6-8/10

Predictions:
- ⚠️ No HPA configured (all deployments static replicas)
- ⚠️ No resource quotas defined
- ⚠️ Only 2 nodes (no N+1 redundancy)
- ℹ️ No monitoring stack installed
```

**Expected Teams Message:**
```
🔮 Vigilo — Cluster Health Report

📊 Score: 6.5/10
🏗️ Cluster: arn:aws:eks:us-east-1:880335327306:cluster/vigilo-test
🌐 Region: us-east-1
🖥️ Nodes: 2
🚨 Critical: 1-2
⚠️ Warnings: 3-4
🕐 Report Time: 2026-08-25 04:00 UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 [SCALING] Cluster Has Zero Headroom for Failures
⏱️ Error: Failure immediate upon node failure — Entire cluster
🔧 Fix: Add a 3rd t3.medium node for N+1 redundancy.
🛡️ Prevent: Enable cluster autoscaler with min 3, max 6 nodes.

⚠️ [SCALING] No HPA Configured
⏱️ Error: Failure in 48-96 hours — convogent namespace
🔧 Fix: Implement HPA for frontend, backend, voice-service with target CPU 70%.
🛡️ Prevent: Add HPA as part of deployment template for all services.
```

---

## Test Case 2: Mock Data Scan (Simulated Production Issues)

**Scenario:** Mock data simulates a production cluster with disk filling, OOM pods, cert expiring.

**Command:**
```bash
python3 main.py scan --mock
```

**Expected Output:**
```
📊 Cluster Score: 3-5/10

Predictions (11-12 total):
- 🚨 CRITICAL: Disk exhaustion in 4 days (node ip-10-0-3-91, 84% → growing 1.8Gi/day)
- 🚨 CRITICAL: Payment processor OOM in 18 hours (680Mi/768Mi, growing 5Mi/hr)
- 🚨 CRITICAL: Log aggregator OOM in 7 hours (490Mi/512Mi, growing 3Mi/hr)
- 🚨 CRITICAL: TLS cert expires in 3 days (api-gateway-tls, auto-renew OFF)
- 🚨 CRITICAL: HPA maxed out (4/5 replicas, CPU 82%)
- 🚨 CRITICAL: Scheduling failures (5 events in 6 hours)
- ⚠️ WARNING: Node ip-10-0-1-42 disk at 78%
- ⚠️ WARNING: Redis cache at 85% memory
- ⚠️ WARNING: Node CPU at 90%
- ⚠️ WARNING: Node memory pressure (90%)
- ⚠️ WARNING: Pod restart pattern (3 restarts in 7 days)
- ⚠️ WARNING: Namespace quota at 84%
```

**Expected Teams Message:**
```
🔮 Vigilo — Cluster Health Report

📊 Score: 4.2/10
🏗️ Cluster: aivar-production-eks
🌐 Region: us-east-1
🖥️ Nodes: 3
🚨 Critical: 5-6
⚠️ Warnings: 5-6
🕐 Report Time: <current time> UTC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚨 [DISK] Node disk exhaustion imminent
⏱️ Error: Failure in 4.4 days — ip-10-0-3-91.ec2.internal
🔧 Fix: Clean up unused images/logs or expand disk volume to 100Gi.
🛡️ Prevent: Add disk monitoring alerts at 85% threshold.

🚨 [MEMORY] Payment processor OOM kill imminent
⏱️ Error: Failure in 18 hours — payment-processor-7d4f8b6c9-x2k4m (production)
🔧 Fix: Increase memory limit to 1.5Gi immediately.
🛡️ Prevent: Investigate memory leak in v2.4.1, add memory profiling.

🚨 [CERT] TLS certificate expiring
⏱️ Error: Failure in 3 days — api-gateway-tls (gateway namespace)
🔧 Fix: Manually renew certificate immediately.
🛡️ Prevent: Enable auto-renewal with cert-manager.

🚨 [SCALING] HPA at maximum capacity
⏱️ Error: Already occurring — payment-processor HPA (production)
🔧 Fix: Increase max_replicas to 10.
🛡️ Prevent: Add more nodes and enable cluster autoscaler.
```

---

## Test Case 3: Teams Notification Delivery

**Scenario:** Verify report is delivered to Teams with full context.

**Command:**
```bash
python3 main.py report --mock --teams-webhook $TEAMS_WEBHOOK
```

**Expected:**
- ✅ Message appears in Teams channel within 5 seconds
- ✅ Contains cluster name, region, node count, time
- ✅ Each prediction has Error / Fix / Prevent format
- ✅ Severity icons (🚨 / ⚠️) visible
- ✅ Copy-pasteable to Claude/Kiro for remediation

---

## Test Case 4: Cluster Status (Real)

**Scenario:** Check live cluster inventory.

**Command:**
```bash
python3 main.py status
```

**Expected Output:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📊 Cluster: arn:aws:eks:us-east-1:880335327306:cluster/vigilo-test
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🖥  Nodes: 2 total | 2 ready | 0 not ready
  ────────────────────────────────────────
  • ip-192-168-57-20.ec2.internal (t3.medium) — Ready — 11 pods
  • ip-192-168-6-46.ec2.internal (t3.medium) — Ready — 6 pods

  📦 Namespaces:
  ────────────────────────────────────────
  • convogent: 6 deployments, 11 pods running
  • kube-system: 3 deployments, 6 pods running

  🚀 Karpenter: Not installed
  ⚡ KEDA: Not installed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Test Case 5: Scale to Zero + Bring Back

**Scenario:** Scale nodes to 0, then bring back with setup.sh.

**Scale Down:**
```bash
./scale-to-zero.sh
```

**Expected:**
```
🌙 Scaling cluster nodes to ZERO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Account: 880335327306
📋 Finding node groups...
   Found: core
   📉 core: 2 → 0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ All node groups scaled to 0.
```

**Bring Back:**
```bash
./setup.sh
```

**Expected:**
```
🟢 SETTING UP EKS cluster: vigilo-test (us-east-1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Cluster already exists and is ACTIVE.
⚠️  Nodes are scaled to 0. Scaling up to 2...
   ⏳ Waiting for nodes to join (~2 min)...
   Nodes:
   ip-xxx.ec2.internal   Ready
   ip-xxx.ec2.internal   Ready
✅ Namespace 'convogent' exists.
   Pods: 11
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ SETUP COMPLETE
```

---

## Test Case 6: Dry Run (No AI Call)

**Scenario:** Test output format without Bedrock cost.

**Command:**
```bash
python3 main.py scan --mock --dry-run
```

**Expected:** Uses sample predictions, no Bedrock call, shows formatted output.

---

## Test Case 7: JSON Output

**Scenario:** Export predictions as JSON for programmatic use.

**Command:**
```bash
python3 main.py scan --mock --output json --output-file predictions.json
```

**Expected:** `predictions.json` contains valid JSON with `cluster_score`, `predictions[]` array, each with `severity`, `category`, `title`, `time_to_failure`, `recommended_action`.

---

## Test Case 8: PDF/Markdown Report Generation

**Scenario:** Generate report file.

**Command:**
```bash
python3 main.py scan --mock --output pdf --output-file vigilo-report.pdf
```

**Expected:** `vigilo-report.md` created with full table of predictions, detailed breakdown, and footer.

---

## Test Case 9: Cross-Account Credentials

**Scenario:** kubectl uses Cloud Migration (880335327306), Bedrock uses Aivar Agents (283744739430).

**Command:**
```bash
export AWS_ACCESS_KEY_ID="<cloud-migration>"
export BEDROCK_AWS_ACCESS_KEY_ID="<bedrock-account>"
python3 main.py scan
```

**Expected:**
- ✅ kubectl connects to vigilo-test (880335327306)
- ✅ Bedrock calls Claude in 283744739430
- ✅ No cross-account errors

---

## Test Case 10: Destroy and Recreate

**Scenario:** Full lifecycle test.

**Steps:**
```bash
./destroy.sh          # Type 'destroy' to confirm
# Wait 10-15 min
./setup.sh            # Creates everything from scratch
python3 main.py scan  # Verify working
```

**Expected:** Complete cluster destroyed, fresh cluster created, Vigilo works on fresh cluster.

---

## Verification Checklist

| # | Test | Pass Criteria |
|---|------|---------------|
| 1 | Real cluster scan | Score + predictions returned |
| 2 | Mock data scan | 10+ predictions generated |
| 3 | Teams notification | Message appears in channel |
| 4 | Cluster status | Nodes + pods listed |
| 5 | Scale to zero + back | Nodes 2→0→2, pods restored |
| 6 | Dry run | No Bedrock call, sample output |
| 7 | JSON output | Valid JSON file created |
| 8 | PDF/Markdown report | File created with predictions |
| 9 | Cross-account | Both accounts used correctly |
| 10 | Destroy + recreate | Full lifecycle works |
