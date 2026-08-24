#!/bin/bash
# ============================================
# 🟢 SETUP — Create/Resume Vigilo test EKS cluster
# ============================================
# Creates:
# - EKS cluster (vigilo-test) in us-east-1
# - 2x t3.medium nodes
# - Namespace: convogent (with 6 dummy services)
# - Updates kubeconfig so `kubectl get ns` works on your Mac
#
# Prerequisites:
# - AWS creds exported (for 880335327306 Cloud Migration account)
# - eksctl installed (brew install eksctl)
# - kubectl installed
#
# Usage: ./setup.sh

set -e

CLUSTER_NAME="vigilo-test"
REGION="us-east-1"
NODE_TYPE="t3.medium"
NODES=2

# --- Function: Deploy dummy Convogent services ---
deploy_services() {
  kubectl create namespace convogent 2>/dev/null || true
  cat <<'MANIFEST' | kubectl apply -f -
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: convogent-frontend
  namespace: convogent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: convogent-frontend
  template:
    metadata:
      labels:
        app: convogent-frontend
    spec:
      containers:
      - name: frontend
        image: nginx:alpine
        resources:
          requests: { memory: "64Mi", cpu: "50m" }
          limits: { memory: "128Mi", cpu: "200m" }
        ports: [{ containerPort: 80 }]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: convogent-backend
  namespace: convogent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: convogent-backend
  template:
    metadata:
      labels:
        app: convogent-backend
    spec:
      containers:
      - name: backend
        image: nginx:alpine
        resources:
          requests: { memory: "256Mi", cpu: "100m" }
          limits: { memory: "512Mi", cpu: "500m" }
        ports: [{ containerPort: 80 }]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: convogent-chat-service
  namespace: convogent
spec:
  replicas: 2
  selector:
    matchLabels:
      app: convogent-chat-service
  template:
    metadata:
      labels:
        app: convogent-chat-service
    spec:
      containers:
      - name: chat
        image: nginx:alpine
        resources:
          requests: { memory: "128Mi", cpu: "100m" }
          limits: { memory: "256Mi", cpu: "300m" }
        ports: [{ containerPort: 80 }]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: convogent-eval-service
  namespace: convogent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: convogent-eval-service
  template:
    metadata:
      labels:
        app: convogent-eval-service
    spec:
      containers:
      - name: eval
        image: nginx:alpine
        resources:
          requests: { memory: "128Mi", cpu: "100m" }
          limits: { memory: "256Mi", cpu: "300m" }
        ports: [{ containerPort: 80 }]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: convogent-pca-service
  namespace: convogent
spec:
  replicas: 1
  selector:
    matchLabels:
      app: convogent-pca-service
  template:
    metadata:
      labels:
        app: convogent-pca-service
    spec:
      containers:
      - name: pca
        image: nginx:alpine
        resources:
          requests: { memory: "128Mi", cpu: "100m" }
          limits: { memory: "256Mi", cpu: "300m" }
        ports: [{ containerPort: 80 }]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: convogent-voice-service
  namespace: convogent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: convogent-voice-service
  template:
    metadata:
      labels:
        app: convogent-voice-service
    spec:
      containers:
      - name: voice
        image: nginx:alpine
        resources:
          requests: { memory: "256Mi", cpu: "200m" }
          limits: { memory: "512Mi", cpu: "500m" }
        ports: [{ containerPort: 80 }]
MANIFEST
  echo "   ⏳ Waiting for pods to start..."
  sleep 15
  kubectl get pods -n convogent
}

# --- Main ---
echo ""
echo "🟢 SETTING UP EKS cluster: $CLUSTER_NAME ($REGION)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check AWS creds
echo "🔐 Checking AWS credentials..."
ACCOUNT=$(aws sts get-caller-identity --query "Account" --output text 2>/dev/null || echo "")
if [ -z "$ACCOUNT" ]; then
  echo "❌ AWS credentials not set. Export them first:"
  echo '   export AWS_ACCESS_KEY_ID="..."'
  echo '   export AWS_SECRET_ACCESS_KEY="..."'
  echo '   export AWS_SESSION_TOKEN="..."'
  exit 1
fi
echo "   ✅ Account: $ACCOUNT"
echo ""

# Check if cluster already exists
EXISTING=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION" --query "cluster.status" --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$EXISTING" = "ACTIVE" ]; then
  echo "✅ Cluster already exists and is ACTIVE."
  echo "   Updating kubeconfig..."
  aws eks update-kubeconfig --name "$CLUSTER_NAME" --region "$REGION"
  echo ""

  # Check if nodes are scaled to 0
  DESIRED=$(aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name core --region "$REGION" --query "nodegroup.scalingConfig.desiredSize" --output text 2>/dev/null || echo "0")
  if [ "$DESIRED" = "0" ]; then
    echo "⚠️  Nodes are scaled to 0. Scaling up to $NODES..."
    aws eks update-nodegroup-config \
      --cluster-name "$CLUSTER_NAME" \
      --nodegroup-name core \
      --scaling-config minSize=2,maxSize=3,desiredSize=$NODES \
      --region "$REGION" > /dev/null
    echo "   ⏳ Waiting for nodes to join (~2 min)..."
    sleep 120
  fi

  echo "   Nodes:"
  kubectl get nodes
  echo ""

  # Deploy services if not exists
  if ! kubectl get namespace convogent > /dev/null 2>&1; then
    echo "📦 Deploying Convogent dummy services..."
    deploy_services
  else
    echo "✅ Namespace 'convogent' exists."
    echo "   Pods:"
    kubectl get pods -n convogent
  fi

else
  # Create cluster from scratch
  echo "🚀 Creating EKS cluster (this takes ~15 minutes)..."
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
  echo "📦 Deploying Convogent dummy services..."
  deploy_services
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ SETUP COMPLETE"
echo ""
echo "   Cluster: $CLUSTER_NAME ($REGION)"
echo "   Nodes: $NODES x $NODE_TYPE"
echo ""
echo "   Commands:"
echo "   kubectl get ns                      # list namespaces"
echo "   kubectl get pods -n convogent       # list pods"
echo "   kubectl logs -f <pod> -n convogent  # view pod logs"
echo "   python3 main.py status              # vigilo cluster status"
echo "   python3 main.py scan                # vigilo AI prediction"
echo "   python3 main.py shutdown --dry-run  # preview shutdown"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
