#!/bin/bash
# Production Deployment Script for Family Members API Fix
# This script deploys the backend changes to production

set -e  # Exit on any error

echo "=================================================="
echo "Family Members API Fix - Production Deployment"
echo "=================================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Connecting to production server...${NC}"
ssh root@freshlybackend.duckdns.org << 'ENDSSH'

echo ""
echo "Connected to production server"
echo ""

# Navigate to backend directory
cd /root/FreshlyBackend

echo "Step 2: Backing up current code..."
git stash
echo "✓ Code backed up"
echo ""

echo "Step 3: Pulling latest changes from GitHub..."
git pull origin main
echo "✓ Latest code pulled"
echo ""

echo "Step 4: Checking Python dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies up to date"
echo ""

echo "Step 5: Restarting FastAPI service..."
systemctl restart freshly-backend
echo "✓ Service restarted"
echo ""

echo "Step 6: Waiting for service to start..."
sleep 5
echo ""

echo "Step 7: Checking service status..."
if systemctl is-active --quiet freshly-backend; then
    echo "✓ Service is running"
else
    echo "✗ Service failed to start!"
    systemctl status freshly-backend
    exit 1
fi
echo ""

echo "Step 8: Testing the endpoint..."
# Test if the API is responding
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo "✓ API is responding"
else
    echo "✗ API health check failed!"
    exit 1
fi
echo ""

echo "Step 9: Viewing recent logs..."
journalctl -u freshly-backend -n 20 --no-pager
echo ""

echo "=================================================="
echo "✓ Deployment Complete!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Test the endpoint: GET /families/{family_id}/members"
echo "2. Verify it returns nested user objects"
echo "3. Update frontend to use member.user.* syntax"
echo ""

ENDSSH

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo ""
echo "You can monitor logs with:"
echo "ssh root@freshlybackend.duckdns.org 'journalctl -u freshly-backend -f'"
