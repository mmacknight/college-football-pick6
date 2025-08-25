# Pick6 - College Fantasy Football

Draft college teams, earn points for wins. Simple and fun.

## Project Structure

```
ios_pick6/
├── ios-app/               # SwiftUI iOS application
├── backend/               # AWS Lambda functions and infrastructure
│   ├── lambdas/          # Python Lambda functions
│   └── infrastructure/   # SAM/CloudFormation templates
├── plan.txt              # Project planning and decisions
└── README.md             # This file
```

## Tech Stack

- **Frontend**: SwiftUI iOS app
- **Backend**: AWS Lambda + API Gateway + DynamoDB
- **Auth**: AWS Cognito (email/password)
- **Data**: CollegeFootballData.com API

## Getting Started

1. Set up AWS credentials
2. Deploy backend infrastructure
3. Open iOS project in Xcode
4. Configure API endpoints
5. Build and run

## Data Source

Using the free CollegeFootballData.com API for:
- Team information
- Game results and scores
- Conference data 