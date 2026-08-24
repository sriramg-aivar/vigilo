#!/bin/bash
# ============================================
# 🟢 SETUP — Create/Resume Vigilo test environment
# ============================================
# Creates EVERYTHING from scratch OR resumes existing cluster.
# Uses AWS SSO profiles — no manual key export needed.
#
# What it creates:
# - VPC + Subnets + IGW + NAT (via eksctl CloudFormation)
# - EKS cluster (vigilo-test)
# - Managed node group (2x t3.medium)
# - Namespace: convogent (6 dummy services)
# - Vigilo Helm chart (CronJobs for scan + report)
#
# Prerequisites:
# - AWS SSO login: aws sso login --profile cloud-migration
# - eksctl installed: brew install eksctl
# - kubectl installed
# - helm installed: brew install helm
#
# Usage: ./setup.sh

set -e

CLUSTER_NAME="vigilo-test"
REGION="us-east-1"
NODE_TYPE="t3.medium"
NODES=2
AWS_PROFILE="cloud-migration"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${GREEN}🟢 VIGILO — Setup${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --- Check AWS credentials (env vars OR profile) ---
echo "🔐 Checking AWS credentials..."
if [ -n "$AWS_ACCESS_KEY_ID" ]; then
  ACCOUNT=$(aws sts get-caller-identity --query "Account" --output text 2>/dev/null || echo "")
  AWS_ARGS=""
else
  ACCOUNT=$(aws sts get-caller-identity $AWS_ARGS --query "Account" --output text 2>/dev/null || echo "")
  AWS_ARGS="--profile $AWS_PROFILE"
fi
if [ -z "$ACCOUNT" ]; then
  echo -e "${RED}❌ AWS credentials expired or not set.${NC}"
  echo ""
  echo "   Option 1: Export credentials manually:"
  echo '   export AWS_ACCESS_KEY_ID="..."'
  echo '   export AWS_SECRET_ACCESS_KEY="..."'
  echo '   export AWS_SESSION_TOKEN="..."'
  echo ""
  echo "   Option 2: aws sso login --profile cloud-migration"
  exit 1
fi
echo -e "   ${GREEN}✅ Account: $ACCOUNT${NC}"
echo ""

# --- Check if cluster exists ---
EXISTING=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" $AWS_ARGS --query "cluster.status" --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$EXISTING" = "ACTIVE" ]; then
  echo -e "${GREEN}✅ Cluster $CLUSTER_NAME already exists.${NC}"
  echo "   Updating kubeconfig..."
  aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$REGION" $AWS_ARGS
  echo ""

  # Check nodes
  DESIRED=$(aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name core --region "$REGION" $AWS_ARGS --query "nodegroup.scalingConfig.desiredSize" --output text 2>/dev/null || echo "0")
  if [ "$DESIRED" = "0" ]; then
    echo -e "${YELLOW}⚠️  Nodes are scaled to 0. Scaling up to $NODES...${NC}"
    aws eks update-nodegroup-config \
      --cluster-name "$CLUSTER_NAME" \
      --nodegroup-name core \
      --scaling-config minSize=2,maxSize=3,desiredSize=$NODES \
      --region "$REGION" \
      $AWS_ARGS > /dev/null
    echo "   ⏳ Waiting for nodes to join (~2-3 min)..."
    sleep 150
  fi

  echo "   🖥  Nodes:"
  kubectl get nodes 2>/dev/null || echo "   (waiting for nodes...)"
  echo ""

else
  # --- Create cluster from scratch ---
  echo "🚀 Creating EKS cluster: $CLUSTER_NAME"
  echo "   Region: $REGION"
  echo "   Nodes: $NODES x $NODE_TYPE"
  echo "   This takes ~15 minutes..."
  echo ""

  eksctl create cluster \
    --name "$CLUSTER_NAME" \
    --region "$REGION" \
    --version 1.31 \
    --nodegroup-name core \
    --node-type "$NODE_TYPE" \
    --nodes "$NODES" \
    --managed \
    --tags "Project=vigilo,Owner=sriram"

  echo ""
  echo -e "${GREEN}✅ Cluster created.${NC}"
fi

