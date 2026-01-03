#!/bin/bash

# Pick6 Old Resource Cleanup Script
# Identifies and helps remove resources from previous deployments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${YELLOW}🧹 Pick6 Old Resource Cleanup${NC}"
echo -e "${BLUE}Identifying resources without 2025 tags...${NC}"
echo

# Check current region
REGION=$(aws configure get region)
echo -e "${BLUE}Current region: ${REGION}${NC}"

# Function to list resources by service
list_untagged_resources() {
    local service=$1
    local description=$2
    
    echo -e "${YELLOW}📋 ${description}:${NC}"
}

# 1. CloudFront Distributions
echo -e "${YELLOW}🌐 CloudFront Distributions:${NC}"
DISTRIBUTIONS=$(aws cloudfront list-distributions --query "DistributionList.Items[*].[Id,Comment,Status,DomainName]" --output table 2>/dev/null || echo "None found")
echo "$DISTRIBUTIONS"
echo

# 2. API Gateway APIs  
echo -e "${YELLOW}🔌 API Gateway REST APIs:${NC}"
APIS=$(aws apigateway get-rest-apis --query "items[*].[id,name,createdDate]" --output table 2>/dev/null || echo "None found")
echo "$APIS"
echo

# 3. API Gateway WebSocket APIs
echo -e "${YELLOW}🔌 API Gateway WebSocket APIs:${NC}"
WEBSOCKET_APIS=$(aws apigatewayv2 get-apis --query "Items[*].[ApiId,Name,CreatedDate,ProtocolType]" --output table 2>/dev/null || echo "None found")
echo "$WEBSOCKET_APIS"
echo

# 4. Lambda Functions (excluding 2025 tagged ones)
echo -e "${YELLOW}⚡ Lambda Functions:${NC}"
FUNCTIONS=$(aws lambda list-functions --query "Functions[*].[FunctionName,Runtime,LastModified]" --output table 2>/dev/null || echo "None found")
echo "$FUNCTIONS"
echo

# 5. S3 Buckets
echo -e "${YELLOW}🪣 S3 Buckets:${NC}"
BUCKETS=$(aws s3api list-buckets --query "Buckets[*].[Name,CreationDate]" --output table 2>/dev/null || echo "None found")
echo "$BUCKETS"
echo

# 6. Route 53 Records (focusing on cfbpick6.com)
echo -e "${YELLOW}🌍 Route 53 Records for cfbpick6.com:${NC}"
HOSTED_ZONE_ID="Z02999291RLQ564DKGT1U"
aws route53 list-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID --query "ResourceRecordSets[?Type=='A' || Type=='CNAME'].[Name,Type,AliasTarget.DNSName,ResourceRecords[0].Value]" --output table 2>/dev/null || echo "None found"
echo

# Interactive cleanup options
echo -e "${RED}⚠️  CLEANUP OPTIONS:${NC}"
echo
echo -e "${YELLOW}Would you like to clean up any of these resources? (CAREFUL!)${NC}"
echo "1. Delete old CloudFront distribution (d2db0anb4sjukm.cloudfront.net)"
echo "2. List and delete old API Gateway APIs"
echo "3. List and delete old Lambda functions"
echo "4. Show Route 53 records to update"
echo "5. Exit (recommended - review first)"
echo

read -p "Enter your choice (1-5): " choice

case $choice in
    1)
        echo -e "${YELLOW}🌐 CloudFront Distribution Cleanup${NC}"
        echo "Old distribution: d2db0anb4sjukm.cloudfront.net"
        echo -e "${RED}⚠️  This will break the current website!${NC}"
        read -p "Are you sure? Type 'DELETE' to confirm: " confirm
        if [ "$confirm" = "DELETE" ]; then
            # First need to disable the distribution
            echo "Disabling distribution first..."
            # Get distribution ID
            DIST_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?DomainName=='d2db0anb4sjukm.cloudfront.net'].Id" --output text)
            if [ ! -z "$DIST_ID" ]; then
                echo "Distribution ID: $DIST_ID"
                echo "You'll need to:"
                echo "1. Update the A record in Route 53 to point away from this distribution"
                echo "2. Disable the distribution in CloudFront console"
                echo "3. Wait for it to deploy (15-20 minutes)"
                echo "4. Then delete it"
            fi
        else
            echo "Cancelled."
        fi
        ;;
    2)
        echo -e "${YELLOW}🔌 API Gateway Cleanup${NC}"
        echo "Found APIs:"
        aws apigateway get-rest-apis --query "items[*].[id,name,description]" --output table
        echo
        echo "To delete an API, run:"
        echo "aws apigateway delete-rest-api --rest-api-id <API_ID>"
        ;;
    3)
        echo -e "${YELLOW}⚡ Lambda Function Cleanup${NC}"
        echo "Found functions:"
        aws lambda list-functions --query "Functions[*].[FunctionName,Description]" --output table
        echo
        echo "To delete a function, run:"
        echo "aws lambda delete-function --function-name <FUNCTION_NAME>"
        ;;
    4)
        echo -e "${YELLOW}🌍 Route 53 Records${NC}"
        echo "Current A records for cfbpick6.com:"
        aws route53 list-resource-record-sets --hosted-zone-id $HOSTED_ZONE_ID --query "ResourceRecordSets[?Type=='A']"
        echo
        echo "You'll need to update these to point to your new CloudFront distribution"
        echo "after deployment."
        ;;
    5)
        echo -e "${GREEN}✅ Good choice! Review resources first.${NC}"
        echo
        echo -e "${YELLOW}💡 Recommended approach:${NC}"
        echo "1. Deploy new 2025 infrastructure with tags"
        echo "2. Test everything works"
        echo "3. Update Route 53 to point to new CloudFront"
        echo "4. Then clean up old resources"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        ;;
esac

echo
echo -e "${GREEN}📋 Resource Identification Complete${NC}"
echo -e "${YELLOW}💡 All new 2025 resources will be tagged with:${NC}"
echo "  Project: Pick6-CollegeFootball"
echo "  Version: 2025"
echo "  Repository: https://github.com/mmacknight/college-football-pick6"
