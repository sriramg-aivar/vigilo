# Vigilo — Project Plan

## What Is This?

**Vigilo** is an AI-powered Kubernetes failure prediction engine that:

1. **🔮 Failure Prediction** — Predicts cluster failures (disk full, OOM, cert expiry) days before they happen
2. **📊 Cluster Status** — Full cluster inventory (nodes, pods, namespaces, Karpenter, KEDA)
3. **🔔 Teams Alerts** — Microsoft Teams notifications in Error/Fix/Prevent format
4. **🌐 Cross-Account** — Bedrock in one AWS account, EKS in another (via IAM role assumption)

Packaged as a **single CLI/Helm chart** that any team can install on their EKS cluster.

---

## Why It Matters

### Problem: Incidents Happen Without Warning
Current monitoring alerts AFTER something breaks. By then, it's 2 AM and someone is on-call firefighting.

**Vigilo Solution:** AI predicts failures 1-7 days in advance. Team gets a weekly report and real-time Teams alerts for critical predictions in Error/Fix/Prevent format.

---

## Features

### 🔮 Failure Prediction

| What It Does | How |
|---|---|
| Predicts disk full | Tracks disk growth rate → extrapolates time to failure |
| Predicts OOM kills | Monitors memory growth vs limits |
| Predicts cert expiry | Checks cert dates, flags non-auto-renewed ones |
| Predicts scaling limits | Detects HPA near max replicas |
| Predicts pod health issues | Restart count trending up = CrashLoop coming |
| Predicts scheduling failures | Node capacity exhaustion |
| Predicts deployment impact | Before deploy → "this will cause X" |

**Output:** Cluster Health Score (0-10) + predictions with time-to-failure + recommended actions.

### 📊 Cluster Status / Inventory

Shows at any time:
- How many nodes running (and what type)
- How many pods per namespace
- What increased / decreased since last check
- Karpenter nodepool status
- KEDA scaling status

### 🔔 Teams Notifications (Error/Fix/Prevent)

Every alert follows the format:
- **Error:** What is failing or about to fail
- **Fix:** Immediate action to resolve
- **Prevent:** Long-term fix to avoid recurrence

---

## Cross-Account Architecture

Vigilo supports running in one AWS account while calling Bedrock in another:

```
┌─────────────────────────────────────────────────┐
│  EKS Account (where Vigilo runs)                │
│                                                 │
│  Vigilo Pod (IRSA) → assumes cross-account role │
└───────────────────────┬─────────────────────────┘
                        │ sts:AssumeRole
                        ▼
┌─────────────────────────────────────────────────┐
│  Bedrock Account (283744739430)                 │
│                                                 │
│  IAM Role: vigilo-bedrock-access                │
│  Permission: bedrock:InvokeModel                │
│  Trust: EKS account's Vigilo service account    │
└─────────────────────────────────────────────────┘
```

This allows:
- EKS clusters in any account to use Vigilo
- Single Bedrock model access managed centrally
- No static credentials — uses IRSA + role chaining

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

## How It Works

1. **Collect** — Pull live metrics from K8s API (nodes, pods, events, certs, HPA, KEDA)
2. **Trend** — Calculate growth rates and trajectories
3. **Predict** — Feed to Claude (Bedrock) for AI analysis
4. **Score** — Generate cluster health score (0-10) with confidence levels
5. **Alert** — Send critical predictions to Teams (Error/Fix/Prevent format)
6. **Report** — Weekly PDF with all predictions and actions

---

## Integration Plan

| Cluster | How to Integrate | Benefit |
|---------|-----------------|---------|
| **Convogent (Bank)** | Helm install + CronJob (scan every 6 hours) | Prevent incidents before they happen |
| **Vigilo (customers)** | Part of managed K8s offering | Predictive monitoring as a feature |
| **Velogent (Azentio)** | Monitor EKS cluster health | Proactive failure detection |
| **Any EKS cluster** | `pip install` or `helm install` | Universal tool |

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Core engine | Python 3.10+ |
| AI predictions | AWS Bedrock (Claude Sonnet 4) |
| K8s integration | `kubernetes` Python client |
| Autoscaling awareness | Karpenter + KEDA + HPA tracking |
| Reports | Markdown / PDF |
| Email | AWS SES |
| Teams alerts | Incoming Webhook (Adaptive Cards, Error/Fix/Prevent) |
| Deployment | Helm chart + Docker + CronJob |

---

## What's Unique

| What Exists | What Vigilo Does Different |
|---|---|
| CloudWatch alerts after threshold crossed | Vigilo predicts WHEN threshold WILL be crossed |
| kubectl get pods | Vigilo gives AI-analyzed health score with recommendations |
| Generic monitoring dashboards | Vigilo gives actionable Error/Fix/Prevent alerts |
| Single-account tools | Vigilo works cross-account (Bedrock in one, EKS in another) |

---

## Project Status

| Phase | Feature | Status |
|-------|---------|--------|
| v0.1 | Prediction engine (Bedrock + Claude) | ✅ Done & Tested |
| v0.1 | CLI interface (scan, predict-deploy, report, status) | ✅ Done |
| v0.1 | Teams notifications (Error/Fix/Prevent) | ✅ Done |
| v0.1 | Cluster status inventory | ✅ Done |
| v0.1 | Markdown report generation | ✅ Done |
| v0.2 | Real K8s cluster integration | 🔄 Next |
| v0.2 | Cross-account Bedrock access (IRSA) | 🔄 Next |
| v0.3 | Helm chart for in-cluster CronJob | Planned |
| v0.4 | Email reports (SES) | Planned |
| v1.0 | Production release | Planned |

---

## Repo

- **GitHub:** https://github.com/sriramg-aivar/vigilo
- **Run:** `python3 main.py scan --mock` (works today, no cluster needed)
