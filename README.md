# 🔮 Vigilo

**Predict Kubernetes failures before they happen.**

Vigilo is an AI-powered engine that:
1. **Predicts failures** — disk full, OOM kills, cert expiry, scaling limits — days in advance
2. **Reports status** — full cluster inventory (nodes, pods, namespaces, Karpenter, KEDA)
3. **Alerts teams** — Microsoft Teams notifications with Error/Fix/Prevent format

Deploys via Helm as a CronJob inside your EKS cluster. No manual commands needed after install.

---

## Quick Start

```bash
# 1. Export AWS credentials
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
export AWS_DEFAULT_REGION=us-east-1

# 2. Create cluster + install Vigilo (one command)
./setup.sh

# 3. Done. Vigilo runs automatically:
#    - Scan every day 7 PM → predictions sent to Teams
#    - Report every Monday 9 AM → weekly health summary
```

### Lifecycle

```bash
./setup.sh           # Create VPC, EKS, deploy services, install Vigilo Helm chart
./scale-to-zero.sh   # Scale nodes to 0 (saves cost, EKS control plane stays)
./setup.sh           # Resume (scales nodes back up)
./destroy.sh         # Delete EVERYTHING (VPC, EKS, CloudFormation stacks)
```

---

## Features

### 🔮 AI Failure Prediction

Feeds cluster metrics to Claude (Bedrock) and returns predictions with:
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

Full inventory at any time:
- Nodes (count, type, status, pods per node)
- Pods per namespace (running, pending, failed)
- Deployments count
- Karpenter nodepools and active nodes
- KEDA ScaledObjects (active vs paused)

### 🔔 Teams Notifications (Error/Fix/Prevent)

Every alert follows:
- **Error:** What is failing or about to fail
- **Fix:** Immediate action to resolve
- **Prevent:** Long-term fix to avoid recurrence

Delivered via Microsoft Teams Power Automate workflow webhook.

### 📄 Report Generation

- Weekly health report with cluster score and all predictions
- PDF and Markdown output
- Sent to Teams and/or email automatically

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

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  AWS Account: 880335327306 (Cloud Migration)        │
│                                                     │
│  ┌───────────────────────────────────────────┐      │
│  │  EKS Cluster                              │      │
│  │                                           │      │
│  │  namespace: vigilo                        │      │
│  │  ├── CronJob: vigilo-scan (every day 7 PM)│      │
│  │  └── CronJob: vigilo-report (Mon 9 AM)   │      │
│  │                                           │      │
│  │  ┌────────────┐  ┌────────────────────┐   │      │
│  │  │ Collector  │  │    Predictor       │   │      │
│  │  │ (K8s API)  │→ │ (Bedrock/Claude)   │   │      │
│  │  └────────────┘  └─────────┬──────────┘   │      │
│  │                            │              │      │
│  │                   ┌────────┴───────────┐   │      │
│  │                   │     Reporter       │   │      │
│  │                   │ (Teams/PDF)        │   │      │
│  │                   └────────────────────┘   │      │
│  └───────────────────────────────────────────┘      │
└──────────────────────────┬──────────────────────────┘
                           │ Cross-account role assumption
                           ▼
┌─────────────────────────────────────────────────────┐
│  AWS Account: 283744739430 (Aivar Agents)           │
│                                                     │
│  Bedrock: Claude Sonnet 4 (AI predictions)          │
└─────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│  Microsoft Teams                                    │
│  • Critical alerts (Error/Fix/Prevent)              │
│  • Weekly health reports                            │
└─────────────────────────────────────────────────────┘
```

---

## How Vigilo Scans Your Cluster

Vigilo runs **inside** the cluster as a CronJob. It uses a Kubernetes ServiceAccount with read-only ClusterRole — no external credentials needed for cluster access.

### What Vigilo Reads (via K8s API)

| K8s API Endpoint | What It Gets |
|------------------|-------------|
| `/api/v1/nodes` | Node health, CPU, memory, disk, instance type, age |
| `/api/v1/pods` | Pod status, restarts, resource usage vs limits |
| `/api/v1/events` | Warnings, FailedScheduling, OOMKilled events |
| `/api/v1/secrets` (TLS type) | Certificate expiry dates |
| `/api/v1/resourcequotas` | Namespace resource limits vs usage |
| `/apis/apps/v1/deployments` | Deployment replicas, images, status |
| `/apis/autoscaling/v2/hpa` | HPA current vs max replicas, CPU target |
| `/apis/karpenter.sh/v1/nodepools` | Karpenter nodepool status |
| `/apis/keda.sh/v1alpha1/scaledobjects` | KEDA scaling status |

### RBAC (What Vigilo Has Access To)

```yaml
# ClusterRole: vigilo-reader (READ-ONLY)
rules:
  - apiGroups: [""]
    resources: [nodes, pods, events, secrets, namespaces, resourcequotas]
    verbs: [get, list, watch]       # READ ONLY — no create/update/delete
  - apiGroups: [apps]
    resources: [deployments, statefulsets, daemonsets]
    verbs: [get, list, watch]
  - apiGroups: [autoscaling]
    resources: [horizontalpodautoscalers]
    verbs: [get, list, watch]
  - apiGroups: [karpenter.sh]
    resources: [nodepools, nodeclaims]
    verbs: [get, list, watch]
  - apiGroups: [keda.sh]
    resources: [scaledobjects]
    verbs: [get, list, watch]