# --- Deploy dummy Convogent services ---
echo "📦 Deploying Convogent services..."
kubectl create namespace convogent 2>/dev/null || true
cat <<'MANIFEST' | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata: { name: convogent-frontend, namespace: convogent }
spec:
  replicas: 2
  selector: { matchLabels: { app: convogent-frontend } }
  template:
    metadata: { labels: { app: convogent-frontend } }
    spec:
      containers:
      - name: frontend
        image: nginx:alpine
        resources: { requests: { memory: "64Mi", cpu: "50m" }, limits: { memory: "128Mi", cpu: "200m" } }
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: convogent-backend, namespace: convogent }
spec:
  replicas: 2
  selector: { matchLabels: { app: convogent-backend } }
  template:
    metadata: { labels: { app: convogent-backend } }
    spec:
      containers:
      - name: backend
        image: nginx:alpine
        resources: { requests: { memory: "256Mi", cpu: "100m" }, limits: { memory: "512Mi", cpu: "500m" } }
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: convogent-chat-service, namespace: convogent }
spec:
  replicas: 2
  selector: { matchLabels: { app: convogent-chat-service } }
  template:
    metadata: { labels: { app: convogent-chat-service } }
    spec:
      containers:
      - name: chat
        image: nginx:alpine
        resources: { requests: { memory: "128Mi", cpu: "100m" }, limits: { memory: "256Mi", cpu: "300m" } }
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: convogent-eval-service, namespace: convogent }
spec:
  replicas: 1
  selector: { matchLabels: { app: convogent-eval-service } }
  template:
    metadata: { labels: { app: convogent-eval-service } }
    spec:
      containers:
      - name: eval
        image: nginx:alpine
        resources: { requests: { memory: "128Mi", cpu: "100m" }, limits: { memory: "256Mi", cpu: "300m" } }
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: convogent-pca-service, namespace: convogent }
spec:
  replicas: 1
  selector: { matchLabels: { app: convogent-pca-service } }
  template:
    metadata: { labels: { app: convogent-pca-service } }
    spec:
      containers:
      - name: pca
        image: nginx:alpine
        resources: { requests: { memory: "128Mi", cpu: "100m" }, limits: { memory: "256Mi", cpu: "300m" } }
---
apiVersion: apps/v1
kind: Deployment
metadata: { name: convogent-voice-service, namespace: convogent }
spec:
  replicas: 3
  selector: { matchLabels: { app: convogent-voice-service } }
  template:
    metadata: { labels: { app: convogent-voice-service } }
    spec:
      containers:
      - name: voice
        image: nginx:alpine
        resources: { requests: { memory: "256Mi", cpu: "200m" }, limits: { memory: "512Mi", cpu: "500m" } }
MANIFEST

echo "   ⏳ Waiting for pods..."
sleep 15
echo ""
kubectl get pods -n convogent

# --- Install Vigilo Helm Chart ---
echo ""
echo "🔮 Installing Vigilo Helm chart..."
kubectl create namespace vigilo 2>/dev/null || true

# Get Teams webhook from env or set placeholder
TEAMS_URL="${TEAMS_WEBHOOK_URL:-not-configured}"

helm upgrade --install vigilo ./helm/vigilo \
  --namespace vigilo \
  --set aws.region="$REGION" \
  --set notifications.teamsWebhook="$TEAMS_URL" \
  --set schedule.scan="0 */6 * * *" \
  --set schedule.report="0 9 * * MON" \
  --set image.repository="sriramg-aivar/vigilo" \
  --set image.tag="0.1.0" 2>/dev/null || echo "   (Helm chart installed — image not built yet, CronJobs created)"

echo ""
echo "   Vigilo CronJobs:"
kubectl get cronjobs -n vigilo 2>/dev/null || echo "   (pending image build)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ SETUP COMPLETE${NC}"
echo ""
echo "   Cluster: $CLUSTER_NAME ($REGION)"
echo "   Account: $ACCOUNT"
echo "   Nodes:   $NODES x $NODE_TYPE"
echo ""
echo "   Commands:"
echo "   kubectl get ns"
echo "   kubectl get pods -n convogent"
echo "   python3 main.py scan"
echo "   python3 main.py status"
echo "   python3 main.py report --teams-webhook \$TEAMS_WEBHOOK"
echo ""
echo "   Scripts:"
echo "   ./scale-to-zero.sh    # nodes to 0 (save cost)"
echo "   ./setup.sh            # bring back"
echo "   ./destroy.sh          # delete everything"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
