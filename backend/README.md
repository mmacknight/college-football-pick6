# Pick6 Backend - Local Development Setup

## 🚀 Quick Start

### 1. Clone and Setup
```bash
cd backend
cp local-env.json.template local-env.json
```

### 2. Configure Environment Variables
Edit `local-env.json` with your actual values:
```json
{
  "Parameters": {
    "DATABASE_URL": "postgresql://pick6admin:pick6password@localhost:5432/pick6db",
    "JWT_SECRET": "your-secure-jwt-secret-here",
    "CFB_API_KEY": "your-collegefoootballdata-api-key"
  }
}
```

### 3. Get CollegeFootballData.com API Key
1. Visit: https://collegefootballdata.com/
2. Sign up for free account
3. Get your API key from the dashboard
4. Add it to `local-env.json`

### 4. Start Local Development
```bash
./start-local.sh        # Starts PostgreSQL + SAM local API
```

## 🗄️ Database Setup
```bash
# Load initial data (one-time setup)
python scripts/load_schools.py    # Load 134 FBS teams
python scripts/load_games.py      # Load game data for current season
```

## 🔑 Environment Variables Required

- `DATABASE_URL`: PostgreSQL connection string
- `JWT_SECRET`: Secret key for JWT token signing
- `CFB_API_KEY`: CollegeFootballData.com API key for game data

## 📋 API Endpoints
Backend runs on `http://127.0.0.1:3001` with 20+ endpoints for:
- Authentication (`/auth/login`, `/auth/signup`)
- League Management (`/leagues/*`)
- Draft System (`/teams/select`, `/leagues/*/draft-*`)
- Standings & Games (`/leagues/*/standings`, `/leagues/*/games/*`)

## 🚨 Security Note
Never commit `local-env.json` to version control - it contains sensitive API keys!