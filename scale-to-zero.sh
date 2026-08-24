#!/bin/bash
# ============================================
# 🌙 SCALE TO ZERO — Scale nodes to 0 (save cost)
# ============================================
# Keeps EKS control plane alive ($0.10/hr).
# Removes all nodes (EC2 instances terminate).
# Reverse with: ./setup.sh
#
# Uses AWS SSO profile — no manual key export needed.
#
# Usage: ./scale-to-zero.sh

set -e

CLUSTER_NAME="vigilo-test"
REGION="us-east-1"
AWS_PROFILE="cloud-migration"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${YELLOW}🌙 Scaling nodes to ZERO${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check creds
ACCOUNT=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --query "Account" --output text 2>/dev/null || echo "")
if [ -z "$ACCOUNT" ]; then
  echo "❌ AWS credentials expired. Run: aws sso login --profile cloud-migration"
  exit 1
fi
echo "✅ Account: $ACCOUNT"
echo ""

# Get all node groups and scale to 0
NODEGROUPS=$(aws eks list-nodegroups --cluster-name "$CLUSTER_NAME" --region "$REGION" --profile "$AWS_PROFILE" --query "nodegroups[]" --output text 2>/dev/null)

if [ -z "$NODEGROUPS" ]; then
  echo "❌ No node groups found for $CLUSTER_NAME"
  exit 1
fi

for NG in $NODEGROUPS; do
  CURRENT=$(aws eks describe-nodegroup --cluster-name "$CLUSTER_NAME" --nodegroup-name "$NG" --region "$REGION" --profile "$AWS_PROFILE" --query "nodegroup.scalingConfig.desiredSize" --output text)
  echo "   📉 $NG: $CURRENT → 0"
  aws eks update-nodegroup-config \
    --cluster-name "$CLUSTER_NAME" \
    --nodegroup-name "$NG" \
    --scaling-config minSize=0,maxSize=3,desiredSize=0 \
    --region "$REGION" \
    --profile "$AWS_PROFILE" > /dev/null 2>&1
done

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ All nodes scaling to 0.${NC}"
echo "   Nodes will terminate in ~1-2 minutes."
echo "   EKS control plane still alive ($0.10/hr)."
echo ""
echo "   To bring back: ./setup.sh"
echo "   To delete everything: ./destroy.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
