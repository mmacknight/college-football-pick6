#!/bin/bash

# Pick6 Backend Deployment Script
# Usage: ./deploy-backend.sh [dev|prod]

set -e

# Configuration
ENVIRONMENT=${1:-dev}
STACK_NAME="pick6-backend-${ENVIRONMENT}"
REGION="us-east-2"
TEMPLATE_FILE="stacks/01-backend-api.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying Pick6 Backend to ${ENVIRONMENT}${NC}"
echo "Stack Name: ${STACK_NAME}"
echo "Region: ${REGION}"
echo

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI not configured. Run 'aws configure' first.${NC}"
    exit 1
fi

# Check for required parameters
if [ "$ENVIRONMENT" = "prod" ]; then
    echo -e "${YELLOW}⚠️  Production deployment requires manual parameter input for security.${NC}"
fi

# Validate template
echo -e "${YELLOW}🔍 Validating CloudFormation template...${NC}"
aws cloudformation validate-template \
    --template-body file://${TEMPLATE_FILE} \
    --region ${REGION}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Template validation passed${NC}"
else
    echo -e "${RED}❌ Template validation failed${NC}"
    exit 1
fi

# Build SAM application
echo -e "${YELLOW}🔨 Building SAM application...${NC}"
sam build --template-file ${TEMPLATE_FILE}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ SAM build completed${NC}"
else
    echo -e "${RED}❌ SAM build failed${NC}"
    exit 1
fi

# Deploy with guided mode for first deployment
echo -e "${YELLOW}🚀 Deploying CloudFormation stack...${NC}"

# Deploy using Parameter Store for secrets (much simpler!)
sam deploy \
    --template-file ${TEMPLATE_FILE} \
    --stack-name ${STACK_NAME} \
    --region ${REGION} \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment=${ENVIRONMENT} \
        DatabaseUrl="postgresql://user:pass@placeholder.neon.tech:5432/pick6db" \
    --resolve-s3 \
    --confirm-changeset \
    --no-fail-on-empty-changeset

if [ $? -eq 0 ]; then
    echo
    echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
    echo
    
    # Get outputs
    echo -e "${YELLOW}📋 Stack Outputs:${NC}"
    aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${REGION} \
        --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
        --output table
        
    echo
    echo -e "${GREEN}🔗 Your API Gateway URL:${NC}"
    aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${REGION} \
        --query 'Stacks[0].Outputs[?OutputKey==`ApiGatewayUrl`].OutputValue' \
        --output text
        
    echo
    echo -e "${GREEN}🔌 Your WebSocket URL:${NC}"
    aws cloudformation describe-stacks \
        --stack-name ${STACK_NAME} \
        --region ${REGION} \
        --query 'Stacks[0].Outputs[?OutputKey==`WebSocketUrl`].OutputValue' \
        --output text
        
else
    echo -e "${RED}❌ Deployment failed${NC}"
    exit 1
fi

echo
echo -e "${GREEN}✅ Backend deployment complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Set up your Neon database and update the DatabaseUrl parameter"
echo "2. Test your API endpoints"
echo "3. Deploy the frontend stack"
