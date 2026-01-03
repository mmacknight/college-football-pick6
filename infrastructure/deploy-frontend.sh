#!/bin/bash

# Pick6 Frontend Deployment Script
# Usage: ./deploy-frontend.sh [dev|prod]

set -e

ENVIRONMENT=${1:-dev}
REGION=$(aws configure get region)

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}📱 Deploying Pick6 Frontend - ${ENVIRONMENT}${NC}"

# Get bucket name from CloudFormation
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name "pick6-frontend-${ENVIRONMENT}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebsiteBucketName`].OutputValue' \
    --output text)

if [ -z "$BUCKET_NAME" ]; then
    echo -e "${RED}❌ Could not find S3 bucket. Deploy infrastructure first.${NC}"
    exit 1
fi

# Get API URL for frontend config - use custom domain
if [ "$ENVIRONMENT" == "prod" ]; then
    API_URL="https://api.cfbpick6.com"
else
    API_URL="https://dev-api.cfbpick6.com"
fi

# Get WebSocket URL
WEBSOCKET_URL=$(aws cloudformation describe-stacks \
    --stack-name "pick6-backend-${ENVIRONMENT}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebSocketUrl`].OutputValue' \
    --output text)

echo -e "${YELLOW}🔧 Configuration:${NC}"
echo "API URL: ${API_URL}"
echo "WebSocket URL: ${WEBSOCKET_URL}"
echo "S3 Bucket: ${BUCKET_NAME}"
echo

# Update frontend config
cd ../web-app

# Create production config
cat > src/config/config.js << EOF
// Auto-generated configuration for ${ENVIRONMENT}
const config = {
  API_BASE_URL: '${API_URL}',
  WEBSOCKET_URL: '${WEBSOCKET_URL}',
  ENVIRONMENT: '${ENVIRONMENT}'
};

export default config;
EOF

echo -e "${YELLOW}🔨 Building React application...${NC}"
npm run build

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed${NC}"
    exit 1
fi

echo -e "${YELLOW}📤 Uploading to S3...${NC}"
aws s3 sync dist/ s3://${BUCKET_NAME}/ --delete --cache-control "public, max-age=31536000" --exclude "*.html"
aws s3 cp dist/index.html s3://${BUCKET_NAME}/index.html --cache-control "public, max-age=0, must-revalidate"

# Get CloudFront distribution ID for cache invalidation
DISTRIBUTION_ID=$(aws cloudformation describe-stacks \
    --stack-name "pick6-frontend-${ENVIRONMENT}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`CloudFrontDistributionId`].OutputValue' \
    --output text)

echo -e "${YELLOW}🔄 Invalidating CloudFront cache...${NC}"
aws cloudfront create-invalidation \
    --distribution-id "${DISTRIBUTION_ID}" \
    --paths "/*" > /dev/null

echo -e "${GREEN}✅ Frontend deployment complete!${NC}"

# Get the final URL
WEBSITE_URL=$(aws cloudformation describe-stacks \
    --stack-name "pick6-frontend-${ENVIRONMENT}" \
    --region "${REGION}" \
    --query 'Stacks[0].Outputs[?OutputKey==`WebsiteURL`].OutputValue' \
    --output text)

echo
echo -e "${GREEN}🌍 Your app is live at: ${WEBSITE_URL}${NC}"
echo
echo -e "${YELLOW}💡 Note: CloudFront cache invalidation takes 5-15 minutes to propagate globally${NC}"

cd ..
