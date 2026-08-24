# Kubogent Prophecy — Project Plan

## What Is This?

**Kubogent Prophecy** is an AI-powered Kubernetes failure prediction engine. It predicts cluster failures **before they happen** — days in advance — and alerts the team via email and Microsoft Teams.

Think of it like a weather forecast for your Kubernetes cluster:
- "Your disk will be full in 4 days"
- "This pod will OOM in 18 hours"
- "TLS cert expires in 3 days (auto-renew not configured)"
- "HPA is maxed out — next traffic spike will cause downtime"

---

## Why It's Unique (Nobody Has This)

| Existing Tools | What They Do | What Prophecy Does Different |
|----------------|--------------|------------------------------|
| CloudWatch / Prometheus | Alert WHEN threshold is crossed | Predicts WHEN threshold WILL be crossed (days ahead) |
| Datadog / New Relic | Show current metrics | Shows FUTURE state based on trend analysis |
| PagerDuty / OpsGenie | Notifies after incident | Notifies BEFORE incident |
| kube-bench / Kubescape | Scan for misconfigurations | Predict failures from behavior patterns |

**No tool in the market does AI-driven failure prediction for Kubernetes.** This is novel.

---

## How It Works

```
┌─────────────────────────────────────────┐
│       Customer's EKS Cluster            │
│                                         │
│  Kubogent Prophecy (runs as CronJob)    │
│  ┌─────────────────────────────────┐    │
│  │ 1. Collect K8s metrics          │    │
│  │    (nodes, pods, certs, events) │    │
│  │                                 │    │
│  │ 2. Calculate trends             │    │
│  │    (growth rates, patterns)     │    │
│  │                                 │    │
│  │ 3. Send to Claude (Bedrock)     │    │
│  │    (AI analyzes & predicts)     │    │
│  │                                 │    │
│  │ 4. Generate predictions         │    │
│  │    (time-to-failure, severity)  │    │
│  │                                 │    │
│  │ 5. Alert (Teams/Email)          │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

---

## What It Predicts

| Category | Example Prediction |
|----------|-------------------|
| 💾 Disk | "Node disk will be full in 4.4 days at current growth rate" |
| 🧠 Memory | "Pod payment-processor will OOM in 17.6 hours (growing 5Mi/hour)" |
| 🔐 Certificates | "api-gateway TLS cert expires in 3 days, auto-renew is OFF" |
| 📈 Scaling | "HPA at 4/5 max replicas, CPU 82% — next spike = no headroom" |
| 🔄 Pod Health | "Restart count increasing: 0→1→2→3 in 7 days — CrashLoop coming" |
| 🌐 Scheduling | "5 FailedScheduling events in 6 hours — cluster can't fit new pods" |

---

## Delivery Model (How Customers Use It)

### Option A: Helm Install (Recommended)
```bash
helm install prophecy kubogent/prophecy \
  --set notifications.email=devops@customer.com \
  --set notifications.teamsWebhook=https://teams.webhook.url \
  --set schedule.report="0 9 * * MON"
```
Runs inside their cluster. Data never leaves. Weekly reports + real-time alerts.

### Option B: CLI (One-time Scan)
```bash
pip install kubogent-prophecy
kubogent-prophecy scan --kubeconfig ~/.kube/config
```

### Option C: Docker
```bash
docker run aivar/kubogent-prophecy scan
```

---

## Current Status

| Phase | What | Status |
|-------|------|--------|
| v0.1 | Prediction engine (Bedrock) + CLI + mock data | ✅ **Done & Working** |
| v0.2 | Real K8s cluster integration (live metrics) | 🔄 Next |
| v0.3 | Teams webhook + Email (SES) notifications | 🔄 Next |
| v0.4 | Helm chart for in-cluster deployment | Planned |
| v0.5 | Deployment impact prediction (pre-deploy check) | Planned |
| v1.0 | Production release | Planned |

---

## Demo Output (Working Today)

```
🔮 Kubogent Prophecy — Scanning cluster...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📊 Cluster Score: 3.2/10
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🚨 CRITICAL (3)
  ────────────────────────────────────────

  [CERT] Manual Certificate Expiration Imminent
  ⏱  Time to failure: 72 hours
  📍 Affected: api-gateway-tls (gateway namespace)
  💡 Action: Immediately renew certificate

  [DISK] Node Disk Space Exhaustion
  ⏱  Time to failure: ~4 days
  📍 Affected: ip-10-0-3-91.ec2.internal
  💡 Action: Expand EBS volume or clean images

  [MEMORY] Payment Processor OOM Kill Imminent
  ⏱  Time to failure: ~18 hours
  📍 Affected: payment-processor (production)
  💡 Action: Increase memory limit to 1Gi

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Total: 6 predictions | Critical: 3 | Warning: 3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Core engine | Python | Fast to build, K8s client library, boto3 |
| AI predictions | AWS Bedrock (Claude Sonnet 4) | Company already uses Bedrock |
| K8s integration | `kubernetes` Python client | Standard, works with any cluster |
| Reports | Markdown / PDF | Professional, shareable |
| Email | AWS SES | Already available in our accounts |
| Teams alerts | Incoming Webhook | Simple HTTP POST, no app registration |
| Deployment | Helm chart + Docker | Standard K8s deployment |

---

## Why This Is a Kubogent Feature (Not Just a Script)

1. **Runs continuously inside the cluster** (not a one-time scan)
2. **Self-contained** — Helm install, data stays inside customer's cluster
3. **AI-native** — Claude analyzes patterns a human would miss
4. **Integrated** — Teams/Email notifications, PDF reports for management
5. **Scalable** — works on any EKS cluster, any size
6. **Novel** — no existing tool does predictive failure analysis for K8s

---

## Business Value

| For | Value |
|-----|-------|
| **DevOps teams** | Prevent incidents before they happen. Reduce MTTR to zero (no incident = no resolution needed). |
| **Customers** | Higher availability, fewer outages, proactive maintenance |
| **Sales** | "Our managed K8s includes AI-powered predictive monitoring" — differentiator |
| **Management** | Weekly cluster health score + predictions = visibility without technical depth |

---

## Warp Speed Scoring

| Factor | Value |
|--------|-------|
| Size | M (Medium) — solo, 1-2 weeks |
| AI leverage ×1.5 | ✅ Claude/Bedrock is the prediction engine |
| Customer-facing ×1.5 | ✅ Kubogent product for customer clusters |
| Revenue-linked ×1.5 | ✅ Azentio & KoreAI run EKS |
| **Estimated Points** | **25 × 3.375 = 84.4 pts** |

---

## Repo

- **GitHub:** https://github.com/sriramg-aivar/kubogent-prophecy (private)
- **Language:** Python
- **Dependencies:** boto3, kubernetes, requests, pyyaml
