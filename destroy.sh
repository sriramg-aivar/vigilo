#!/bin/bash
# ============================================
# 🔴 DESTROY — Delete Vigilo test EKS cluster
# ============================================
# This will permanently delete:
# - All namespaces and workloads
# - EKS cluster (vigilo-test)
# - Node groups
# - VPC, subnets, security groups (created by eksctl)
# - CloudFormation stacks
#
# Usage: ./destroy.sh

set -e

CLUSTER_NAME="vigilo-test"
REGION="us-east-1"

echo ""
echo "🔴 DESTROYING EKS cluster: $CLUSTER_NAME ($REGION)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  This will permanently delete EVERYTHING in the cluster."
echo ""
read -p "Type 'destroy' to confirm: " CONFIRM
if [ "$CONFIRM" != "destroy" ]; then
  echo "❌ Aborted."
  exit 1
fi

echo ""
echo "🗑  Deleting cluster $CLUSTER_NAME..."
eksctl delete cluster --name "$CLUSTER_NAME" --region "$REGION" --wait

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Cluster $CLUSTER_NAME fully destroyed."
echo "   All resources (VPC, nodes, stacks) removed."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
