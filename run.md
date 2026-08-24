# 🔮 Vigilo — Setup & Run Guide

## What We Need

| # | Requirement | Purpose | Status |
|---|------------|---------|--------|
| 1 | **AWS Account (New)** | EKS cluster for testing | ❓ Need to create |
| 2 | **AWS Bedrock Access** (Account: 283744739430) | Claude Sonnet 4.5 for predictions | ✅ Have it |
| 3 | **Microsoft Teams Webhook URL** | Send shutdown/wakeup/alert notifications | ❓ Need from you |
| 4 | **Outlook/Email** (optional) | Weekly PDF report delivery | ❓ Need SES sender or SMTP |

---

## Step 1: Create Test EKS Cluster (New Account)

We need a separate account for testing. The cluster doesn't need real workloads — just dummy deployments to demonstrate shutdown/wakeup and predictions.

### What I Need From You:
- **AWS Account ID** (the new account to create EKS in)
- **Region** (ap-south-1 / us-east-1?)
- **VPC + Subnets** (or should I create fresh?)

### EKS Setup (I'll handle this):
```bash
# 1. Create EKS cluster
eksctl create cluster \
  --name vigilo-test \
  --region ap-south-1 \
  --version 1.29 \
  --nodegroup-name core \
  --node-type t3.medium \
  --nodes 2 \
  --managed

# 2. Install Karpenter (for node auto-scaling demo)
# 3. Install KEDA (for autoscaling demo)
# 4. Deploy dummy Convogent services (from bank repo values)
# 5. Install Vigilo via Helm
```

### Dummy Deployments (from bank repo):
We'll deploy the same chart structure as Convogent (frontend, backend, chat, eval, pca, voice) but with:
- Dummy images (nginx or httpbin) — no real app needed
- Same resource requests/limits
- Same KEDA ScaledObjects
- Same Karpenter NodePools
- Result: looks like production but does nothing

---

## Step 2: Cross-Account Bedrock Access

Vigilo runs inside the **test cluster** but calls Bedrock in **283744739430** (Aivar Agents).

### Option A: Cross-Account IAM Role (Recommended)
```
Test Account EKS Pod → assumes role → 283744739430 Bedrock
```

I'll create:
1. IAM role in 283744739430 with Bedrock InvokeModel permission
2. Trust policy allowing the test account's EKS pod to assume it
3. Pod uses IRSA (IAM Roles for Service Accounts) to get creds

### Option B: Static Credentials in Secret (Quick & Dirty for Demo)
```
Test Account EKS Pod → uses AWS creds from K8s Secret → 283744739430 Bedrock
```

For demo purposes, we can put temporary creds in a K8s secret. Not production-safe but works for testing.

---

## Step 3: Teams Webhook Setup

### What I Need From You:
1. Go to any **Microsoft Teams channel** (create one called "vigilo-alerts" or use existing)
2. Click **⋯ (three dots)** on the channel → **Connectors** (or **Manage channel** → **Connectors**)
3. Find **Incoming Webhook** → **Configure**
4. Name: `Vigilo`
5. Upload icon (optional)
6. Click **Create** → **Copy the webhook URL**
7. Share the URL with me (format: `https://outlook.office.com/webhook/...`)

That's it. No app registration needed.

---

## Step 4: Install Vigilo (Helm)

Once EKS cluster is ready:

```bash
# Add helm repo
helm repo add vigilo https://sriramg-aivar.github.io/vigilo

# Install
helm install vigilo vigilo/vigilo \
  --namespace vigilo \
  --create-namespace \
  --set aws.region=us-east-1 \
  --set aws.bedrockRoleArn=arn:aws:iam::283744739430:role/vigilo-bedrock-access \
  --set notifications.teamsWebhook="<YOUR_TEAMS_WEBHOOK_URL>" \
  --set schedule.shutdown="0 21 * * *" \
  --set schedule.wakeup="0 9 * * MON-FRI" \
  --set schedule.scan="0 */6 * * *" \
  --set scheduler.namespace="convogent"
```

### What Gets Deployed:
```
namespace: vigilo
├── CronJob: vigilo-scan (every 6 hours → predictions)
├── CronJob: vigilo-shutdown (9 PM daily → scale to zero)
├── CronJob: vigilo-wakeup (9 AM weekdays → bring back)
├── ServiceAccount: vigilo (with IRSA for Bedrock)
├── ConfigMap: vigilo-config (thresholds, namespaces)
└── Secret: vigilo-credentials (Teams webhook, AWS role)
```

---

## Step 5: Demo Flow

### Demo 1: Prediction Scan
```
EKS cluster running → Vigilo scans → AI analyzes → Teams message:

🔮 Vigilo — Weekly Report
Cluster Score: 7.5/10
⚠️ 2 warnings detected
• Node disk at 75%, will reach 90% in 5 days
• Pod restart count increasing (memory pressure)
```