```

**Vigilo NEVER modifies anything in your cluster.** It only reads.

### Cross-Account Bedrock Access

The cluster may be in a different AWS account than Bedrock. Vigilo handles this via:
- **IRSA (recommended):** ServiceAccount annotated with IAM role that can assume Bedrock role
- **Environment variables:** `BEDROCK_AWS_ACCESS_KEY_ID`, `BEDROCK_AWS_SECRET_ACCESS_KEY`, `BEDROCK_AWS_SESSION_TOKEN`

```
EKS Pod (Account A) → assumes IAM role → Bedrock (Account B) → Claude Sonnet 4.5
```

---

## How Predictions Work

1. **Collect** — Pull live metrics from K8s API (nodes, pods, events, certs, HPA, KEDA)
2. **Trend** — Calculate growth rates and trajectories
3. **Predict** — Feed to Claude (Bedrock) for AI analysis
4. **Score** — Generate cluster health score (0-10) with confidence levels
5. **Alert** — Send critical predictions to Teams immediately
6. **Report** — Weekly PDF/Markdown with all predictions and actions

---

## Helm Chart

The Helm chart deploys Vigilo as CronJobs inside your cluster. No manual commands needed.

### Install (Standalone — Any EKS Cluster)

```bash
# Clone the repo
git clone https://github.com/sriramg-aivar/vigilo.git
cd vigilo

# Install Vigilo into your cluster
helm install vigilo ./helm/vigilo \
  --namespace vigilo \
  --create-namespace \
  --set aws.region=us-east-1 \
  --set notifications.teamsWebhook="<YOUR_TEAMS_WEBHOOK_URL>" \
  --set aws.bedrock.roleArn="arn:aws:iam::283744739430:role/vigilo-bedrock-access"
```

### What Gets Deployed

```
namespace: vigilo
├── CronJob: vigilo-scan (every day 7 PM → predictions sent to Teams)
├── CronJob: vigilo-report (weekly Monday 9 AM → full report to Teams)
├── ServiceAccount: vigilo (with IRSA for cross-account Bedrock)
├── ClusterRole: vigilo-reader (read-only access to cluster resources)
├── ClusterRoleBinding: vigilo-reader-binding
├── ConfigMap: vigilo-config (Teams webhook, region, model)
└── Secret: vigilo-credentials (Teams webhook)
```

### Helm Values

```yaml
aws:
  region: us-east-1
  bedrockRoleArn: arn:aws:iam::283744739430:role/vigilo-bedrock-access

notifications:
  teamsWebhook: "https://prod-XX.westus.logic.azure.com/workflows/..."

schedule:
  scan: "30 13 * * *"            # Every day 7 PM IST (1:30 PM UTC)
  report: "30 3 * * MON"         # Weekly Monday 9 AM IST (3:30 AM UTC)

thresholds:
  disk_warn_percent: 80
  disk_critical_percent: 90
  memory_warn_percent: 85
  memory_critical_percent: 95
  cert_warn_days: 14
  cert_critical_days: 7
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `setup.sh` | Create VPC, EKS cluster, deploy services, install Vigilo Helm chart |
| `scale-to-zero.sh` | Scale all node groups to 0 (cost savings) |
| `destroy.sh` | Delete EVERYTHING (VPC, EKS, CloudFormation stacks) |

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_DEFAULT_REGION` | Yes | AWS region (default: us-east-1) |
| `AWS_ACCESS_KEY_ID` | Yes* | AWS credentials (*or use IAM role) |
| `AWS_SECRET_ACCESS_KEY` | Yes* | AWS credentials |
| `TEAMS_WEBHOOK_URL` | No | Microsoft Teams Power Automate webhook URL |
| `VIGILO_MODEL_ID` | No | Bedrock model (default: Claude Sonnet 4) |

### AWS Accounts

| Account | ID | Purpose |
|---------|-----|---------|
| Cloud Migration | 880335327306 | EKS cluster (kubectl access) |
| Aivar Agents | 283744739430 | Bedrock (Claude Sonnet 4 for AI predictions) |

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

For local development and testing only:

```bash
# Clone
git clone https://github.com/sriramg-aivar/vigilo.git
cd vigilo

# Install dependencies
pip install -r requirements.txt

# Test prediction (no cluster needed — uses mock data)
python3 main.py scan --mock

# Run against real cluster
python3 main.py scan --kubeconfig ~/.kube/config

# Cluster status
python3 main.py status

# Run tests
pytest tests/
```

### CLI Commands (Dev Only)

| Command | Description |
|---------|-------------|
| `scan` | Run AI failure prediction scan |
| `predict-deploy` | Predict impact of a deployment manifest before applying |
| `report` | Generate health report (Teams + PDF) |
| `status` | Show full cluster inventory |

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| AWS credentials (Cloud Migration account) | EKS cluster access |
| AWS Bedrock access (Aivar Agents account) | Claude for AI predictions |
| Microsoft Teams webhook | Notifications |
| `kubectl` configured | Cluster access (handled by setup.sh) |

---

## License

Internal — Aivar Innovations
