# 🚀 Setup VPS cho Nosara Blue Scraper API

## 📋 Yêu cầu VPS:
- **OS**: Ubuntu 20.04+ hoặc Debian 11+
- **RAM**: Tối thiểu 2GB (khuyến nghị 4GB)
- **Storage**: 20GB+
- **CPU**: 2 cores+

## 🔧 Bước 1: Chuẩn bị VPS

### 1.1 Tạo VPS (DigitalOcean, Vultr, Linode, etc.)
```bash
# SSH vào VPS
ssh root@YOUR_VPS_IP
```

### 1.2 Upload code lên VPS
```bash
# Tạo thư mục project
mkdir -p /opt/nosara-scraper
cd /opt/nosara-scraper

# Upload files (từ máy local)
scp main.py requirements.txt setup_vps.sh root@YOUR_VPS_IP:/opt/nosara-scraper/
```

## 🛠️ Bước 2: Chạy Setup Script

```bash
# SSH vào VPS
ssh root@YOUR_VPS_IP

# Chạy setup script
cd /opt/nosara-scraper
chmod +x setup_vps.sh
./setup_vps.sh
```

## ✅ Bước 3: Kiểm tra API

```bash
# Kiểm tra service status
sudo systemctl status nosara-scraper

# Xem logs
sudo journalctl -u nosara-scraper -f

# Test API
curl http://YOUR_VPS_IP:8000/
```

## 🔧 Bước 4: Cấu hình n8n

### 4.1 Workflow trong n8n:

#### Node 1: HTTP Request (Trigger Scraping)
```
Method: POST
URL: http://YOUR_VPS_IP:8000/scrape
```

#### Node 2: Wait (Optional)
```
Wait for: 30 seconds
```

#### Node 3: HTTP Request (Check Status)
```
Method: GET
URL: http://YOUR_VPS_IP:8000/status
```

#### Node 4: IF Node (Check if completed)
```
Condition: {{ $json.is_running == false }}
```

#### Node 5: HTTP Request (Get Data)
```
Method: GET
URL: http://YOUR_VPS_IP:8000/data
```

### 4.2 Workflow Logic:
1. **Trigger scraping** → POST `/scrape`
2. **Wait 30s** → để scraper chạy
3. **Check status** → GET `/status`
4. **If completed** → GET `/data`
5. **Process data** → Xử lý JSON response

## 📊 API Endpoints:

### 1. **GET /** - Home
```bash
curl http://YOUR_VPS_IP:8000/
```
**Response:**
```json
{
  "message": "Nosara Blue Classes Scraper API",
  "status": "running",
  "endpoints": {
    "/scrape": "POST - Trigger scraping",
    "/status": "GET - Get scraping status",
    "/data": "GET - Get latest data"
  }
}
```

### 2. **POST /scrape** - Trigger Scraping
```bash
curl -X POST http://YOUR_VPS_IP:8000/scrape
```
**Response:**
```json
{
  "success": true,
  "message": "Đã bắt đầu scraping",
  "status": {
    "is_running": true,
    "last_run": null,
    "total_classes": 0,
    "error": null
  }
}
```

### 3. **GET /status** - Check Status
```bash
curl http://YOUR_VPS_IP:8000/status
```
**Response:**
```json
{
  "is_running": false,
  "last_run": "2025-01-27T10:30:00",
  "total_classes": 45,
  "error": null
}
```

### 4. **GET /data** - Get Data
```bash
curl http://YOUR_VPS_IP:8000/data
```
**Response:**
```json
{
  "success": true,
  "total_classes": 45,
  "data": [
    {
      "event_date": "2025-01-27",
      "start_time": "09:00",
      "end_time": "10:00",
      "title": "Mat Pilates",
      "instructor": "Laura Murillo",
      "location": "Nosara Blue",
      "source_url": "https://www.nosarablue.com/classes",
      "description": "Mat Pilates - 1 hr - 50 spots available",
      "category": "",
      "tags": ""
    }
  ]
}
```

## 🔧 Quản lý Service:

```bash
# Start service
sudo systemctl start nosara-scraper

# Stop service
sudo systemctl stop nosara-scraper

# Restart service
sudo systemctl restart nosara-scraper

# Check status
sudo systemctl status nosara-scraper

# View logs
sudo journalctl -u nosara-scraper -f

# View recent logs
sudo journalctl -u nosara-scraper -n 50
```

## 🔒 Bảo mật:

### 1. Thêm Authentication (Optional)
```bash
# Tạo API key
echo "YOUR_API_KEY" > /opt/nosara-scraper/api_key.txt
```

### 2. Setup Nginx Reverse Proxy (Optional)
```bash
# Install nginx
sudo apt install nginx

# Create nginx config
sudo nano /etc/nginx/sites-available/nosara-scraper
```

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/nosara-scraper /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🚨 Troubleshooting:

### 1. Service không start
```bash
# Check logs
sudo journalctl -u nosara-scraper -f

# Check Python path
which python3.11

# Check dependencies
pip list
```

### 2. Playwright lỗi
```bash
# Reinstall Playwright
playwright install --force chromium

# Check system dependencies
ldd $(which chromium)
```

### 3. Port 8000 bị block
```bash
# Check firewall
sudo ufw status

# Allow port
sudo ufw allow 8000/tcp
```

## 📞 Support:
- **Logs**: `sudo journalctl -u nosara-scraper -f`
- **Status**: `sudo systemctl status nosara-scraper`
- **Restart**: `sudo systemctl restart nosara-scraper`
