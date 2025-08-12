from playwright.sync_api import sync_playwright
import time
from datetime import datetime, timezone, timedelta
import json
import re
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import threading
import os

app = FastAPI()

# Global variable to store scraping status
scraping_status = {
    "is_running": False,
    "last_run": None,
    "total_classes": 0,
    "error": None,
    "progress": 0,
    "current_date": None,
    "daily_summary": []
}

def run_scraper():
    """Hàm chạy scraper trong thread riêng - sử dụng logic mới từ test_scraper.py"""
    global scraping_status
    
    scraping_status["is_running"] = True
    scraping_status["error"] = None
    scraping_status["progress"] = 0
    scraping_status["current_date"] = None
    scraping_status["daily_summary"] = []
    
    try:
        with sync_playwright() as p:
            # Cấu hình browser cho Render Linux environment
            browser = p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--single-process',
                    '--disable-extensions',
                    '--disable-plugins',
                    '--disable-images'
                ]
            )
            page = browser.new_page()
            
            page.goto("https://www.nosarablue.com/classes")
            print("✅ Đã truy cập trang web thành công")
            
            time.sleep(10)  # Chờ render
            print("⏳ Đã chờ 10 giây")
            
            classes_data = []
            week_count = 0
            total_processed_days = 0
            max_days = 30
            daily_summary = []  # Lưu tổng kết theo ngày
            
            while True:
                week_count += 1
                print(f"\n{'='*60}")
                print(f"📅 TUẦN {week_count}")
                print(f"{'='*60}")
                
                # Tìm ngày đang được focus
                calendar_divs = page.locator('div[role="list"]')
                if calendar_divs.count() == 0:
                    print("❌ Không tìm thấy calendar")
                    break
                
                # Lấy tất cả buttons trong calendar
                buttons = calendar_divs.first.locator('button')
                total_days = buttons.count()
                print(f"📅 Tìm thấy {total_days} ngày trong calendar")
                
                # Tìm button đang được disabled
                disabled_button_index = None
                for i in range(total_days):
                    button = buttons.nth(i)
                    if button.get_attribute("disabled") is not None:
                        disabled_button_index = i
                        current_date = button.get_attribute("aria-label")
                        print(f"🎯 Tìm thấy button disabled: {current_date} (index {i})")
                        break
                
                if disabled_button_index is None:
                    print("❌ Không tìm thấy button disabled")
                    break
                
                # Lặp từ button disabled trở đi
                for day_index in range(disabled_button_index, total_days):
                    # Kiểm tra điều kiện dừng
                    if total_processed_days >= max_days:
                        print(f"\n🎯 Đã đạt giới hạn {max_days} ngày, dừng scraper")
                        break
                    
                    total_processed_days += 1
                    scraping_status["progress"] = int((total_processed_days / max_days) * 100)
                    print(f"\n{'='*50}")
                    print(f"📅 Đang xử lý ngày {total_processed_days}/{max_days}")
                    
                    # Lấy ngày hiện tại đang được focus
                    buttons = calendar_divs.first.locator('button')
                    current_date = None
                    for i in range(buttons.count()):
                        button = buttons.nth(i)
                        if button.get_attribute("disabled") is not None:
                            current_date = button.get_attribute("aria-label")
                            scraping_status["current_date"] = current_date
                            print(f"🎯 Ngày hiện tại: {current_date}")
                            break
                    
                    # Lấy dữ liệu lớp học cho ngày hiện tại
                    if calendar_divs.count() >= 2:
                        classes_div = calendar_divs.nth(1)
                        list_items = classes_div.locator('div[role="listitem"]')
                        day_classes_count = list_items.count()
                        
                        print(f"📊 Tìm thấy {day_classes_count} lớp học cho ngày {current_date}")
                        
                        if day_classes_count > 0:
                            for i in range(day_classes_count):
                                item = list_items.nth(i)
                                all_texts = item.locator('*').all_text_contents()
                                unique_texts = list(dict.fromkeys([text.strip() for text in all_texts if text.strip()]))
                                
                                # Cải thiện logic xử lý thông tin
                                # Tìm thời gian (chứa am/pm và có dạng giờ:phút)
                                time_info = None
                                for text in unique_texts:
                                    if ('am' in text.lower() or 'pm' in text.lower()) and ':' in text and len(text) < 10:
                                        time_info = text
                                        break
                                
                                # Tìm thời lượng (chứa hr và min)
                                duration_info = None
                                for text in unique_texts:
                                    if ('hr' in text.lower() or 'min' in text.lower()) and len(text) < 15:
                                        duration_info = text
                                        break
                                
                                # Tìm tên lớp (loại trừ các từ khóa khác)
                                class_name_info = None
                                for text in unique_texts:
                                    if (text != time_info and text != duration_info and 
                                        'spots' not in text.lower() and 'book' not in text.lower() and
                                        'am' not in text.lower() and 'pm' not in text.lower() and
                                        len(text) > 5 and len(text) < 50):
                                        # Kiểm tra xem có phải tên người không (quá ngắn hoặc quá dài)
                                        if not (len(text) < 3 or len(text) > 30):
                                            class_name_info = text
                                            break
                                
                                # Tìm tên giáo viên (thường là tên người, không chứa từ đặc biệt)
                                instructor_info = None
                                for text in unique_texts:
                                    if (text != time_info and text != duration_info and text != class_name_info and
                                        'spots' not in text.lower() and 'book' not in text.lower() and
                                        'am' not in text.lower() and 'pm' not in text.lower() and
                                        'hr' not in text.lower() and 'min' not in text.lower() and
                                        len(text) > 2 and len(text) < 30):
                                        # Kiểm tra xem có phải tên người không
                                        if not any(char.isdigit() for char in text):
                                            instructor_info = text
                                            break
                                
                                # Tìm description (spots)
                                description_info = None
                                for text in unique_texts:
                                    if 'spots' in text.lower() and len(text) < 30:
                                        description_info = text
                                        break
                                
                                class_info = {
                                    'date': current_date,
                                    'class_number': i + 1,
                                    'time': time_info,
                                    'duration': duration_info,
                                    'class_name': class_name_info,
                                    'instructor': instructor_info,
                                    'description': description_info
                                }
                                classes_data.append(class_info)
                                
                                print(f"  Lớp {i+1}: {time_info} - {class_name_info} - {instructor_info}")
                            
                            print(f"✅ Ngày {current_date}: Đã scraper được {day_classes_count} lớp học")
                            # Lưu tổng kết ngày
                            daily_summary.append(f"Ngày {current_date}: {day_classes_count} tiết học")
                        else:
                            print(f"⚠️ Ngày {current_date}: Không có lớp học nào")
                            # Lưu tổng kết ngày
                            daily_summary.append(f"Ngày {current_date}: 0 tiết học")
                    
                    # Click vào button tiếp theo (nếu không phải button cuối và chưa đạt giới hạn)
                    if day_index < total_days - 1 and total_processed_days < max_days:
                        print(f"🔄 Click vào button tiếp theo...")
                        next_button = buttons.nth(day_index + 1)
                        next_button.click()
                        print(f"✅ Đã click vào button {day_index + 2}")
                        
                        # Chờ 3 giây để dữ liệu hiện lên
                        time.sleep(3)
                        print("⏳ Đã chờ 3 giây")
                    else:
                        print("🏁 Đã xử lý xong tất cả các ngày trong tuần")
                
                # Kiểm tra điều kiện dừng sau khi xử lý tuần
                if total_processed_days >= max_days:
                    print(f"\n🎯 Đã đạt giới hạn {max_days} ngày, dừng scraper")
                    break
                
                # Sau khi xử lý xong tuần, tìm và click nút Next Week (›)
                print(f"\n{'='*50}")
                print("🔄 Tìm nút Next Week (›)...")
                
                # Tìm nút Next Week bằng nhiều cách khác nhau
                next_week_button = None
                
                # Cách 1: Tìm theo text content
                try:
                    next_week_button = page.locator('button:has-text("›")').first
                    if next_week_button.count() > 0:
                        print("✅ Tìm thấy nút Next Week bằng text ›")
                    else:
                        next_week_button = None
                except:
                    pass
                
                # Cách 2: Tìm theo aria-label
                if next_week_button is None:
                    try:
                        next_week_button = page.locator('button[aria-label*="next"]').first
                        if next_week_button.count() > 0:
                            print("✅ Tìm thấy nút Next Week bằng aria-label")
                        else:
                            next_week_button = None
                    except:
                        pass
                
                # Cách 3: Tìm theo class hoặc data attribute
                if next_week_button is None:
                    try:
                        next_week_button = page.locator('button[class*="next"], button[data-testid*="next"]').first
                        if next_week_button.count() > 0:
                            print("✅ Tìm thấy nút Next Week bằng class/data-testid")
                        else:
                            next_week_button = None
                    except:
                        pass
                
                # Click nút Next Week nếu tìm thấy
                if next_week_button is not None:
                    print("🔄 Click vào nút Next Week...")
                    next_week_button.click()
                    print("✅ Đã click vào nút Next Week")
                    
                    # Chờ 5 giây để trang load tuần mới
                    time.sleep(5)
                    print("⏳ Đã chờ 5 giây để load tuần mới")
                    
                    # Kiểm tra xem có tuần mới không
                    new_calendar_divs = page.locator('div[role="list"]')
                    if new_calendar_divs.count() > 0:
                        new_buttons = new_calendar_divs.first.locator('button')
                        new_total_days = new_buttons.count()
                        print(f"📅 Tuần mới: Tìm thấy {new_total_days} ngày")
                        
                        # Lấy ngày đầu tiên của tuần mới
                        if new_total_days > 0:
                            first_day = new_buttons.nth(0)
                            first_day_date = first_day.get_attribute("aria-label")
                            print(f"🎯 Ngày đầu tiên tuần mới: {first_day_date}")
                            
                            # Tiếp tục vòng lặp while để xử lý tuần mới
                            continue
                    else:
                        print("❌ Không tìm thấy calendar mới")
                        break
                else:
                    print("❌ Không tìm thấy nút Next Week")
                    break
            
            browser.close()
            
            # Lưu dữ liệu vào file
            if classes_data:
                with open('classes_data.json', 'w', encoding='utf-8') as f:
                    json.dump(classes_data, f, ensure_ascii=False, indent=2)
                print(f"✅ Đã lưu {len(classes_data)} lớp học vào file")
            
            # Cập nhật status
            scraping_status["total_classes"] = len(classes_data)
            scraping_status["daily_summary"] = daily_summary
            scraping_status["last_run"] = datetime.now().isoformat()
            scraping_status["progress"] = 100
            
            # In tổng kết
            print(f"\n{'='*60}")
            print("📋 TỔNG KẾT CHI TIẾT")
            print(f"{'='*60}")
            for summary in daily_summary:
                print(summary)
            
            print(f"\n{'='*60}")
            print(f"🎯 TỔNG KẾT CUỐI CÙNG")
            print(f"{'='*60}")
            print(f"Total {total_processed_days} ngày: {len(classes_data)} tiết học")
            
    except Exception as e:
        print("✗ Lỗi:", e)
        scraping_status["error"] = str(e)
    finally:
        scraping_status["is_running"] = False
        scraping_status["current_date"] = None

