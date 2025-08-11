# Nosara Blue Classes Scraper

API để scrape thông tin lớp học từ website Nosara Blue.

## Tính năng

- Scrape thông tin lớp học trong 7 ngày tới
- API endpoints để trigger scraping và lấy dữ liệu
- Tối ưu cho Render Free tier
- Chạy async trong background thread

## Deploy lên Render

### 1. Chuẩn bị

Đảm bảo có các file sau trong repo:
- `main.py` - Code chính
- `requirements.txt` - Dependencies
- `render.yaml` - Cấu hình Render (optional)

### 2. Deploy

1. Tạo repo GitHub chứa code này
2. Vào [render.com](https://render.com) → New Web Service
3. Connect repo GitHub
4. Chọn environment: **Python 3.x**
5. Cấu hình:
   - **Build Command**: `pip install -r requirements.txt && playwright install chromium`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Deploy

### 3. Sử dụng API

#### Trigger scraping
```bash
POST https://your-app-name.onrender.com/scrape
```

#### Kiểm tra trạng thái
```bash
GET https://your-app-name.onrender.com/status
```

#### Lấy dữ liệu
```bash
GET https://your-app-name.onrender.com/data
```

## API Endpoints

### GET /
Trang chủ với thông tin API

### POST /scrape
Trigger scraping process. Trả về ngay lập tức, scraping chạy trong background.

### GET /status
Lấy trạng thái scraping:
```json
{
  "is_running": false,
  "last_run": "2024-01-15T10:30:00",
  "total_classes": 25,
  "error": null,
  "progress": 100,
  "current_date": null
}
```

### GET /data
Lấy dữ liệu lớp học mới nhất

## Lưu ý Render Free Tier

- **Timeout**: Request tối đa 90 giây
- **Sleep**: App ngủ sau 15 phút không có traffic
- **Filesystem**: Reset khi restart container
- **Memory**: Giới hạn 512MB RAM

## Tối ưu đã thực hiện

1. **Giảm thời gian scrape**: Từ 30 ngày xuống 7 ngày
2. **Browser args**: Tối ưu cho Linux environment
3. **Progress tracking**: Theo dõi tiến độ scraping
4. **Async processing**: Trả về ngay, xử lý background
5. **Error handling**: Xử lý lỗi tốt hơn

## N8n Integration

Sử dụng trong n8n workflow:

1. **Trigger**: POST `/scrape` để bắt đầu
2. **Wait**: Poll `/status` để đợi hoàn thành
3. **Get Data**: GET `/data` để lấy kết quả
