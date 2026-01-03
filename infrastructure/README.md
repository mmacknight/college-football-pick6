# Pick6 AWS Infrastructure Deployment

## 🎯 Ultra-Budget AWS Deployment ($50/month)

Complete CloudFormation infrastructure for Pick6 college football fantasy app.

### 📦 What's Included

- **20+ Lambda Functions** (Auth, Leagues, Drafts, Standings)
- **API Gateway** with WebSocket support
- **CloudFront + S3** global CDN hosting
- **Route 53** DNS management
- **SSL Certificates** (free via AWS Certificate Manager)
- **Cost Monitoring** with $50/month budget alerts
- **Parameter Store** for secure secret management

### 💰 Cost Breakdown

```
Neon PostgreSQL (free tier):    $0/month
Lambda (within free tier):      $0-2/month  
API Gateway:                    $3-8/month
CloudFront + S3:               $1-5/month
Route 53:                      $0.50/month
DynamoDB (WebSocket):          $0/month (free tier)
Certificate Manager:           $0/month
Total: ~$4.50-15.50/month 🎯
```

## 🚀 Quick Deployment

### Prerequisites

1. **AWS CLI configured** with admin permissions
2. **SAM CLI installed** (`brew install aws-sam-cli`)
3. **Domain name** (cfbpick6.com) in Route 53

### One-Command Deployment

```bash
cd infrastructure
./deploy-all.sh dev
```

This deploys everything in the correct order:
1. SSL certificates (us-east-1)
2. Backend API (your region)
3. Frontend hosting (your region)
4. Monitoring & budgets (your region)

## 📋 Manual Step-by-Step

### 1. Deploy SSL Certificates (us-east-1 only)

```bash
aws cloudformation deploy \
  --template-file stacks/00-certificates.yaml \
  --stack-name pick6-certificates \
  --region us-east-1 \
  --parameter-overrides DomainName=cfbpick6.com
```

### 2. Deploy Backend API

```bash
cd backend
sam build --template-file ../infrastructure/stacks/01-backend-api.yaml
sam deploy \
  --template-file ../infrastructure/stacks/01-backend-api.yaml \
  --stack-name pick6-backend-dev \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides Environment=dev
```

### 3. Deploy Frontend Hosting

```bash
aws cloudformation deploy \
  --template-file stacks/02-frontend-hosting.yaml \
  --stack-name pick6-frontend-dev \
  --parameter-overrides Environment=dev DomainName=cfbpick6.com CertificateArn=<cert-arn>
```

### 4. Deploy Monitoring

```bash
aws cloudformation deploy \
  --template-file stacks/03-monitoring.yaml \
  --stack-name pick6-monitoring \
  --parameter-overrides BudgetLimit=50 AlertEmail=your-email@example.com
```

## 🔐 Secret Management

Secrets are stored in AWS Parameter Store:

```bash
# Already created for you:
/pick6/dev/cfb-api-key      # Your CollegeFootballData.com API key
/pick6/dev/jwt-secret       # Secure random JWT secret
/pick6/prod/cfb-api-key     # Same API key for prod
/pick6/prod/jwt-secret      # Different JWT secret for prod
```

### Add Database URL

```bash
aws ssm put-parameter \
  --name "/pick6/dev/database-url" \
  --value "postgresql://user:pass@your-neon.neon.tech:5432/pick6db" \
  --type "SecureString" \
  --overwrite
```

## 🌐 Frontend Deployment

After infrastructure is deployed:

```bash
./deploy-frontend.sh dev
```

This will:
1. Build your React app with correct API URLs
2. Upload to S3 with optimal caching headers
3. Invalidate CloudFront cache
4. Show you the live URL

## 📊 Monitoring

- **CloudWatch Dashboard**: Monitor Lambda, API Gateway, CloudFront
- **Budget Alerts**: Email notifications at 80% and 100% of $50 budget
- **Error Alarms**: SNS notifications for high error rates

## 🔧 Troubleshooting

### Check Stack Status
```bash
aws cloudformation describe-stacks --stack-name pick6-backend-dev
```

### View Logs
```bash
sam logs --stack-name pick6-backend-dev --tail
```

### Test API
```bash
curl https://your-api-id.execute-api.us-east-2.amazonaws.com/dev/schools
```

## 🏈 Production Deployment

For production:

```bash
./deploy-all.sh prod
```

Don't forget to:
1. Update DNS nameservers at your domain registrar
2. Set up production Neon database
3. Update Parameter Store with production database URL

## 📞 Support

- Check CloudFormation events for deployment issues
- Review CloudWatch logs for runtime errors
- Monitor costs in AWS Billing dashboard
