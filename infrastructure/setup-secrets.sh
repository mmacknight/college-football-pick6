#!/bin/bash

# Pick6 Parameter Store Secrets Setup
# Usage: ./setup-secrets.sh [dev|prod]

set -e

# Configuration
ENVIRONMENT=${1:-dev}
REGION="us-east-2"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔐 Setting up Pick6 Parameter Store secrets for ${ENVIRONMENT}${NC}"
echo "Region: ${REGION}"
echo

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo -e "${RED}❌ AWS CLI not configured. Run 'aws configure' first.${NC}"
    exit 1
fi

# Function to create or update parameter
create_parameter() {
    local param_name=$1
    local param_value=$2
    local param_description=$3
    
    echo -e "${YELLOW}📝 Setting parameter: ${param_name}${NC}"
    
    # Try to create the parameter
    aws ssm put-parameter \
        --name "${param_name}" \
        --value "${param_value}" \
        --type "SecureString" \
        --description "${param_description}" \
        --region ${REGION} \
        --overwrite > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Parameter ${param_name} set successfully${NC}"
    else
        echo -e "${RED}❌ Failed to set parameter ${param_name}${NC}"
        exit 1
    fi
}

# Set up parameters based on environment
if [ "$ENVIRONMENT" = "dev" ]; then
    echo -e "${BLUE}Setting up development environment parameters...${NC}"
    
    # JWT Secret for dev
    create_parameter \
        "/pick6/dev/jwt-secret" \
        "dev-jwt-secret-$(date +%s)" \
        "JWT secret for Pick6 development environment"
    
    # CFB API Key (you'll need to provide this)
    echo -e "${YELLOW}⚠️  Please enter your CollegeFootballData.com API key:${NC}"
    read -s cfb_api_key
    create_parameter \
        "/pick6/dev/cfb-api-key" \
        "${cfb_api_key}" \
        "CollegeFootballData.com API key for development"
    
    # Database URL (Neon dev database)
    echo -e "${YELLOW}⚠️  Please enter your Neon development database URL:${NC}"
    echo -e "${BLUE}Format: postgresql://username:password@host:5432/pick6_dev${NC}"
    read -s database_url
    create_parameter \
        "/pick6/dev/database-url" \
        "${database_url}" \
        "Neon PostgreSQL database URL for development"

elif [ "$ENVIRONMENT" = "prod" ]; then
    echo -e "${BLUE}Setting up production environment parameters...${NC}"
    echo -e "${RED}⚠️  PRODUCTION ENVIRONMENT - USE STRONG SECRETS!${NC}"
    
    # JWT Secret for prod (generate a strong one)
    jwt_secret=$(openssl rand -base64 32)
    create_parameter \
        "/pick6/prod/jwt-secret" \
        "${jwt_secret}" \
        "JWT secret for Pick6 production environment"
    
    # CFB API Key
    echo -e "${YELLOW}⚠️  Please enter your CollegeFootballData.com API key for PRODUCTION:${NC}"
    read -s cfb_api_key
    create_parameter \
        "/pick6/prod/cfb-api-key" \
        "${cfb_api_key}" \
        "CollegeFootballData.com API key for production"
    
    # Database URL (Neon prod database)
    echo -e "${YELLOW}⚠️  Please enter your Neon PRODUCTION database URL:${NC}"
    echo -e "${BLUE}Format: postgresql://username:password@host:5432/pick6_prod${NC}"
    read -s database_url
    create_parameter \
        "/pick6/prod/database-url" \
        "${database_url}" \
        "Neon PostgreSQL database URL for production"
else
    echo -e "${RED}❌ Invalid environment. Use 'dev' or 'prod'${NC}"
    exit 1
fi

echo
echo -e "${GREEN}🎉 Parameter Store setup completed successfully!${NC}"
echo
echo -e "${YELLOW}📋 Created parameters:${NC}"
aws ssm describe-parameters \
    --parameter-filters "Key=Name,Option=BeginsWith,Values=/pick6/${ENVIRONMENT}/" \
    --region ${REGION} \
    --query 'Parameters[*].[Name,Description]' \
    --output table

echo
echo -e "${GREEN}✅ Secrets are now ready for deployment!${NC}"
echo -e "${YELLOW}Next step: Run ./deploy-backend.sh ${ENVIRONMENT}${NC}"
