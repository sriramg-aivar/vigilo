# 🔮 Kubogent Prophecy

**Predict Kubernetes failures before they happen.**

Kubogent Prophecy is an AI-powered engine that runs inside your Kubernetes cluster, analyzes resource trends, and predicts failures days before they occur. Get weekly reports via email and real-time alerts on Microsoft Teams.

---

## What It Does

| Feature | Description |
|---------|-------------|
| **Failure Prediction** | Predicts disk full, OOM kills, cert expiry, scaling limits — days in advance |
| **Deployment Impact** | Before you deploy, know the impact: resource changes, eviction risks, conflicts |
| **Weekly Reports** | PDF/email report with cluster health score and predictions |
| **Real-time Alerts** | Microsoft Teams notifications when critical predictions are detected |
| **CLI Scan** | One command to scan your cluster and see predictions |

---

## Quick Start

### Option 1: CLI (One-time Scan)

```bash
# Clone and install
git clone https://github.com/aivar-tech/kubogent-prophecy.git
cd kubogent-prophecy
pip install -r requirements.txt

# Scan your cluster (uses current kubeconfig context)
python main.py scan --kubeconfig ~/.kube/config

# Scan with mock data (for testing without cluster access)
python main.py scan --mock

# Predict deployment impact
python main.py predict-deploy --manifest ./my-deployment.yaml

# Generate and email report
python main.py report --email devops@company.com --teams-webhook https://outlook.office.com/webhook/xxx
```

### Option 2: Helm Install (Runs Continuously in Cluster)

```bash
helm repo add kubogent https://aivar-tech.github.io/kubogent-prophecy
helm install prophecy kubogent/prophecy \
  --namespace kubogent \
  --create-namespace \
  --set aws.region=us-east-1 \
  --set notifications.email=devops@company.com \
  --set notifications.teamsWebhook="https://outlook.office.com/webhook/xxx" \
  --set schedule.report="0 9 * * MON" \
  --set schedule.scan="0 */6 * * *"
```

### Option 3: Docker

```bash
docker run --rm \
  -v ~/.kube/config:/root/.kube/config \
  -v ~/.aws:/root/.aws \
  aivar/kubogent-prophecy scan
```

---

## What Gets Predicted

| Category | Examples |
|----------|----------|
| 💾 **Disk** | Node disk filling up (growth rate extrapolation) |
| 🧠 **Memory** | Pod approaching OOM (memory growth vs limit) |
| ⚡ **CPU** | Sustained high CPU, throttling risk |
| 🔐 **Certificates** | TLS cert expiring soon |
| 📈 **Scaling** | HPA at max replicas, can't scale further |
| 🔄 **Pod Health** | Increasing restart count, CrashLoopBackOff trend |
| 🌐 **Network** | Failed scheduling due to resource exhaustion |
| 🚀 **Deployments** | Impact prediction before applying changes |

---

## Example Output

```
🔮 Kubogent Prophecy — Scanning cluster...

📊 Using cluster: aivar-production-eks
🧠 Analyzing trends with AI...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📊 Cluster Score: 5.8/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Cluster has 3 predicted failures within 7 days.
  Immediate attention needed for disk and memory issues.

  🚨 CRITICAL (2)
  ────────────────────────────────────────

  [DISK] Node disk will reach capacity
  ⏱  Time to failure: ~4 days
  📍 Affected: ip-10-0-3-91.ec2.internal
  📈 Current: 84% → Threshold: 95%
  🎯 Confidence: HIGH
  💡 Action: Expand EBS volume or clean unused images

  [MEMORY] Pod OOM kill imminent
  ⏱  Time to failure: ~18 hours
  📍 Affected: log-aggregator (monitoring namespace)
  📈 Current: 490Mi/512Mi (96%) → Growing 3Mi/hour
  🎯 Confidence: HIGH
  💡 Action: Increase memory limit to 1Gi

  ⚠️  WARNING (1)
  ────────────────────────────────────────

  [CERT] TLS certificate expiring
  ⏱  Time to failure: 3 days
  📍 Affected: api-gateway-tls (gateway namespace)
  📈 Current: expires 2026-08-27
  🎯 Confidence: HIGH
  💡 Action: Manually renew certificate (auto-renew not configured)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total: 3 predictions | Critical: 2 | Warning: 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_DEFAULT_REGION` | Yes | AWS region for Bedrock (default: us-east-1) |
