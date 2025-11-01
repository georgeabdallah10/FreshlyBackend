# Production Deployment Steps

## Current Status
- ✅ Backend code has been pushed to GitHub
- ✅ Fixed OPENAI_API_KEY configuration issue  
- ✅ Fixed users table updated_at column issue
- ❌ Service not starting on production server

## Required Actions on Production Server

### 1. Connect to Production Server
```bash
ssh root@freshlybackend.duckdns.org
```

### 2. Navigate to Application Directory
```bash
cd ~/FreshlyBackend
```

### 3. Pull Latest Changes
```bash
git pull origin main
```

### 4. Apply Database Migration
```bash
# Activate virtual environment
source .venv/bin/activate

# Apply the migration for updated_at column
python -m alembic upgrade head
```

### 5. Add OpenAI API Key to Environment (Optional)
```bash
# Edit the .env file to add OpenAI API key
nano .env

# Add this line (if you want AI features enabled):
OPENAI_API_KEY=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
```

### 6. Restart the Service
```bash
systemctl restart freshly.service
```

### 7. Check Service Status
```bash
# Check if service is running
systemctl status freshly.service

# Check recent logs
journalctl -u freshly.service -n 20 --no-pager

# Check if API is responding
curl http://localhost:8000/health
```

### 8. Verify External Access
```bash
curl https://freshlybackend.duckdns.org/health
```

## Issues Fixed in This Update

1. **Database Error**: Added `updated_at` column to users table to fix trigger error
2. **Configuration Error**: Made `OPENAI_API_KEY` properly optional to allow startup without it
3. **Service Stability**: Enhanced error handling for missing API keys

## Expected Result
After these steps, the service should start successfully and respond with:
```json
{"status":"healthy","app":"Freshly API","env":"local"}
```

## AI Features Status
- **With OpenAI API Key**: All AI features (chat, image generation, grocery scanning) will work
- **Without OpenAI API Key**: Service will start but AI endpoints will return 503 errors with helpful messages

## Database Migration Details
The migration adds an `updated_at` column to the `users` table:
- **Migration File**: `53525018d25f_add_updated_at_to_users.py`
- **SQL**: `ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now()`
- **Trigger**: Uses existing `update_updated_at_column()` trigger
