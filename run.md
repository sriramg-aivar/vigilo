# 🔮 Vigilo — Setup & Run Guide

Complete step-by-step guide: from zero to predictions arriving in Teams.

---

## Prerequisites

| Requirement | Purpose |
|-------------|---------|
| AWS credentials (Cloud Migration: 880335327306) | EKS cluster + kubectl |
| AWS Bedrock access (Aivar Agents: 283744739430) | Claude Sonnet 4 for AI predictions |
| Microsoft Teams webhook URL | Receive alerts and reports |
| macOS/Linux terminal | Run setup scripts |

---

## Step 1: Export AWS Credentials

```bash
# Cloud Migration account (EKS cluster lives here)
export AWS_ACCESS_KEY_ID=<your-key>
export AWS_SECRET_ACCESS_KEY=<your-secret>
export AWS_DEFAULT_REGION=us-east-1
```

These credentials need permissions for:
- CloudFormation (create VPC, EKS)
- EKS (create cluster, node groups)
- EC2 (networking, security groups)
- IAM (service roles)

---

## Step 2: Set Up Teams Webhook (Power Automate)

Microsoft retired the old "Incoming Webhook" connector. Use **Power Automate workflow** instead:

### Create the Workflow

1. Open **Microsoft Teams**
2. Go to the channel where you want alerts (e.g., create `#vigilo-alerts`)
3. Click **⋯ (three dots)** on the channel → **Workflows**
4. Search for **"Post to a channel when a webhook request is received"**
5. Click it → **Set up workflow**
6. Select the Team and Channel
7. Click **Add workflow**
8. Copy the webhook URL (format: `https://prod-XX.westus.logic.azure.com/workflows/...`)

### Set the Webhook

```bash
export TEAMS_WEBHOOK_URL="https://prod-XX.westus.logic.azure.com/workflows/..."
```

### Test It (Optional)

```bash
curl -X POST "$TEAMS_WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{"type":"message","attachments":[{"contentType":"application/vnd.microsoft.card.adaptive","content":{"type":"AdaptiveCard","$schema":"http://adaptivecards.io/schemas/adaptive-card.json","version":"1.4","body":[{"type":"TextBlock","text":"✅ Vigilo webhook test successful!","weight":"Bolder"}]}}]}'
```

You should see the message appear in your Teams channel.

---

## Step 3: Run setup.sh

```bash
./setup.sh
```

This single command does everything:
1. Creates a VPC (CloudFormation)
2. Creates an EKS cluster with managed node groups
3. Updates your local kubeconfig (so `kubectl` works)
4. Deploys dummy services (to have something to scan)
5. Installs Vigilo Helm chart (CronJobs for scan + report)

**Expected time:** ~15-20 minutes (EKS cluster creation takes time)

### What Gets Created

```
AWS Resources:
├── VPC + subnets + security groups (CloudFormation)
├── EKS cluster: vigilo-test
├── Node group: 2x t3.medium nodes
└── IAM roles (cluster role, node role, IRSA)

Kubernetes:
├── namespace: convogent (dummy services for scanning)
├── namespace: vigilo
│   ├── CronJob: vigilo-scan (every 6 hours)
│   ├── CronJob: vigilo-report (Monday 9 AM)
│   ├── ServiceAccount: vigilo (IRSA for Bedrock)
│   ├── ConfigMap: vigilo-config
│   └── Secret: vigilo-credentials (Teams webhook)
```

---

## Step 4: Verify It's Working

```bash
# Check cluster is accessible
kubectl get nodes

# Check Vigilo is deployed
kubectl get cronjobs -n vigilo

# Check pods are running (dummy services)
kubectl get pods -n convogent

# Trigger a manual scan (optional — don't need to wait 6 hours)
kubectl create job --from=cronjob/vigilo-scan vigilo-scan-manual -n vigilo

# Watch the scan run
kubectl logs -f job/vigilo-scan-manual -n vigilo
```

---

## Step 5: What Happens Automatically

Once installed, Vigilo runs on schedule with no intervention:

