# 🔮 Vigilo — Setup & Run Guide

## What We Need

| # | Requirement | Purpose | Status |
|---|------------|---------|--------|
| 1 | **AWS Account (EKS)** | EKS cluster for testing | ❓ Need to create |
| 2 | **AWS Bedrock Access** (Account: 283744739430) | Claude Sonnet 4 for predictions | ✅ Have it |
| 3 | **Microsoft Teams Webhook URL** | Send prediction alerts (Error/Fix/Prevent) | ❓ Need from you |
| 4 | **Outlook/Email** (optional) | Weekly PDF report delivery | ❓ Need SES sender or SMTP |

---

## Step 1: Create Test EKS Cluster

```bash
# Set up cluster + deploy dummy services (one command)
./setup.sh
```

This creates:
- EKS cluster (`vigilo-test`) in us-east-1
- 2x t3.medium nodes
- Namespace `convogent` with 6 dummy services
- Updates kubeconfig so `kubectl` works on your Mac

---

## Step 2: Cross-Account Bedrock Access

Vigilo runs inside the **EKS cluster** but calls Bedrock in **283744739430** (Aivar Agents).

### Option A: Cross-Account IAM Role (Recommended)
```
EKS Pod (IRSA) → assumes role → 283744739430 Bedrock
```

Setup:
1. IAM role in 283744739430 with `bedrock:InvokeModel` permission
2. Trust policy allowing the EKS account's Vigilo service account to assume it
3. Pod uses IRSA (IAM Roles for Service Accounts) to get creds

### Option B: Static Credentials (Quick for Demo)
```
EKS Pod → uses AWS creds from K8s Secret → 283744739430 Bedrock
```

For demo purposes — put temporary creds in a K8s secret. Not production-safe.

---

## Step 3: Teams Webhook Setup

1. Go to any **Microsoft Teams channel** (create one called "vigilo-alerts" or use existing)
2. Click **⋯ (three dots)** on the channel → **Connectors** → **Incoming Webhook** → **Configure**
3. Name: `Vigilo`
4. Click **Create** → **Copy the webhook URL**
5. Share the URL (format: `https://outlook.office.com/webhook/...`)

---

## Step 4: Run Vigilo

### Daily Flow

```bash
# 1. Set up cluster (or resume if scaled to zero)
./setup.sh

# 2. Run AI prediction scan
python3 main.py scan --kubeconfig ~/.kube/config

# 3. Generate report (sends to Teams)
python3 main.py report --teams-webhook <URL>

# 4. Scale to zero when done (saves ~$28/night)
./scale-to-zero.sh
```

### All CLI Commands

```bash
# === PREDICTION ===
# Scan cluster (real)
python3 main.py scan --kubeconfig ~/.kube/config

# Scan cluster (mock — no cluster needed)
python3 main.py scan --mock

# Predict deployment impact
python3 main.py predict-deploy --manifest deployment.yaml

# === STATUS ===
# Full cluster inventory
python3 main.py status --kubeconfig ~/.kube/config

# === REPORTS ===
# Generate + send to Teams
python3 main.py report --teams-webhook "https://outlook.office.com/webhook/xxx"

# Generate + email
python3 main.py report --email devops@aivar.tech --teams-webhook "https://..."
```

---

## Step 5: Install via Helm (In-Cluster)

Once tested, deploy as a CronJob inside the cluster:

```bash
helm repo add vigilo https://sriramg-aivar.github.io/vigilo

helm install vigilo vigilo/vigilo \
  --namespace vigilo \
  --create-namespace \
  --set aws.region=us-east-1 \
  --set aws.bedrockRoleArn=arn:aws:iam::283744739430:role/vigilo-bedrock-access \
  --set notifications.teamsWebhook="<YOUR_TEAMS_WEBHOOK_URL>" \
  --set schedule.scan="0 */6 * * *" \
  --set schedule.report="0 9 * * MON"
```

### What Gets Deployed:
```
namespace: vigilo
├── CronJob: vigilo-scan (every 6 hours → predictions)
├── CronJob: vigilo-report (weekly Monday 9 AM)
├── ServiceAccount: vigilo (with IRSA for cross-account Bedrock)
├── ConfigMap: vigilo-config (thresholds, namespaces)
└── Secret: vigilo-credentials (Teams webhook)
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  EKS Account (where Vigilo runs)                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  EKS Cluster: vigilo-test                           │    │
│  │                                                     │    │
│  │  namespace: convogent (dummy services)              │    │
│  │  ├── frontend (nginx, 2 replicas)                   │    │
│  │  ├── backend (httpbin, 2 replicas)                  │    │
│  │  ├── chat-service (nginx, 2 replicas)               │    │
│  │  ├── eval-service (nginx, 1 replica)                │    │
│  │  ├── pca-service (nginx, 1 replica)                 │    │
│  │  └── voice-service (nginx, 3 replicas)              │    │
│  │                                                     │    │
│  │  namespace: vigilo (our tool)                       │    │
│  │  ├── CronJob: vigilo-scan                           │    │
│  │  └── CronJob: vigilo-report                         │    │
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
│  Bedrock: Claude Sonnet 4                                   │
│  (Vigilo calls this for AI predictions)                     │
└─────────────────────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Microsoft Teams                                            │
│                                                             │
│  Channel: #vigilo-alerts                                    │
│  • Critical prediction alerts (Error/Fix/Prevent)           │
│  • Weekly health reports                                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Scripts

| Script | Purpose |
|--------|---------|
| `setup.sh` | Create/resume EKS test cluster + deploy dummy services |
| `scale-to-zero.sh` | Scale all node groups to 0 (cost savings, ~$28/night saved) |
| `destroy.sh` | Tear down the test cluster completely |

```bash
./setup.sh           # Create or resume cluster
./scale-to-zero.sh   # Scale nodes to 0 (EKS control plane stays alive)
./setup.sh           # Bring it back (scales nodes up, deploys services)
./destroy.sh         # Delete everything
```

---

## What I Need From You

| # | What | How to Get |
|---|------|-----------|
| 1 | **AWS Account ID** | For test EKS cluster (which account to use?) |
| 2 | **AWS credentials for that account** | To create EKS + deploy |
| 3 | **Teams Webhook URL** | Channel → Connectors → Incoming Webhook → Copy URL |
| 4 | **Bedrock account creds** (283744739430) | Already have (or set up cross-account role) |

---

## Timeline

| Day | Task |
|-----|------|
| Day 1 | Create test EKS cluster + deploy dummy services |
| Day 2 | Build Helm chart + deploy Vigilo |
| Day 3 | Test predictions (live cluster) + Teams integration |
| Day 4 | End-to-end: scan → report → Teams alert |
| Day 5 | Demo to TL + file Warp Speed issue |
