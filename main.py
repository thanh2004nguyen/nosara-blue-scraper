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
            
            print("🚀 Bắt đầu truy cập trang web...")
            page.goto("https://www.nosarablue.com/classes")
            print("✅ Đã truy cập trang web thành công")
            
            # Lấy title để kiểm tra
            title = page.title()
            print(f"📄 Title: {title}")
            
            # Lấy URL hiện tại
            current_url = page.url
            print(f"🔗 URL: {current_url}")
            
            time.sleep(3)
            print("⏳ Đã chờ 3 giây")
            
            # Kiểm tra xem có calendar không
            calendar_divs = page.locator('div[role="list"]')
            calendar_count = calendar_divs.count()
            print(f"🔍 Tìm thấy {calendar_count} calendar divs")
            
            # Lấy tất cả text trên trang để debug
            page_text = page.text_content('body')
            print(f"📝 Page text length: {len(page_text) if page_text else 0}")
            
            # Kiểm tra xem có button nào không
            all_buttons = page.locator('button')
            button_count = all_buttons.count()
            print(f"🔘 Tìm thấy {button_count} buttons")
            
            # Kiểm tra xem có text "Classes" không
            if page_text and "Classes" in page_text:
                print("✅ Tìm thấy text 'Classes' trên trang")
            else:
                print("❌ Không tìm thấy text 'Classes'")
            
            # Thử lấy một số text mẫu
            if page_text:
                sample_text = page_text[:500]
                print(f"📄 Sample text: {sample_text}")
            
            browser.close()
            
            # Trả về thông tin debug
            return {
                "success": True,
                "debug_info": {
                    "title": title,
                    "url": current_url,
                    "calendar_divs_count": calendar_count,
                    "buttons_count": button_count,
                    "page_text_length": len(page_text) if page_text else 0,
                    "has_classes_text": "Classes" in page_text if page_text else False,
                    "sample_text": page_text[:200] if page_text else None
                },
                "total_days": 0,
                "total_classes": 0,
                "daily_summary": [],
                "data": []
            }
            
    except Exception as e:
        print("✗ Lỗi:", e)
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "debug_info": None,
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
