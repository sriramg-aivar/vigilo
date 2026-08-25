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
  --wait 2>&1 || true

# --- Force cleanup stuck resources (VPC endpoints, ENIs, subnets) ---
echo ""
echo "🧹 Cleaning up any stuck resources..."

# Find the VPC created by eksctl (tagged with cluster name)
VPC_ID=$(aws ec2 describe-vpcs --region "$REGION" \
  --filters "Name=tag:alpha.eksctl.io/cluster-name,Values=$CLUSTER_NAME" \
  --query "Vpcs[0].VpcId" --output text 2>/dev/null || echo "None")

if [ "$VPC_ID" != "None" ] && [ -n "$VPC_ID" ]; then
  echo "   Found stuck VPC: $VPC_ID"

  # Delete VPC endpoints
  echo "   Deleting VPC endpoints..."
  ENDPOINTS=$(aws ec2 describe-vpc-endpoints --region "$REGION" \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "VpcEndpoints[].VpcEndpointId" --output text 2>/dev/null || echo "")
  for EP in $ENDPOINTS; do
    aws ec2 delete-vpc-endpoints --vpc-endpoint-ids "$EP" --region "$REGION" 2>/dev/null || true
    echo "     Deleted endpoint: $EP"
  done

  # Delete network interfaces
  echo "   Deleting network interfaces..."
  ENIS=$(aws ec2 describe-network-interfaces --region "$REGION" \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "NetworkInterfaces[].NetworkInterfaceId" --output text 2>/dev/null || echo "")
  for ENI in $ENIS; do
    # Detach first if attached
    ATTACH_ID=$(aws ec2 describe-network-interfaces --region "$REGION" \
      --network-interface-ids "$ENI" \
      --query "NetworkInterfaces[0].Attachment.AttachmentId" --output text 2>/dev/null || echo "None")
    if [ "$ATTACH_ID" != "None" ] && [ -n "$ATTACH_ID" ]; then
      aws ec2 detach-network-interface --attachment-id "$ATTACH_ID" --force --region "$REGION" 2>/dev/null || true
      sleep 5
    fi
    aws ec2 delete-network-interface --network-interface-id "$ENI" --region "$REGION" 2>/dev/null || true
    echo "     Deleted ENI: $ENI"
  done

  # Delete subnets
  echo "   Deleting subnets..."
  SUBNETS=$(aws ec2 describe-subnets --region "$REGION" \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "Subnets[].SubnetId" --output text 2>/dev/null || echo "")
  for SUBNET in $SUBNETS; do
    aws ec2 delete-subnet --subnet-id "$SUBNET" --region "$REGION" 2>/dev/null || true
    echo "     Deleted subnet: $SUBNET"
  done

  # Delete security groups (except default)
  echo "   Deleting security groups..."
  SGS=$(aws ec2 describe-security-groups --region "$REGION" \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "SecurityGroups[?GroupName!='default'].GroupId" --output text 2>/dev/null || echo "")
  for SG in $SGS; do
    aws ec2 delete-security-group --group-id "$SG" --region "$REGION" 2>/dev/null || true
    echo "     Deleted SG: $SG"
  done

  # Delete internet gateway
  echo "   Deleting internet gateway..."
  IGW=$(aws ec2 describe-internet-gateways --region "$REGION" \
    --filters "Name=attachment.vpc-id,Values=$VPC_ID" \
    --query "InternetGateways[0].InternetGatewayId" --output text 2>/dev/null || echo "None")
  if [ "$IGW" != "None" ] && [ -n "$IGW" ]; then
    aws ec2 detach-internet-gateway --internet-gateway-id "$IGW" --vpc-id "$VPC_ID" --region "$REGION" 2>/dev/null || true
    aws ec2 delete-internet-gateway --internet-gateway-id "$IGW" --region "$REGION" 2>/dev/null || true
    echo "     Deleted IGW: $IGW"
  fi

  # Delete NAT gateways
  echo "   Deleting NAT gateways..."
  NATS=$(aws ec2 describe-nat-gateways --region "$REGION" \
    --filter "Name=vpc-id,Values=$VPC_ID" "Name=state,Values=available" \
    --query "NatGateways[].NatGatewayId" --output text 2>/dev/null || echo "")
  for NAT in $NATS; do
    aws ec2 delete-nat-gateway --nat-gateway-id "$NAT" --region "$REGION" 2>/dev/null || true
    echo "     Deleted NAT: $NAT"
  done
  if [ -n "$NATS" ]; then
    echo "   Waiting for NAT gateways to delete (60s)..."
    sleep 60
  fi

  # Delete route tables (non-main)
  echo "   Deleting route tables..."
  RTS=$(aws ec2 describe-route-tables --region "$REGION" \
    --filters "Name=vpc-id,Values=$VPC_ID" \
    --query "RouteTables[?Associations[0].Main!=\`true\`].RouteTableId" --output text 2>/dev/null || echo "")
  for RT in $RTS; do
    # Disassociate first
    ASSOCS=$(aws ec2 describe-route-tables --region "$REGION" \
      --route-table-ids "$RT" \
      --query "RouteTables[0].Associations[?!Main].RouteTableAssociationId" --output text 2>/dev/null || echo "")
    for ASSOC in $ASSOCS; do
      aws ec2 disassociate-route-table --association-id "$ASSOC" --region "$REGION" 2>/dev/null || true
    done
    aws ec2 delete-route-table --route-table-id "$RT" --region "$REGION" 2>/dev/null || true
    echo "     Deleted RT: $RT"
  done

  # Finally delete VPC
  echo "   Deleting VPC..."
  aws ec2 delete-vpc --vpc-id "$VPC_ID" --region "$REGION" 2>/dev/null || true
  echo -e "   ${GREEN}✅ VPC $VPC_ID deleted.${NC}"
else
  echo "   No stuck VPC found. Clean."
fi

# Delete any remaining CloudFormation stacks
echo ""
echo "🧹 Checking for remaining CloudFormation stacks..."
STACKS=$(aws cloudformation list-stacks --region "$REGION" \
  --stack-status-filter CREATE_COMPLETE ROLLBACK_COMPLETE DELETE_FAILED UPDATE_COMPLETE \
  --query "StackSummaries[?contains(StackName,'vigilo')].StackName" --output text 2>/dev/null || echo "")
if [ -n "$STACKS" ]; then
  for STACK in $STACKS; do
    echo "   🗑  Deleting stack: $STACK"
    aws cloudformation update-termination-protection --no-enable-termination-protection --stack-name "$STACK" --region "$REGION" 2>/dev/null || true
    aws cloudformation delete-stack --stack-name "$STACK" --region "$REGION" 2>/dev/null || true
  done
  echo "   ⏳ Waiting for stacks to delete..."
  for STACK in $STACKS; do
    aws cloudformation wait stack-delete-complete --stack-name "$STACK" --region "$REGION" 2>/dev/null || true
  done
fi

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
