#!/bin/bash
# ============================================
# 🔴 DESTROY — Delete EVERYTHING
# ============================================
# Deletes:
# - All namespaces and workloads
# - EKS cluster (vigilo-test)
# - Node groups
# - VPC, subnets, NAT gateway, IGW
# - All CloudFormation stacks created by eksctl
# - Security groups, route tables
#
# Uses AWS SSO profile — no manual key export needed.
#
# Usage: ./destroy.sh

set -e

CLUSTER_NAME="vigilo-test"
REGION="us-east-1"
AWS_PROFILE="cloud-migration"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${RED}🔴 DESTROY — Deleting cluster: $CLUSTER_NAME${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  This will PERMANENTLY delete:"
echo "   • EKS cluster ($CLUSTER_NAME)"
echo "   • All node groups and EC2 instances"
echo "   • VPC, subnets, NAT gateway, IGW"
echo "   • All CloudFormation stacks"
echo "   • All workloads and data inside the cluster"
echo ""
read -p "Type 'destroy' to confirm: " CONFIRM
if [ "$CONFIRM" != "destroy" ]; then
  echo "❌ Aborted."
  exit 1
fi

echo ""

# Check creds
echo "🔐 Checking credentials..."
ACCOUNT=$(aws sts get-caller-identity --query "Account" --output text 2>/dev/null || echo "")
if [ -z "$ACCOUNT" ]; then
  echo -e "${RED}❌ AWS credentials expired. Run: aws sso login --profile cloud-migration${NC}"
  exit 1
fi
echo -e "   ${GREEN}✅ Account: $ACCOUNT${NC}"
echo ""

# Check if cluster exists
EXISTING=$(aws eks describe-cluster --name "$CLUSTER_NAME" --region "$REGION"  --query "cluster.status" --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$EXISTING" = "NOT_FOUND" ]; then
  echo "ℹ️  Cluster $CLUSTER_NAME does not exist."
  echo ""
  echo "   Checking for leftover CloudFormation stacks..."
  STACKS=$(aws cloudformation list-stacks  --region "$REGION" --stack-status-filter CREATE_COMPLETE ROLLBACK_COMPLETE UPDATE_COMPLETE --query "StackSummaries[?contains(StackName,'vigilo')].StackName" --output text)
  if [ -n "$STACKS" ]; then
    echo "   Found leftover stacks: $STACKS"
    for STACK in $STACKS; do
      echo "   🗑  Deleting stack: $STACK"
      aws cloudformation update-termination-protection --no-enable-termination-protection --stack-name "$STACK" --region "$REGION"  2>/dev/null || true
      aws cloudformation delete-stack --stack-name "$STACK" --region "$REGION" 
    done
    echo "   ⏳ Waiting for stacks to delete..."
    for STACK in $STACKS; do
      aws cloudformation wait stack-delete-complete --stack-name "$STACK" --region "$REGION"  2>/dev/null || true
    done
    echo -e "   ${GREEN}✅ Stacks deleted.${NC}"
  else
    echo "   No leftover stacks found."
  fi
  echo ""
  echo -e "${GREEN}✅ Nothing to delete. Clean state.${NC}"
  exit 0
fi

# Delete cluster with eksctl (handles VPC, subnets, everything)
echo "🗑  Deleting cluster $CLUSTER_NAME (this takes ~10 minutes)..."
echo "   eksctl will delete: nodegroup, cluster, VPC, subnets, NAT, IGW, stacks"
echo ""

eksctl delete cluster \
  --name "$CLUSTER_NAME" \
  --region "$REGION" \
  --wait

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ DESTROYED. Everything deleted.${NC}"
echo ""
echo "   • Cluster: deleted"
echo "   • Node groups: deleted"
echo "   • VPC + networking: deleted"
echo "   • CloudFormation stacks: deleted"
echo ""
echo "   To recreate: ./setup.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
