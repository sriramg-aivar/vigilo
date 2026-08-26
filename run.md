# Vigilo — How to Run

## Install on Any EKS Cluster (2 minutes)

```bash
# 1. Clone
git clone https://github.com/sriramg-aivar/vigilo.git
cd vigilo

# 2. Install
helm install vigilo ./helm/vigilo \
  --namespace vigilo \
  --create-namespace \
  --set notifications.teamsWebhook="<YOUR_TEAMS_WEBHOOK_URL>" \
  --set aws.region=us-east-1

# 3. Done. Report arrives Monday 9 AM on Teams.
```

---

## Teams Webhook Setup (30 seconds)

1. Open **Microsoft Teams** → go to your channel
2. Click **⋯ three dots** → **Workflows**
3. Search: **"Post to a channel when a webhook request is received"**
4. Name it `Vigilo` → select Team and Channel → **Save**
5. Copy the generated **HTTP POST URL**
6. Use it as `--set notifications.teamsWebhook="<URL>"`

---

## Test Cluster (For Demo/Development)

```bash
# Export AWS creds for Cloud Migration (880335327306)
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_SESSION_TOKEN="..."

# Create test cluster + deploy dummy services + install Vigilo
./setup.sh

# Scale nodes to 0 (save cost)
./scale-to-zero.sh

# Delete everything
./destroy.sh
```

---

## Manual Scan (Trigger Anytime)

```bash
# From inside cluster (trigger CronJob manually)
kubectl create job vigilo-manual --from=cronjob/vigilo-report -n vigilo

# From your laptop (CLI)
export BEDROCK_AWS_ACCESS_KEY_ID="..."
export BEDROCK_AWS_SECRET_ACCESS_KEY="..."
export BEDROCK_AWS_SESSION_TOKEN="..."
python3 main.py report --teams-webhook "$TEAMS_WEBHOOK_URL"
```

---

## View Logs

```bash
# CronJob status
kubectl get cronjobs -n vigilo

# Last job run
kubectl get jobs -n vigilo

# Logs from last scan
kubectl logs -l app=vigilo -n vigilo --tail=100
```

---

## Uninstall

```bash
helm uninstall vigilo -n vigilo
kubectl delete namespace vigilo
```
