# Vigilo — Project Plan

## TL;DR

**Vigilo** predicts Kubernetes failures before they happen. It runs inside your EKS cluster as a Helm-deployed CronJob, uses Claude (Bedrock) for AI analysis, and sends Error/Fix/Prevent alerts to Microsoft Teams.

**One command to deploy:** `./setup.sh` — creates the cluster, deploys services, installs Vigilo. No manual Python commands needed.

---

## What It Does

| Feature | Description |
|---------|-------------|
| 🔮 AI Failure Prediction | Predicts disk full, OOM, cert expiry, scaling limits — days in advance |
| 📊 Cluster Status | Full inventory: nodes, pods, deployments, Karpenter, KEDA |
| 🔔 Teams Alerts | Error/Fix/Prevent format via Power Automate webhook |
| 📄 Reports | Weekly PDF/Markdown health report with cluster score |
| ⚙️ Helm Chart | Deploys as CronJob — scan every 6h, report every Monday |

---

## How It Works

```
K8s API → Collector → Claude (Bedrock) → Predictions → Teams Alert
                                                     → PDF Report
```

1. **Collect** — Pull live metrics from K8s API (nodes, pods, events, certs, HPA, KEDA)
2. **Trend** — Calculate growth rates and trajectories
3. **Predict** — Feed to Claude Sonnet 4 (Bedrock, cross-account) for AI analysis
4. **Score** — Generate cluster health score (0-10) with confidence levels
5. **Alert** — Send critical predictions to Teams immediately
6. **Report** — Weekly PDF/Markdown with all predictions and actions

---

## Demo Output

### Prediction Scan (Cluster Score: 3.2/10)

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

## Scoring & Prediction Model

### Cluster Health Score (0-10)

| Score | Meaning |
|-------|---------|
| 9-10 | Healthy — no predicted failures |
| 7-8 | Good — minor warnings only |
| 5-6 | Attention needed — warnings that could escalate |
| 3-4 | Degraded — critical predictions within days |
| 0-2 | Critical — immediate failures predicted |

### Prediction Categories

| Category | Detection Method | Time Window |
|----------|-----------------|-------------|
| 💾 Disk | Growth rate extrapolation | 1-7 days |
| 🧠 Memory | Usage vs limits trending | 6-48 hours |
| ⚡ CPU | Sustained utilization + throttling | 12-72 hours |
| 🔐 Certificates | Expiry date check (non-auto-renewed) | 7-30 days |
| 📈 Scaling | HPA/KEDA near max + traffic trends | 1-3 days |
| 🔄 Pod Health | Restart count acceleration | 6-24 hours |
| 🌐 Scheduling | Node capacity vs pending pods | 1-3 days |

### Confidence Levels

| Level | Meaning |
|-------|---------|
| HIGH | Strong trend data, failure very likely |
| MEDIUM | Trend detected but could stabilize |
| LOW | Early signal, worth monitoring |

---

## What Makes Vigilo Different

| Existing Tools | Vigilo |
|---|---|
| CloudWatch alerts AFTER threshold crossed | Predicts WHEN threshold WILL be crossed |
| `kubectl get pods` shows current state | AI-analyzed health score with recommendations |
| Generic monitoring dashboards | Actionable Error/Fix/Prevent alerts |
| Manual correlation across metrics | AI connects patterns across disk/memory/CPU/certs/scaling |
| Single-account tools | Cross-account (Bedrock in one account, EKS in another) |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  AWS Account: 880335327306 (Cloud Migration)        │
│                                                     │
│  EKS Cluster                                        │
│  ├── namespace: vigilo                              │
│  │   ├── CronJob: vigilo-scan (every 6h)           │
│  │   └── CronJob: vigilo-report (Mon 9 AM)         │
│  └── namespace: convogent (production services)     │
│                                                     │
└──────────────────────────┬──────────────────────────┘
                           │ Cross-account role assumption
                           ▼
┌─────────────────────────────────────────────────────┐
│  AWS Account: 283744739430 (Aivar Agents)           │
│  Bedrock: Claude Sonnet 4 (AI predictions)          │
└─────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────┐
│  Microsoft Teams (Power Automate Webhook)           │
│  • Critical alerts (Error/Fix/Prevent)              │
│  • Weekly health reports                            │
└─────────────────────────────────────────────────────┘
```

---

## Test Results

### What's Been Tested

| Test | Result |
|------|--------|
| Mock scan (no cluster) | ✅ Predictions generated correctly |
| Bedrock integration (Claude Sonnet 4) | ✅ AI analysis returns structured predictions |
| Teams notification delivery | ✅ Adaptive Cards with Error/Fix/Prevent format |
| Report generation (Markdown) | ✅ Full report with score + predictions |
| Cross-account Bedrock access | ✅ IRSA → assume role → invoke model |
| Cluster status collection | ✅ Nodes, pods, namespaces, Karpenter, KEDA |
| Helm chart deployment | ✅ CronJobs created and running on schedule |

### How to Test Locally

```bash
# No cluster needed — uses mock data
python3 main.py scan --mock
```

---

## Deployment Model

Vigilo deploys via Helm chart as CronJobs inside the cluster. No manual intervention after install.

| Component | Schedule | Output |
|-----------|----------|--------|
| `vigilo-scan` | Every 6 hours | Predictions → Teams alert if critical |
| `vigilo-report` | Monday 9 AM | Full report → Teams + PDF |

### End-User Workflow

```bash
./setup.sh           # One command: creates everything, installs Vigilo
# ... Vigilo runs automatically from here ...
./scale-to-zero.sh   # Save cost when not needed
./destroy.sh         # Delete everything
```

No Python commands. No manual scans. Helm chart handles scheduling.

---

## Integration Targets

| Cluster | How | Benefit |
|---------|-----|---------|
| Convogent (Bank) | Helm install + CronJob | Prevent incidents before they happen |
| Velogent (Azentio) | Helm install | Proactive EKS failure detection |
| Any EKS cluster | `./setup.sh` or Helm install | Universal predictive monitoring |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Core engine | Python 3.10+ |
| AI predictions | AWS Bedrock (Claude Sonnet 4) |
| K8s integration | `kubernetes` Python client |
| Autoscaling awareness | Karpenter + KEDA + HPA tracking |
| Reports | Markdown / PDF |
| Teams alerts | Power Automate workflow webhook (Adaptive Cards) |
| Deployment | Helm chart + Docker + CronJob |
| Infrastructure | CloudFormation (VPC, EKS) |

---

## Project Status

| Feature | Status |
|---------|--------|
| Prediction engine (Bedrock + Claude) | ✅ Done |
| CLI interface (scan, predict-deploy, report, status) | ✅ Done |
| Teams notifications (Error/Fix/Prevent) | ✅ Done |
| Cluster status inventory | ✅ Done |
| Report generation (Markdown/PDF) | ✅ Done |
| Real K8s cluster integration | ✅ Done |
| Cross-account Bedrock access (IRSA) | ✅ Done |
| Helm chart (in-cluster CronJob) | ✅ Done |
| setup.sh (one-command deployment) | ✅ Done |
| scale-to-zero.sh (cost savings) | ✅ Done |
| destroy.sh (full teardown) | ✅ Done |
