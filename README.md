# 🔮 Vigilo

**Predict Kubernetes failures before they happen. Auto-manage cluster lifecycle.**

Vigilo is an AI-powered engine that:
1. **Predicts failures** — disk full, OOM kills, cert expiry, scaling limits — days in advance
2. **Schedules clusters** — auto shutdown at night (9 PM), auto wakeup in morning (9 AM)
3. **Reports status** — full cluster inventory (nodes, pods, namespaces, Karpenter, KEDA)
4. **Alerts teams** — Microsoft Teams notifications + email reports

Install via Helm or run as CLI. Works with any EKS cluster.

---

## Quick Start

```bash
# Clone and install
git clone https://github.com/sriramg-aivar/vigilo.git
cd vigilo
pip install -r requirements.txt

# Predict failures (uses mock data — no cluster needed)
python3 main.py scan --mock

# Predict failures (real cluster)
python3 main.py scan --kubeconfig ~/.kube/config

# Cluster status
python3 main.py status

# Shutdown cluster (scale to zero)
python3 main.py shutdown --dry-run                    # preview first
python3 main.py shutdown --teams-webhook <URL>        # execute + notify

# Wake up cluster
python3 main.py wakeup --dry-run                     # preview first
python3 main.py wakeup --teams-webhook <URL>         # execute + notify

# Generate report
python3 main.py report --email devops@company.com --teams-webhook <URL>

# Predict deployment impact
python3 main.py predict-deploy --manifest deploy.yaml
```

---

## Features

### 🔮 AI Failure Prediction

Feeds cluster metrics to Claude (Bedrock) and gets back predictions with:
- **Time to failure** (hours/days)
- **Severity** (CRITICAL / WARNING / INFO)
- **Confidence level** (HIGH / MEDIUM / LOW)
- **Recommended action** (specific, actionable)
- **Cluster health score** (0-10)

| Category | What It Predicts |
|----------|-----------------|
| 💾 Disk | Node disk filling up (growth rate extrapolation) |
| 🧠 Memory | Pod approaching OOM kill (memory growth vs limit) |
| ⚡ CPU | Sustained high CPU, throttling risk |
| 🔐 Certificates | TLS cert expiring soon (flags non-auto-renewed) |
| 📈 Scaling | HPA at max replicas, can't scale further |
| 🔄 Pod Health | Increasing restart count → CrashLoopBackOff coming |
| 🌐 Scheduling | Resource exhaustion, pods can't be scheduled |
| 🚀 Deployments | Impact prediction before applying changes |

### ⏰ Cluster Scheduler (Shutdown / Wakeup)

**Shutdown (9 PM):**
1. Saves current replica counts (state file)
2. Scales all Deployments to 0
3. Scales all StatefulSets to 0
4. Pauses KEDA ScaledObjects (prevents auto-scale-up)
5. Karpenter removes empty nodes automatically
6. Sends Teams notification: "✅ Cluster shutdown complete"

**Wakeup (9 AM):**
1. Loads saved state
2. Restores all Deployments to original replicas
3. Restores StatefulSets
4. Resumes KEDA ScaledObjects
5. Karpenter provisions nodes (~2 min)
6. Pods become Ready (~3-5 min)
7. Sends Teams notification: "✅ Cluster is live"

**Safety:**
- Never touches `kube-system`, `karpenter`, `cert-manager`, `argocd`, `external-secrets`
- Saves state before shutdown — always knows how to restore
- `--dry-run` flag to preview without making changes
- `--namespace` flag to target specific namespace only

### 📊 Cluster Status

Shows full inventory at any time:
- Nodes (count, type, status, pods per node)
- Pods per namespace (running, pending, failed)
- Deployments count
- Karpenter nodepools and active nodes
- KEDA ScaledObjects (active vs paused)

### 📧 Notifications

| Channel | When |
|---------|------|
| Microsoft Teams | Shutdown complete, wakeup complete, critical predictions |
| Email (SES) | Weekly report with health score + predictions |
| PDF/Markdown | On-demand report generation |

---

## Example Output

