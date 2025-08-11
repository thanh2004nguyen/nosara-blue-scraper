# Nosara Blue Classes Scraper

Web scraper để thu thập dữ liệu lớp học từ trang web Nosara Blue.

## 🎯 Tính năng

- Tự động thu thập thông tin lớp học trong 30 ngày
- Xử lý navigation giữa các tuần
- Lưu dữ liệu dưới dạng JSON
- Hỗ trợ format thời gian 24h
- Xử lý các trường hợp "No Classes Available"

## 📋 Yêu cầu

- Python 3.8+
- Playwright

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

```bash
python main.py
```

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
    buildCommand: pip install -r requirements.txt && playwright install
    startCommand: python main.py
```

## 📝 License

MIT License
