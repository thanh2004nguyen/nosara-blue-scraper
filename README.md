# Nosara Blue Classes Scraper API

Web scraper API để thu thập dữ liệu lớp học từ trang web Nosara Blue. Có thể được gọi từ n8n hoặc các ứng dụng khác.

## 🎯 Tính năng

- **API Endpoints** để trigger scraping từ n8n
- Tự động thu thập thông tin lớp học trong 30 ngày
- Xử lý navigation giữa các tuần
- Lưu dữ liệu dưới dạng JSON
- Hỗ trợ format thời gian 24h
- Xử lý các trường hợp "No Classes Available"

## 📋 Yêu cầu

- Python 3.11
- Playwright
- Flask
- Gunicorn

## 🛠️ Cài đặt

```bash
# Clone repository
git clone <your-repo-url>
cd nosara-blue-scraper

# Cài đặt dependencies
pip install -r requirements.txt

# Cài đặt Playwright browsers
playwright install
```

## 🚀 Sử dụng

### Chạy locally:
```bash
python main.py
```

### Chạy với gunicorn (production):
```bash
gunicorn main:app --bind 0.0.0.0:5000 --workers 1 --timeout 300
```

### API Endpoints:

#### 1. **GET /** - Home page
```bash
curl https://your-app.onrender.com/
```
Trả về thông tin API và các endpoints có sẵn.

#### 2. **POST /scrape** - Trigger scraping
```bash
curl -X POST https://your-app.onrender.com/scrape
```
**Dành cho n8n:** Gọi endpoint này để bắt đầu thu thập dữ liệu.

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

#### 3. **GET /status** - Kiểm tra trạng thái
```bash
curl https://your-app.onrender.com/status
```
Kiểm tra xem scraping có đang chạy không và thông tin lần chạy cuối.

#### 4. **GET /data** - Lấy dữ liệu
```bash
curl https://your-app.onrender.com/data
```
Lấy dữ liệu lớp học mới nhất đã thu thập được.

## 🔧 Cấu hình n8n

Trong n8n, bạn có thể:

1. **Trigger scraping:**
   - Node: HTTP Request
   - Method: POST
   - URL: `https://your-app.onrender.com/scrape`

2. **Kiểm tra trạng thái:**
   - Node: HTTP Request
   - Method: GET
   - URL: `https://your-app.onrender.com/status`

3. **Lấy dữ liệu:**
   - Node: HTTP Request
   - Method: GET
   - URL: `https://your-app.onrender.com/data`

## 📊 Output

Dữ liệu được lưu vào file `classes_data.json` với format:

```json
{
  "event_date": "2025-08-11",
  "start_time": "09:00",
  "end_time": "10:00",
  "title": "Mat Pilates",
  "instructor": "Laura Murillo Danza",
  "location": "Nosara Blue",
  "source_url": "https://www.nosarablue.com/classes",
  "description": "Mat Pilates - 1 hr - 50 spots available",
  "category": "",
  "tags": ""
}
```

## 🔧 Cấu hình Render

Để deploy lên Render, tạo file `render.yaml`:

```yaml
services:
  - type: web
    name: nosara-blue-scraper
    env: python
    buildCommand: pip install -r requirements.txt && playwright install chromium
    startCommand: gunicorn main:app --bind 0.0.0.0:$PORT --workers 1 --timeout 300
    healthCheckPath: /
```

## 📝 License

MIT License
