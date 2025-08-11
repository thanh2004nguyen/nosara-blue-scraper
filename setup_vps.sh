#!/bin/bash

echo "🚀 Setup VPS cho Nosara Blue Scraper API..."

# Update system
echo "📦 Updating system..."
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
echo "🐍 Installing Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3.11-pip

# Install system dependencies for Playwright
echo "🔧 Installing system dependencies..."
sudo apt install -y wget unzip fontconfig locales gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils

# Create project directory
echo "📁 Creating project directory..."
mkdir -p /opt/nosara-scraper
cd /opt/nosara-scraper

# Create virtual environment
echo "🔧 Creating virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "🌐 Installing Playwright browsers..."
playwright install chromium

# Create systemd service
echo "⚙️ Creating systemd service..."
sudo tee /etc/systemd/system/nosara-scraper.service > /dev/null <<EOF
[Unit]
Description=Nosara Blue Scraper API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/nosara-scraper
Environment=PATH=/opt/nosara-scraper/venv/bin
ExecStart=/opt/nosara-scraper/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "🚀 Starting service..."
sudo systemctl daemon-reload
sudo systemctl enable nosara-scraper
sudo systemctl start nosara-scraper

# Setup firewall
echo "🔥 Setting up firewall..."
sudo ufw allow 8000/tcp
sudo ufw allow ssh
sudo ufw --force enable

echo "✅ Setup completed!"
echo "🌐 API will be available at: http://YOUR_VPS_IP:8000"
echo "📊 Check status: sudo systemctl status nosara-scraper"
echo "📝 View logs: sudo journalctl -u nosara-scraper -f"
