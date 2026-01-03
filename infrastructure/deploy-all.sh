#!/bin/bash

# Pick6 Complete Deployment Script
# Usage: ./deploy-all.sh [dev|prod]

set -e

# Configuration
ENVIRONMENT=${1:-dev}
DOMAIN_NAME="cfbpick6.com"
YOUR_EMAIL="your-email@example.com"  # UPDATE THIS!

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}🚀 Complete Pick6 Deployment - ${ENVIRONMENT} Environment${NC}"
echo -e "${BLUE}Domain: ${DOMAIN_NAME}${NC}"
echo -e "${BLUE}Budget: \$50/month${NC}"
echo

# Check AWS CLI
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI not configured${NC}"
    exit 1
fi

# Get current region
REGION=$(aws configure get region)
echo -e "${BLUE}Current region: ${REGION}${NC}"

# Function to deploy a stack
deploy_stack() {
    local stack_name=$1
    local template_file=$2
    local region=$3
    local params=$4
    
    echo -e "${YELLOW}📦 Deploying ${stack_name}...${NC}"
    
    aws cloudformation deploy \
        --template-file "${template_file}" \
        --stack-name "${stack_name}" \
        --region "${region}" \
        --capabilities CAPABILITY_IAM \
        --parameter-overrides ${params} \
        --no-fail-on-empty-changeset
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ ${stack_name} deployed successfully${NC}"
    else
        echo -e "${RED}❌ ${stack_name} deployment failed${NC}"
        exit 1
    fi
}

# Step 1: Use existing SSL Certificate  
echo -e "${YELLOW}🔐 Step 1: Using Existing SSL Certificate${NC}"
# Use existing certificate ARN (covers cfbpick6.com and www.cfbpick6.com)
CERT_ARN="arn:aws:acm:us-east-1:085104278407:certificate/8f012300-1d66-4616-a910-4419728d3335"
echo -e "${GREEN}📋 Using Certificate ARN: ${CERT_ARN}${NC}"

# Step 2: Deploy backend
echo -e "${YELLOW}🔧 Step 2: Backend API${NC}"
cd backend
sam build --template-file ../infrastructure/stacks/01-backend-api.yaml

sam deploy \
    --template-file ../infrastructure/stacks/01-backend-api.yaml \
    --stack-name "pick6-backend-${ENVIRONMENT}" \
    --region "${REGION}" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
        Environment=${ENVIRONMENT} \
        DatabaseUrl="postgresql://user:pass@placeholder.neon.tech:5432/pick6db" \
    --confirm-changeset \
    --no-fail-on-empty-changeset

cd ..

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend deployed successfully${NC}"
else
    echo -e "${RED}❌ Backend deployment failed${NC}"
    exit 1
fi

# Get API Gateway URL
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "pick6-backend-${ENVIRONMENT}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
    --output text)

echo -e "${GREEN}🔗 API URL: ${API_URL}${NC}"

# Step 3: Deploy frontend
echo -e "${YELLOW}🌐 Step 3: Frontend Hosting${NC}"
deploy_stack \
    "pick6-frontend-${ENVIRONMENT}" \
    "stacks/02-frontend-hosting.yaml" \
    "${REGION}" \
    "Environment=${ENVIRONMENT} DomainName=${DOMAIN_NAME} CertificateArn=${CERT_ARN}"

# Get frontend URLs
CLOUDFRONT_URL=$(aws cloudformation describe-stacks \
    --stack-name "pick6-frontend-${ENVIRONMENT}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDomainName`].OutputValue' \
    --output text)

BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name "pick6-frontend-${ENVIRONMENT}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebsiteBucketName`].OutputValue' \
    --output text)

echo -e "${GREEN}🌍 CloudFront URL: https://${CLOUDFRONT_URL}${NC}"

# Step 4: Deploy monitoring
echo -e "${YELLOW}📊 Step 4: Monitoring & Budgets${NC}"
deploy_stack \
    "pick6-monitoring" \
    "stacks/03-monitoring.yaml" \
    "${REGION}" \
    "BudgetLimit=50 AlertEmail=${YOUR_EMAIL}"

echo
echo -e "${GREEN}🎉 DEPLOYMENT COMPLETE! 🎉${NC}"
echo
echo -e "${YELLOW}📋 Summary:${NC}"
echo -e "${GREEN}Frontend:${NC} https://${CLOUDFRONT_URL}"
echo -e "${GREEN}API:${NC} ${API_URL}"
echo -e "${GREEN}S3 Bucket:${NC} ${BUCKET_NAME}"
echo
echo -e "${YELLOW}🔧 Next Steps:${NC}"
echo "1. Set up Neon database and update Parameter Store:"
echo "   aws ssm put-parameter --name '/pick6/${ENVIRONMENT}/database-url' --value 'postgresql://user:pass@your-neon.neon.tech:5432/pick6db' --type 'SecureString' --overwrite"
echo
echo "2. Build and deploy your React app:"
echo "   cd web-app && npm run build"
echo "   aws s3 sync dist/ s3://${BUCKET_NAME}/ --delete"
echo
echo "3. Update your DNS at your registrar to point to:"
if [ "$ENVIRONMENT" = "prod" ]; then
    HOSTED_ZONE_ID=$(aws cloudformation describe-stacks \
        --stack-name "pick6-certificates" \
        --region "us-east-1" \
        --query 'Stacks[0].Outputs[?OutputKey==`HostedZoneId`].OutputValue' \
        --output text)
    
    NAME_SERVERS=$(aws cloudformation describe-stacks \
        --stack-name "pick6-certificates" \
        --region "us-east-1" \
        --query 'Stacks[0].Outputs[?OutputKey==`NameServers`].OutputValue' \
        --output text)
    
    echo "   ${NAME_SERVERS}"
fi
echo
echo -e "${GREEN}✅ Your Pick6 app is ready for $50/month! 🏈${NC}"
