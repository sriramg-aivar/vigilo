# 🔮 Vigilo

**Predict Kubernetes failures before they happen.**

Vigilo is an AI-powered engine that:
1. **Predicts failures** — disk full, OOM kills, cert expiry, scaling limits — days in advance
2. **Reports status** — full cluster inventory (nodes, pods, namespaces, Karpenter, KEDA)
3. **Alerts teams** — Microsoft Teams notifications with Error/Fix/Prevent format

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
| Microsoft Teams | Critical predictions, health reports (Error/Fix/Prevent format) |
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
  --set schedule.scan="0 */6 * * *" \
  --set schedule.report="0 9 * * MON"
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
  scan: "0 */6 * * *"            # Every 6 hours
  report: "0 9 * * MON"          # Weekly Monday 9 AM

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
│  │        Vigilo (CronJob/Pod)               │      │
│  │                                           │      │
│  │  ┌────────────┐  ┌────────────────────┐   │      │
│  │  │ Collector  │  │    Predictor       │   │      │
│  │  │ (K8s API)  │→ │ (Bedrock/Claude)   │   │      │
│  │  └────────────┘  └─────────┬──────────┘   │      │
│  │                            │              │      │
│  │                   ┌────────┴───────────┐   │      │
│  │                   │     Reporter       │   │      │
│  │                   │ (Teams/Email/PDF)  │   │      │
│  │                   └────────┬───────────┘   │      │
│  └────────────────────────────┼──────────────┘      │
│                               │                     │
│                               ▼                     │
│                      ┌──────────────┐               │
│                      │   Karpenter  │               │
│                      │   (nodes)    │               │
│                      └──────────────┘               │
└─────────────────────────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  Teams / Email   │
                    │  (Notifications) │
                    └──────────────────┘
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

## Scripts

| Script | Purpose |
|--------|---------|
| `setup.sh` | Create/resume EKS test cluster + deploy dummy services |
| `scale-to-zero.sh` | Scale all node groups to 0 (cost savings for non-prod) |
| `destroy.sh` | Tear down the test cluster |

```bash
# Set up the test cluster
./setup.sh

# Scale to zero at night (saves ~$28/night per cluster)
./scale-to-zero.sh

# Bring it back
./setup.sh
```

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `scan` | Run AI failure prediction scan |
| `predict-deploy` | Predict impact of a deployment manifest before applying |
| `report` | Generate health report (email + Teams) |
| `status` | Show full cluster inventory |

```bash
python3 main.py scan --mock                           # test without cluster
python3 main.py scan --kubeconfig ~/.kube/config      # real cluster
python3 main.py predict-deploy --manifest deploy.yaml # deployment impact
python3 main.py report --teams-webhook <URL>          # generate report
python3 main.py status                                # cluster inventory
```

---

## Compatibility

| Component | Supported |
|-----------|-----------|
| EKS | ✅ (primary target) |
| Karpenter | ✅ (tracked in predictions) |
| KEDA | ✅ (tracked in predictions) |
| HPA | ✅ (tracked in predictions) |
| ArgoCD | ✅ (compatible) |
| cert-manager | ✅ (cert expiry predictions) |
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

# Cluster status
python3 main.py status

# Run tests
pytest tests/
```

---

## Roadmap

| Phase | Features | Status |
|-------|----------|--------|
| v0.1 | Prediction engine + CLI + Teams | ✅ Done |
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
| EKS cluster | Metrics source |
| kubectl configured | Cluster access |
| Teams webhook (optional) | Notifications |

---

## License

Internal — Aivar Innovations