### Prediction Scan
```
🔮 Vigilo — Scanning cluster...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📊 Cluster Score: 3.2/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Cluster has 6 predicted failures within 7 days.
  Immediate attention needed for disk and memory issues.

  🚨 CRITICAL (3)
  ────────────────────────────────────────

  [CERT] Manual Certificate Expiration Imminent
  ⏱  Time to failure: 72 hours
  📍 Affected: api-gateway-tls (gateway namespace)
  💡 Action: Immediately renew certificate

  [DISK] Node Disk Space Exhaustion
  ⏱  Time to failure: ~4 days
  📍 Affected: ip-10-0-3-91.ec2.internal
  💡 Action: Expand EBS volume or clean unused images

  [MEMORY] Payment Processor OOM Kill Imminent
  ⏱  Time to failure: ~18 hours
  📍 Affected: payment-processor (production)
  💡 Action: Increase memory limit to 1Gi

  ⚠️  WARNING (3)
  ────────────────────────────────────────

  [MEMORY] log-aggregator near OOM (96%)
  [SCALING] HPA at max replicas (4/5, CPU 82%)
  [MEMORY] Node memory pressure building (90%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total: 6 | Critical: 3 | Warning: 3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Cluster Status
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📊 Cluster: convogent-production
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🖥  Nodes: 5 total | 5 ready | 0 not ready
  ────────────────────────────────────────
  • core-node-1 (m5.large) — Ready — 12 pods
  • karpenter-dev-1 (c6a.xlarge) — Ready — 8 pods
  • karpenter-dev-2 (c6a.xlarge) — Ready — 6 pods
  • karpenter-voice-1 (c6in.xlarge) — Ready — 3 pods
  • karpenter-monitoring-1 (t4g.large) — Ready — 9 pods

  📦 Namespaces:
  ────────────────────────────────────────
  • convogent: 6 deployments, 14 pods running
  • monitoring: 4 deployments, 9 pods running
  • kube-system: 3 deployments, 12 pods running

  🚀 Karpenter: 4 nodes across 6 pools
  ⚡ KEDA: 6 active / 0 paused ScaledObjects

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Shutdown (Dry Run)
```
🌙 Vigilo — Initiating cluster shutdown...

  1. Save current replica counts to state file
  2. Scale deployments to 0:
     • convogent-frontend (2 → 0)
     • convogent-backend (2 → 0)
     • convogent-chat-service (2 → 0)
     • convogent-eval-service (1 → 0)
     • convogent-pca-service (1 → 0)
     • convogent-voice-service (3 → 0)
  3. Scale StatefulSets to 0: livekit-server (3 → 0)
  4. Pause KEDA ScaledObjects
  5. Karpenter removes empty nodes
  6. Teams notification: 'Cluster shutdown complete'
```

### Wakeup (Dry Run)
```
☀️ Vigilo — Waking up cluster...

  1. Load saved state from state file
  2. Restore deployments to original replicas:
     • convogent-frontend (0 → 2)
     • convogent-backend (0 → 2)
     • convogent-chat-service (0 → 2)
     • convogent-eval-service (0 → 1)
     • convogent-pca-service (0 → 1)
     • convogent-voice-service (0 → 3)
  3. Restore StatefulSets: livekit-server (0 → 3)
  4. Resume KEDA ScaledObjects
  5. Karpenter provisions nodes (~2 min)
  6. Wait for pods Ready (~3-5 min)
  7. Teams notification: 'Cluster is live'
```

---

## Installation

### Option 1: CLI (pip)

```bash
pip install -r requirements.txt
python3 main.py scan --kubeconfig ~/.kube/config
```

### Option 2: Helm Chart (In-Cluster CronJob)

```bash
helm repo add vigilo https://aivar-tech.github.io/vigilo
helm install vigilo vigilo/vigilo \
  --namespace vigilo \
  --create-namespace \
  --set aws.region=us-east-1 \
  --set notifications.teamsWebhook="https://outlook.office.com/webhook/xxx" \
  --set schedule.shutdown="0 21 * * *" \
  --set schedule.wakeup="0 9 * * MON-FRI" \
  --set schedule.scan="0 */6 * * *"
```

### Option 3: Docker

```bash
docker run --rm \
  -v ~/.kube/config:/root/.kube/config \
  -v ~/.aws:/root/.aws \
  aivar/vigilo scan
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_DEFAULT_REGION` | Yes | AWS region for Bedrock (default: us-east-1) |
| `AWS_ACCESS_KEY_ID` | Yes* | AWS credentials (*or use IAM role) |
| `AWS_SECRET_ACCESS_KEY` | Yes* | AWS credentials |
| `KUBECONFIG` | No | Path to kubeconfig (default: ~/.kube/config) |
| `VIGILO_MODEL_ID` | No | Bedrock model (default: us.anthropic.claude-sonnet-4-20250514-v1:0) |
| `TEAMS_WEBHOOK_URL` | No | Microsoft Teams webhook URL |
| `SES_SENDER` | No | Email sender (for reports) |

### Helm Values

```yaml
aws:
  region: us-east-1

notifications:
  teamsWebhook: "https://outlook.office.com/webhook/your-url"
  email: devops@yourcompany.com

schedule:
  shutdown: "0 21 * * *"          # 9 PM daily
  wakeup: "0 9 * * MON-FRI"      # 9 AM weekdays only
  scan: "0 */6 * * *"            # Every 6 hours
  report: "0 9 * * MON"          # Weekly Monday 9 AM