| CronJob | Schedule | What It Does |
|---------|----------|--------------|
| `vigilo-scan` | Every 6 hours | Collects metrics → AI prediction → Teams alert if critical |
| `vigilo-report` | Monday 9 AM | Full health report → Teams + PDF |

### Teams Alerts Arrive Automatically

When a scan detects critical predictions:
- **Adaptive Card** posted to your Teams channel
- **Error/Fix/Prevent** format for each prediction
- **Cluster score** included (0-10)

---

## Lifecycle Commands

```bash
# Resume after scaling to zero (or first-time setup)
./setup.sh

# Scale nodes to 0 (saves cost — EKS control plane stays alive at ~$2.40/day)
./scale-to-zero.sh

# Delete EVERYTHING (VPC, EKS, CloudFormation stacks — irreversible)
./destroy.sh
```

### Cost Breakdown

| State | Cost |
|-------|------|
| Running (2x t3.medium + EKS) | ~$5.50/day |
| Scaled to zero (EKS control plane only) | ~$2.40/day |
| Destroyed | $0 |

---

## Cross-Account Bedrock Access

Vigilo runs in **880335327306** (Cloud Migration) but calls Bedrock in **283744739430** (Aivar Agents).

### How It Works

```
Vigilo Pod (IRSA) → sts:AssumeRole → 283744739430 → bedrock:InvokeModel
```

1. Vigilo pod uses IRSA (IAM Roles for Service Accounts) to get AWS credentials
2. Assumes a cross-account role in 283744739430
3. Calls Bedrock with Claude Sonnet 4

### IAM Role in Bedrock Account (283744739430)

```json
{
  "RoleName": "vigilo-bedrock-access",
  "Permissions": ["bedrock:InvokeModel"],
  "Trust": "EKS account's Vigilo service account (IRSA)"
}
```

---

## Troubleshooting

### Cluster not accessible after setup

```bash
# Update kubeconfig manually
aws eks update-kubeconfig --name vigilo-test --region us-east-1
```

### Scan not producing results

```bash
# Check CronJob status
kubectl get cronjobs -n vigilo

# Check recent job logs
kubectl logs -l job-name=vigilo-scan --tail=50 -n vigilo

# Verify Bedrock access
kubectl exec -it deploy/vigilo-debug -n vigilo -- aws bedrock-runtime invoke-model --help
```

### Teams notifications not arriving

1. Verify webhook URL is set in the secret:
   ```bash
   kubectl get secret vigilo-credentials -n vigilo -o jsonpath='{.data.teams-webhook}' | base64 -d
   ```
2. Test the webhook manually (curl command in Step 2)
3. Check Power Automate workflow is enabled in Teams

### Nodes not scaling back up

```bash
# Check node group status
aws eks describe-nodegroup --cluster-name vigilo-test --nodegroup-name vigilo-nodes --region us-east-1

# Force scale up
aws eks update-nodegroup-config --cluster-name vigilo-test --nodegroup-name vigilo-nodes --scaling-config minSize=2,maxSize=4,desiredSize=2 --region us-east-1
```

---

## Configuration Reference

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AWS_ACCESS_KEY_ID` | Yes | AWS credentials for Cloud Migration account |
| `AWS_SECRET_ACCESS_KEY` | Yes | AWS credentials |
| `AWS_DEFAULT_REGION` | Yes | Region (default: us-east-1) |
| `TEAMS_WEBHOOK_URL` | No | Power Automate webhook for Teams alerts |
| `VIGILO_MODEL_ID` | No | Bedrock model (default: Claude Sonnet 4) |

### Helm Values (Configurable)

```yaml
aws:
  region: us-east-1
  bedrockRoleArn: arn:aws:iam::283744739430:role/vigilo-bedrock-access

notifications:
  teamsWebhook: "https://prod-XX.westus.logic.azure.com/workflows/..."

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

## Summary: End-to-End Flow

```
1. Export AWS creds
2. Set Teams webhook URL
3. Run ./setup.sh
4. Wait ~15 mins for cluster creation
5. ✅ Vigilo is running — predictions arrive in Teams automatically

No Python commands. No manual scans. Helm chart handles everything.
```
