#!/bin/bash
"""
Deployment script for the automated game loading system
Handles both development and production deployments
"""

set -e  # Exit on any error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Print colored output
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }
print_info() { echo -e "📋 $1"; }

# Default environment
ENVIRONMENT=${1:-dev}

print_info "🏈 Deploying Game Loading System to $ENVIRONMENT environment"
echo "================================================================"

# Validate environment
if [[ "$ENVIRONMENT" != "dev" && "$ENVIRONMENT" != "prod" ]]; then
    print_error "Invalid environment: $ENVIRONMENT. Use 'dev' or 'prod'"
    exit 1
fi

# Check if we're in the right directory
if [[ ! -f "infrastructure/stacks/01-backend-api.yaml" ]]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Step 1: Build the SAM application
print_info "Step 1: Building SAM application..."
sam build -t infrastructure/stacks/01-backend-api.yaml
if [[ $? -eq 0 ]]; then
    print_success "SAM build completed"
else
    print_error "SAM build failed"
    exit 1
fi

# Step 2: Deploy the backend stack
print_info "Step 2: Deploying backend stack to $ENVIRONMENT..."

# Get database URL from parameter store
DATABASE_URL=$(aws ssm get-parameter --name "/pick6/$ENVIRONMENT/database-url" --with-decryption --query "Parameter.Value" --output text 2>/dev/null)
if [[ -z "$DATABASE_URL" ]]; then
    print_error "Could not retrieve database URL for $ENVIRONMENT environment"
    print_warning "Make sure Parameter Store is set up: /pick6/$ENVIRONMENT/database-url"
    exit 1
fi

sam deploy \
    --stack-name "pick6-backend-$ENVIRONMENT" \
    --capabilities CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
        DatabaseUrl="$DATABASE_URL" \
    --region us-east-2 \
    --resolve-s3 \
    --no-confirm-changeset

if [[ $? -eq 0 ]]; then
    print_success "Backend deployment completed"
else
    print_error "Backend deployment failed"
    exit 1
fi

# Step 3: Test the new endpoints
print_info "Step 3: Testing new game loading endpoints..."

# Determine API URL based on environment
if [[ "$ENVIRONMENT" == "prod" ]]; then
    API_URL="https://api.cfbpick6.com"
else
    API_URL="https://dev-api.cfbpick6.com"
fi

# Test bulk games load endpoint
print_info "Testing bulk games load endpoint..."
BULK_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X OPTIONS "$API_URL/admin/games/load")
BULK_STATUS=$(echo "$BULK_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)

if [[ "$BULK_STATUS" == "200" ]]; then
    print_success "Bulk games load endpoint is accessible"
else
    print_warning "Bulk games load endpoint returned status: $BULK_STATUS"
fi

# Test scheduled games endpoint
print_info "Testing scheduled games endpoint..."
SCHEDULED_RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X OPTIONS "$API_URL/admin/games/scheduled")
SCHEDULED_STATUS=$(echo "$SCHEDULED_RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)

if [[ "$SCHEDULED_STATUS" == "200" ]]; then
    print_success "Scheduled games endpoint is accessible"
else
    print_warning "Scheduled games endpoint returned status: $SCHEDULED_STATUS"
fi

# Step 4: Check EventBridge rules
print_info "Step 4: Verifying EventBridge scheduling rules..."

# List EventBridge rules for this stack
RULES=$(aws events list-rules --name-prefix "pick6-admin-games-scheduled-$ENVIRONMENT" --query "Rules[].Name" --output text 2>/dev/null)
if [[ -n "$RULES" ]]; then
    print_success "EventBridge rules found: $RULES"
    
    # Check if rules are enabled
    for rule in $RULES; do
        STATE=$(aws events describe-rule --name "$rule" --query "State" --output text 2>/dev/null)
        if [[ "$STATE" == "ENABLED" ]]; then
            print_success "Rule $rule is ENABLED"
        else
            print_warning "Rule $rule is in state: $STATE"
        fi
    done
else
    print_warning "No EventBridge rules found - they may be created with different naming"
fi

# Step 5: Show next steps
echo ""
print_info "🎉 Deployment completed successfully!"
echo "================================================================"
print_info "Next Steps:"
echo ""
echo "1. 📊 Initial Data Loading (run once per season):"
echo "   curl -X POST $API_URL/admin/games/load \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"seasons\": [\"2024\", \"2025\"]}'"
echo ""
echo "2. 🔄 Manual Scheduled Update (for testing):"
echo "   curl -X POST $API_URL/admin/games/scheduled \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"season\": 2025}'"
echo ""
echo "3. 📈 Monitor Lambda Functions:"
echo "   aws logs tail /aws/lambda/pick6-admin-games-scheduled-$ENVIRONMENT --follow"
echo ""
echo "4. ⚙️ Check EventBridge Execution:"
echo "   aws logs filter-log-events \\"
echo "     --log-group-name \"/aws/lambda/pick6-admin-games-scheduled-$ENVIRONMENT\" \\"
echo "     --start-time \$(date -d '1 hour ago' +%s)000"
echo ""
print_success "🏈 Automated game loading system is now active!"

print_info "📅 Schedule Summary:"
echo "   • Saturdays: Every 10 minutes (6 AM - 11 PM UTC / 12 AM - 5 PM CST)"
echo "   • All days: Every hour"
echo "   • Current week games only (efficient API usage)"