scheduler:
  namespace: "convogent"           # Target namespace (empty = all app namespaces)
  protectedNamespaces:
    - kube-system
    - karpenter
    - cert-manager
    - argocd
    - external-secrets

thresholds:
  disk_warn_percent: 80
  disk_critical_percent: 90
  memory_warn_percent: 85
  memory_critical_percent: 95
  cert_warn_days: 14
  cert_critical_days: 7
```

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Your EKS Cluster                        │
│                                                     │
│  ┌───────────────────────────────────────────┐      │
│  │     Vigilo (CronJob/Pod)       │      │
│  │                                           │      │
│  │  ┌────────────┐  ┌────────────────────┐   │      │
│  │  │ Collector  │  │    Predictor       │   │      │
│  │  │ (K8s API)  │→ │ (Bedrock/Claude)   │   │      │
│  │  └────────────┘  └─────────┬──────────┘   │      │
│  │                            │              │      │
│  │  ┌────────────┐  ┌────────┴───────────┐   │      │
│  │  │ Scheduler  │  │     Reporter       │   │      │
│  │  │ (shutdown/ │  │ (Teams/Email/PDF)  │   │      │
│  │  │  wakeup)   │  └────────┬───────────┘   │      │
│  │  └─────┬──────┘           │              │      │
│  └────────┼──────────────────┼──────────────┘      │
│           │                  │                     │
│           ▼                  ▼                     │
│  ┌────────────────┐  ┌──────────────┐             │
│  │ Deployments    │  │   Karpenter  │             │
│  │ StatefulSets   │  │   (nodes)    │             │
│  │ KEDA           │  │              │             │
│  └────────────────┘  └──────────────┘             │
└─────────────────────────────────────────────────────┘
              │                  │
              ▼                  ▼
       ┌──────────┐      ┌──────────┐
       │  Teams   │      │  Email   │
       │(Webhook) │      │  (SES)   │
       └──────────┘      └──────────┘
```

---

## How Predictions Work

1. **Collect** — Pull live metrics from K8s API (nodes, pods, events, certs, HPA, KEDA)
2. **Trend** — Calculate growth rates and trajectories
3. **Predict** — Feed to Claude (Bedrock) for AI analysis
4. **Score** — Generate cluster health score (0-10) with confidence levels
5. **Alert** — Send critical predictions to Teams/email immediately
6. **Report** — Weekly PDF with all predictions and actions

---

## Cluster Scheduler: How It Saves Money

| Time | What Happens | Nodes | Cost |
|------|-------------|-------|------|
| 9 AM | Wakeup → all pods restored, Karpenter provisions nodes | 5 | Full |
| 9 PM | Shutdown → all pods scaled to 0, nodes terminate | 1 (core only) | ~80% savings |

**Example savings (Convogent Bank cluster):**
- 4 Karpenter nodes × ~$0.60/hr = $2.40/hr
- 12 hours/night × $2.40 = **$28.80/night**
- 30 days = **$864/month saved per cluster**

For 3 non-prod clusters = **$2,592/month saved**

---

## Compatibility

| Component | Supported |
|-----------|-----------|
| EKS | ✅ (primary target) |
| Karpenter | ✅ (auto node removal on shutdown) |
| KEDA | ✅ (pause/resume ScaledObjects) |
| HPA | ✅ (tracked in predictions) |
| ArgoCD | ✅ (protected namespace, not touched) |
| cert-manager | ✅ (protected namespace) |
| Any K8s cluster | ✅ (predictions work everywhere) |

---

## Development

```bash
# Clone
git clone https://github.com/sriramg-aivar/vigilo.git
cd vigilo

# Install
pip install -r requirements.txt

# Test prediction (no cluster needed)
python3 main.py scan --mock

# Test scheduler (no cluster needed)
python3 main.py shutdown --dry-run
python3 main.py wakeup --dry-run
python3 main.py status

# Run tests
pytest tests/
```

---

## Roadmap

| Phase | Features | Status |
|-------|----------|--------|
| v0.1 | Prediction engine + CLI + scheduler + Teams | ✅ Done |
| v0.2 | Real K8s cluster integration | 🔄 Next |
| v0.3 | Helm chart + CronJob deployment | Planned |
| v0.4 | Email reports (SES) + PDF | Planned |
| v0.5 | Deployment impact prediction | Planned |
| v1.0 | Production release | Planned |

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| Python 3.10+ | Runtime |
| AWS Bedrock access | Claude for predictions |
| EKS cluster | Metrics source + scheduler target |
| kubectl configured | Cluster access |
| Teams webhook (optional) | Notifications |

---

## License

Internal — Aivar Innovations