@app.get('/')
def home():
    return JSONResponse({
        "message": "Nosara Blue Classes Scraper API",
        "status": "running",
        "endpoints": {
            "/scrape": "POST - Trigger scraping",
            "/status": "GET - Get scraping status", 
            "/data": "GET - Get latest data"
        }
    })

@app.post('/scrape')
def trigger_scrape():
    """API endpoint để n8n gọi và trigger scraping"""
    global scraping_status
    
    if scraping_status["is_running"]:
        raise HTTPException(status_code=409, detail={
            "success": False,
            "message": "Scraping đang chạy, vui lòng đợi",
            "status": scraping_status
        })
    
    # Chạy scraper trong thread riêng
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    return JSONResponse({
        "success": True,
        "message": "Đã bắt đầu scraping",
        "status": scraping_status
    })

@app.get('/status')
def get_status():
    """API endpoint để kiểm tra trạng thái scraping"""
    return JSONResponse(scraping_status)

@app.get('/data')
def get_data():
    """API endpoint để lấy dữ liệu mới nhất"""
    try:
        if os.path.exists('classes_data.json'):
            with open('classes_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            return JSONResponse({
                "success": True,
                "total_classes": len(data),
                "data": data
            })
        else:
            raise HTTPException(status_code=404, detail={
                "success": False,
                "message": "Chưa có dữ liệu"
            })
    except Exception as e:
        raise HTTPException(status_code=500, detail={
            "success": False,
            "message": f"Lỗi đọc dữ liệu: {str(e)}"
        })

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
