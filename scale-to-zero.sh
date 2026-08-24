#!/bin/bash
# ============================================
# 🌙 SCALE TO ZERO — Scale all nodes to 0
# ============================================
# Scales all node groups in the EKS cluster to 0.
# EKS control plane stays alive (AWS managed).
# All pods will be evicted, all nodes terminated.
#
# Usage: ./scale-to-zero.sh
# Reverse: ./setup.sh (brings everything back)
#
# Prerequisites:
# - AWS creds exported (for 880335327306 Cloud Migration account)
# - kubectl configured

set -e

CLUSTER_NAME="vigilo-test"
REGION="us-east-1"

echo ""
echo "🌙 Scaling cluster nodes to ZERO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check AWS creds
ACCOUNT=$(aws sts get-caller-identity --query "Account" --output text 2>/dev/null || echo "")
if [ -z "$ACCOUNT" ]; then
  echo "❌ AWS credentials not set. Export them first."
  exit 1
fi
echo "✅ Account: $ACCOUNT"

# Get all node groups
echo ""
echo "📋 Finding node groups..."
NODEGROUPS=$(aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$REGION" --query "nodegroups[]" --output text 2>/dev/null)

if [ -z "$NODEGROUPS" ]; then
  echo "❌ No node groups found for cluster $CLUSTER_NAME"
  exit 1
fi

echo "   Found: $NODEGROUPS"
echo ""

# Scale each node group to 0
for NG in $NODEGROUPS; do
  CURRENT=$(aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NG" --region "$REGION" --query "nodegroup.scalingConfig.desiredSize" --output text)
  echo "   📉 $NG: $CURRENT → 0"
  aws eks update-nodegroup-config \
    --cluster-name "$CLUSTER_NAME" \
    --nodegroup-name "$NG" \
    --scaling-config minSize=0,maxSize=3,desiredSize=0 \
    --region "$REGION" > /dev/null 2>&1
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ All node groups scaled to 0."
echo "   Nodes will terminate in ~1-2 minutes."
echo "   EKS control plane is still alive."
echo ""
echo "   To bring back: ./setup.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