### Demo 2: Night Shutdown (9 PM)
```
CronJob triggers → scales everything to 0 → nodes terminate → Teams message:

🌙 Cluster Shutdown Complete
• 6 deployments scaled to 0
• 14 pods terminated
• 4 Karpenter nodes removed
• Savings: $2.40/hour
```

### Demo 3: Morning Wakeup (9 AM)
```
CronJob triggers → restores replicas → nodes provision → Teams message:

☀️ Cluster is LIVE
• 6 deployments restored
• 14 pods starting
• 4 nodes provisioning
• Ready in: 3-5 minutes
```

---

## What I Need From You (Summary)

| # | What | How to Get |
|---|------|-----------|
| 1 | **New AWS Account ID** | For test EKS cluster (which account to use?) |
| 2 | **AWS credentials for that account** | To create EKS + deploy |
| 3 | **Teams Webhook URL** | Channel → Connectors → Incoming Webhook → Copy URL |
| 4 | **Bedrock account creds** (283744739430) | Already have (session tokens — or set up cross-account role) |

---

## Architecture (Full Picture)

```
┌─────────────────────────────────────────────────────────────┐
│  Test AWS Account (New)                                      │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  EKS Cluster: vigilo-test                         │    │
│  │                                                     │    │
│  │  namespace: convogent (dummy services)              │    │
│  │  ├── frontend (nginx, 2 replicas)                   │    │
│  │  ├── backend (httpbin, 2 replicas)                  │    │
│  │  ├── chat-service (nginx, 2 replicas)               │    │
│  │  ├── eval-service (nginx, 1 replica)                │    │
│  │  ├── pca-service (nginx, 1 replica)                 │    │
│  │  └── voice-service (nginx, 3 replicas)              │    │
│  │                                                     │    │
│  │  namespace: vigilo (our tool)                     │    │
│  │  ├── CronJob: vigilo-scan                         │    │
│  │  ├── CronJob: vigilo-shutdown                     │    │
│  │  └── CronJob: vigilo-wakeup                       │    │
│  │                                                     │    │
│  │  Karpenter (auto-scales nodes)                      │    │
│  │  KEDA (auto-scales pods)                            │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────┬───────────────────────────────────────┘
                      │ Cross-account assume role
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS Account: 283744739430 (Aivar Agents)                   │
│                                                             │
│  Bedrock: Claude Sonnet 4.5                                 │
│  (Vigilo calls this for AI predictions)                   │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Microsoft Teams                                            │
│                                                             │
│  Channel: #vigilo-alerts                                  │
│  • Shutdown notifications                                   │
│  • Wakeup notifications                                     │
│  • Critical prediction alerts                               │
│  • Weekly health reports                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Timeline

| Day | Task |
|-----|------|
| Day 1 | Create test EKS cluster + deploy dummy services |
| Day 2 | Build Helm chart + deploy Vigilo |
| Day 3 | Test predictions (live cluster) + Teams integration |
| Day 4 | Test shutdown/wakeup cycle + Teams notifications |
| Day 5 | Demo to TL + file Warp Speed issue |

---

## Commands Reference

```bash
# === PREDICTION ===
# Scan cluster (real)
python3 main.py scan --kubeconfig ~/.kube/config

# Scan cluster (mock — no cluster needed)
python3 main.py scan --mock

# Predict deployment impact
python3 main.py predict-deploy --manifest deployment.yaml

# === SCHEDULER ===
# Shutdown (preview)
python3 main.py shutdown --dry-run

# Shutdown (execute + notify Teams)
python3 main.py shutdown --kubeconfig ~/.kube/config --namespace convogent \
  --teams-webhook "https://outlook.office.com/webhook/xxx"

# Wakeup (preview)
python3 main.py wakeup --dry-run

# Wakeup (execute + notify Teams)
python3 main.py wakeup --kubeconfig ~/.kube/config --namespace convogent \
  --teams-webhook "https://outlook.office.com/webhook/xxx"

# === STATUS ===
# Full cluster inventory
python3 main.py status --kubeconfig ~/.kube/config

# JSON output
python3 main.py status --kubeconfig ~/.kube/config --output json

# === REPORTS ===
# Generate + email
python3 main.py report --email devops@aivar.tech --teams-webhook "https://..."

# Generate PDF/markdown
python3 main.py scan --mock --output pdf --output-file report.pdf
```

---

## After Demo: Integrate into Real Convogent

Once demo is successful, integration into real Convogent/Vigilo is just:

```bash
# In the real Convogent EKS cluster:
helm install vigilo vigilo/vigilo \
  --namespace vigilo \
  --set scheduler.namespace="convogent" \
  --set notifications.teamsWebhook="<real-team-webhook>"
```

Same Helm chart, different cluster. Works everywhere.
