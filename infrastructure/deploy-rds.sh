#!/bin/bash
set -euo pipefail

# Deploy RDS PostgreSQL for Pick6
# Usage: ./deploy-rds.sh [dev|prod] [password]

ENVIRONMENT=${1:-prod}
DB_PASSWORD=${2:-}

if [ -z "$DB_PASSWORD" ]; then
  echo "❌ Error: Database password required"
  echo "Usage: ./deploy-rds.sh [dev|prod] <password>"
  echo "Example: ./deploy-rds.sh prod MySecurePassword123"
  exit 1
fi

if [ ${#DB_PASSWORD} -lt 8 ]; then
  echo "❌ Error: Password must be at least 8 characters"
  exit 1
fi

REGION=${AWS_REGION:-us-east-2}
STACK_NAME="pick6-rds-${ENVIRONMENT}"

echo "🚀 Deploying RDS PostgreSQL for Pick6 ${ENVIRONMENT}"
echo "   Region: ${REGION}"
echo "   Stack: ${STACK_NAME}"
echo ""

# Deploy the stack
aws cloudformation deploy \
  --template-file stacks/04-rds-postgres.yaml \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --parameter-overrides \
    Environment="${ENVIRONMENT}" \
    DBMasterUsername=pick6admin \
    DBMasterPassword="${DB_PASSWORD}" \
    DBName=pick6db \
  --capabilities CAPABILITY_IAM \
  --tags \
    Project=Pick6 \
    Environment="${ENVIRONMENT}" \
    ManagedBy=CloudFormation

echo ""
echo "✅ RDS stack deployed successfully!"
echo ""
echo "📊 Getting database details..."
echo ""

# Get outputs
DB_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`DatabaseEndpoint`].OutputValue' \
  --output text)

DB_PORT=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`DatabasePort`].OutputValue' \
  --output text)

VPC_ID=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`VpcId`].OutputValue' \
  --output text)

LAMBDA_SG=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`LambdaSecurityGroupId`].OutputValue' \
  --output text)

PRIVATE_SUBNETS=$(aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --region "${REGION}" \
  --query 'Stacks[0].Outputs[?OutputKey==`PrivateSubnetIds`].OutputValue' \
  --output text)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 RDS PostgreSQL Configuration"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Database Endpoint: ${DB_ENDPOINT}"
echo "🔌 Port: ${DB_PORT}"
echo "🗄️  Database Name: pick6db"
echo "👤 Username: pick6admin"
echo "🔐 Password: (stored in Parameter Store)"
echo ""
echo "🌐 VPC ID: ${VPC_ID}"
echo "🛡️  Lambda Security Group: ${LAMBDA_SG}"
echo "🔒 Private Subnets: ${PRIVATE_SUBNETS}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔗 Connection String (saved to Parameter Store)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "postgresql://pick6admin:****@${DB_ENDPOINT}/pick6db"
echo ""
echo "Retrieve the full URL with:"
echo "aws ssm get-parameter --name /pick6/${ENVIRONMENT}/database-url --with-decryption --region ${REGION} --query 'Parameter.Value' --output text"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⏱️  Estimated Setup Time: 5-10 minutes"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Wait for RDS instance to become available (~5-10 min)"
echo "   aws rds describe-db-instances --db-instance-identifier pick6-postgres-${ENVIRONMENT} --region ${REGION} --query 'DBInstances[0].DBInstanceStatus'"
echo ""
echo "2. Initialize the database schema"
echo "   cd ../backend && python scripts/init_db_schema.py"
echo ""
echo "3. Migrate data from Neon (once it's accessible)"
echo "   ./scripts/migrate_from_neon.sh ${ENVIRONMENT}"
echo ""
echo "4. Update Lambda functions to use new VPC and security group"
echo "   See: infrastructure/update-lambdas-for-rds.sh"
echo ""
echo "💰 Cost: ~\$13-15/month (FREE for 12 months with AWS Free Tier)"
echo ""
