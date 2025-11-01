#!/bin/bash
# Production deployment script - Run this on the production server

set -e  # Exit on error

echo "🚀 Starting production deployment..."

# 1. Navigate to application directory
cd ~/FreshlyBackend

# 2. Stop the service
echo "⏸️  Stopping service..."
sudo systemctl stop freshly.service

# 3. Pull latest changes
echo "📥 Pulling latest code..."
git fetch origin
git reset --hard origin/main

# 4. Activate virtual environment and update dependencies
echo "📦 Updating dependencies..."
source .venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt

# 5. Apply database migrations
echo "🗄️  Applying database migrations..."
alembic upgrade head

# 6. Add OpenAI API key to .env if not present
echo "🔑 Checking environment variables..."
if ! grep -q "OPENAI_API_KEY" .env; then
    echo "OPENAI_API_KEY=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" >> .env
    echo "✅ Added OPENAI_API_KEY to .env"
else
    echo "✅ OPENAI_API_KEY already present in .env"
fi

# 7. Start the service
echo "▶️  Starting service..."
sudo systemctl start freshly.service

# 8. Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 5

# 9. Check service status
echo "🔍 Checking service status..."
sudo systemctl status freshly.service --no-pager -l

# 10. Test the API
echo "🧪 Testing API..."
sleep 2
curl -s http://localhost:8000/health | jq '.'

echo ""
echo "✅ Deployment complete!"
echo "🌐 Test external access: curl https://freshlybackend.duckdns.org/health"