| `AWS_ACCESS_KEY_ID` | Yes* | AWS credentials (*or use IAM role/instance profile) |
| `AWS_SECRET_ACCESS_KEY` | Yes* | AWS credentials |
| `KUBECONFIG` | No | Path to kubeconfig (default: ~/.kube/config) |
| `PROPHECY_MODEL_ID` | No | Bedrock model (default: anthropic.claude-sonnet-4-20250514) |
| `SES_SENDER` | No | Email sender address (for email reports) |
| `TEAMS_WEBHOOK_URL` | No | Microsoft Teams webhook (for real-time alerts) |

### Helm Values

```yaml
# values.yaml
aws:
  region: us-east-1

notifications:
  email: devops@yourcompany.com
  teamsWebhook: "https://outlook.office.com/webhook/your-webhook-url"

schedule:
  # Full report (weekly, Monday 9 AM)
  report: "0 9 * * MON"
  # Quick scan (every 6 hours)
  scan: "0 */6 * * *"
  # Alert check (every hour)
  alert: "0 * * * *"

thresholds:
  disk_warn_percent: 80
  disk_critical_percent: 90
  memory_warn_percent: 85
  memory_critical_percent: 95
  cert_warn_days: 14
  cert_critical_days: 7

bedrock:
  modelId: "anthropic.claude-sonnet-4-20250514"
  maxTokens: 4096
```

---

## Integrations

### Microsoft Teams

1. Go to your Teams channel → Connectors → Incoming Webhook
2. Name it "Kubogent Prophecy" → Copy webhook URL
3. Pass as `--teams-webhook` or set `TEAMS_WEBHOOK_URL`

### Email (AWS SES)

1. Verify sender email in SES
2. Set `SES_SENDER` environment variable
3. Pass recipients via `--email`

### Outlook (Microsoft Graph)

For direct Outlook integration (without SES):
- See [docs/outlook-setup.md](docs/outlook-setup.md)

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│            Your EKS Cluster                      │
│                                                  │
│  ┌──────────────────────────────────────┐       │
│  │   Kubogent Prophecy (CronJob/Pod)    │       │
│  │                                      │       │
│  │  ┌─────────────┐ ┌──────────────┐   │       │
│  │  │  Collector  │ │   Predictor  │   │       │
│  │  │ (K8s API)   │→│  (Bedrock)   │   │       │
│  │  └─────────────┘ └──────┬───────┘   │       │
│  │                          │           │       │
│  │               ┌──────────┴────────┐  │       │
│  │               │     Reporter      │  │       │
│  │               └──┬─────────┬──────┘  │       │
│  └──────────────────┼─────────┼─────────┘       │
│                     │         │                  │
└─────────────────────┼─────────┼──────────────────┘
                      │         │
                      ▼         ▼
               ┌──────────┐ ┌──────────┐
               │  Email   │ │  Teams   │
               │  (SES)   │ │ (Webhook)│
               └──────────┘ └──────────┘
```

---

## How Predictions Work

1. **Collect** — Pulls live metrics from K8s API (nodes, pods, events, certs, HPA)
2. **Trend** — Calculates growth rates and trajectories over time
3. **Predict** — Feeds metrics + trends to Claude (Bedrock) for AI analysis
4. **Report** — Generates predictions with confidence levels, severity, and actions
5. **Alert** — Sends critical predictions to Teams/Email immediately

The AI doesn't just check thresholds — it understands:
- Growth patterns (linear, exponential)
- Correlated failures (deployment → OOM → cascade)
- Historical context (similar events in the past)
- Blast radius (what else breaks if this fails)

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| AWS Account with Bedrock access | Claude for predictions |
| EKS cluster (or any K8s cluster) | Metrics source |
| Python 3.10+ | Runtime |
| kubectl configured | Cluster access |

---

## Development

```bash
# Clone
git clone https://github.com/aivar-tech/kubogent-prophecy.git
cd kubogent-prophecy

# Install dependencies
pip install -r requirements.txt

# Run with mock data (no cluster needed)
python main.py scan --mock

# Run tests
pytest tests/
```

---

## Roadmap

| Phase | Features | Status |
|-------|----------|--------|
| v0.1 | Prediction engine + mock data + CLI | ✅ Done |
| v0.2 | Real K8s cluster integration | 🔄 Next |
| v0.3 | Email + Teams notifications | 🔄 Next |
| v0.4 | Helm chart for in-cluster deployment | Planned |
| v0.5 | Deployment impact prediction | Planned |
| v1.0 | Production-ready release | Planned |

---

## License

Internal — Aivar Innovations
