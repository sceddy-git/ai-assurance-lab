#!/bin/bash
set -e

echo "🚀 AI Assurance Lab - EC2 Setup"
echo "================================"

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Update system
echo -e "\n${BLUE}Step 1: Updating system packages...${NC}"
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y python3.11 python3.11-venv python3-pip git curl wget

# Step 2: Clone repository
echo -e "\n${BLUE}Step 2: Cloning repository...${NC}"
cd /home/ubuntu
git clone https://github.com/your-username/ai-assurance-lab.git || {
    echo "Repository URL not set. Please update the script with your repo URL."
    exit 1
}
cd ai-assurance-lab

# Step 3: Create Python virtual environment
echo -e "\n${BLUE}Step 3: Creating Python environment...${NC}"
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Step 4: Create .env from template
echo -e "\n${BLUE}Step 4: Creating .env file...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo ""
    echo -e "${RED}⚠️  IMPORTANT: Configure your .env file!${NC}"
    echo "You can do this via the web portal Settings tab"
    echo "For now, Flask will start but won't be fully functional"
    echo ""
fi

# Step 5: Create systemd service
echo -e "\n${BLUE}Step 5: Creating systemd service...${NC}"
sudo tee /etc/systemd/system/flask-app.service > /dev/null <<EOF
[Unit]
Description=AI Assurance Lab Flask App
After=network.target

[Service]
Type=notify
User=ubuntu
WorkingDirectory=/home/ubuntu/ai-assurance-lab
Environment="PATH=/home/ubuntu/ai-assurance-lab/venv/bin"
ExecStart=/home/ubuntu/ai-assurance-lab/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 --timeout 120 app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Step 6: Install Gunicorn
echo -e "\n${BLUE}Step 6: Installing Gunicorn...${NC}"
source venv/bin/activate
pip install gunicorn

# Step 7: Enable and start service
echo -e "\n${BLUE}Step 7: Starting Flask service...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable flask-app
sudo systemctl start flask-app

# Step 8: Wait for service to start
sleep 3

# Step 9: Check if service is running
if sudo systemctl is-active --quiet flask-app; then
    echo -e "\n${GREEN}✅ Flask app is running!${NC}"
else
    echo -e "\n${RED}❌ Flask app failed to start${NC}"
    echo "Check logs with: sudo journalctl -u flask-app -n 50"
    exit 1
fi

# Step 10: Get instance IP
IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4)

# Step 11: Display completion message
echo -e "\n${GREEN}================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "🌐 Access your lab at:"
echo -e "   ${BLUE}http://${IP}${NC}"
echo ""
echo "📝 Next steps:"
echo "   1. Open the URL in your browser"
echo "   2. Log in with your Cognito account"
echo "   3. Click 'Settings' tab"
echo "   4. Configure Cognito details"
echo "   5. Configure encryption key"
echo "   6. Add proctor emails"
echo "   7. Save configuration"
echo ""
echo "📚 Upload students:"
echo "   1. Click 'Students' tab"
echo "   2. Upload CSV file"
echo "   3. Done!"
echo ""
echo "🔍 Check logs:"
echo "   sudo journalctl -u flask-app -f"
echo ""
echo "🔄 Restart Flask:"
echo "   sudo systemctl restart flask-app"
echo ""
echo "Happy teaching! 🎓"
