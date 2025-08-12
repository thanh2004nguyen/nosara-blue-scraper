from playwright.sync_api import sync_playwright
import time
from datetime import datetime, timezone, timedelta
import json
import re
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import os

app = FastAPI()

def run_scraper_sync():
    """Hàm chạy scraper đồng bộ và trả về dữ liệu trực tiếp"""
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
            
            time.sleep(5)  # Giảm thời gian chờ
            print("⏳ Đã chờ 5 giây")
            
            classes_data = []
            week_count = 0
            total_processed_days = 0
            max_days = 5  # Giảm xuống 5 ngày để test
            daily_summary = []  # Lưu tổng kết theo ngày
            
            while True:
                week_count += 1
                print(f"\n{'='*60}")
                print(f"📅 TUẦN {week_count}")
                print(f"{'='*60}")
                
                # Tìm ngày đang được focus
                calendar_divs = page.locator('div[role="list"]')
                print(f"🔍 Tìm thấy {calendar_divs.count()} calendar divs")
                
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
                    print(f"\n{'='*50}")
                    print(f"📅 Đang xử lý ngày {total_processed_days}/{max_days}")
                    
                    # Lấy ngày hiện tại đang được focus
                    buttons = calendar_divs.first.locator('button')
                    current_date = None
                    for i in range(buttons.count()):
                        button = buttons.nth(i)
                        if button.get_attribute("disabled") is not None:
                            current_date = button.get_attribute("aria-label")
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
                                
                                print(f"🔍 Raw texts for class {i+1}: {unique_texts}")
                                
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
                        
                        # Chờ 2 giây để dữ liệu hiện lên
                        time.sleep(2)
                        print("⏳ Đã chờ 2 giây")
                    else:
                        print("🏁 Đã xử lý xong tất cả các ngày trong tuần")
                        break
                
                # Kiểm tra điều kiện dừng sau khi xử lý tuần
                if total_processed_days >= max_days:
                    print(f"\n🎯 Đã đạt giới hạn {max_days} ngày, dừng scraper")
                    break
                
                # Bỏ qua Next Week để test nhanh
                print("🛑 Dừng sau tuần đầu tiên để test")
                break
            
            browser.close()
            
            # Lưu dữ liệu vào file
            if classes_data:
                with open('classes_data.json', 'w', encoding='utf-8') as f:
                    json.dump(classes_data, f, ensure_ascii=False, indent=2)
                print(f"✅ Đã lưu {len(classes_data)} lớp học vào file")
            
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
            
            return {
                "success": True,
                "total_days": total_processed_days,
                "total_classes": len(classes_data),
                "daily_summary": daily_summary,
                "data": classes_data
            }
            
    except Exception as e:
        print("✗ Lỗi:", e)
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "total_days": 0,
            "total_classes": 0,
            "daily_summary": [],
            "data": []
        }

@app.get('/')
def home():
    return JSONResponse({
        "message": "Nosara Blue Classes Scraper API",
        "status": "running",
        "endpoints": {
            "/scrape": "POST - Scrape data and return results directly"
        }
    })

@app.post('/scrape')
def scrape_data():
    """API endpoint duy nhất - chạy scraper và trả về dữ liệu trực tiếp"""
    print("🚀 Bắt đầu scraping...")
    result = run_scraper_sync()
    print("✅ Hoàn thành scraping")
    return JSONResponse(result)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    uvicorn.run(app, host='0.0.0.0', port=port)
