from playwright.sync_api import sync_playwright
import time
from datetime import datetime, timezone, timedelta
import json
import re
import traceback
from flask import Flask, jsonify, request
import threading
import os

app = Flask(__name__)

CLASS_ITEMS_XPATH = "//div[@role='list']//div[@role='listitem']"

# Global variable to store scraping status
scraping_status = {
    "is_running": False,
    "last_run": None,
    "total_classes": 0,
    "error": None
}

def get_cst_date():
    cst = timezone(timedelta(hours=-6))
    return datetime.now(cst).date()

def get_next_day(current_date):
    return current_date + timedelta(days=1)

def parse_time_to_24h(time_str):
    try:
        time_str = time_str.strip().lower()
        pattern = r'(\d{1,2}):(\d{2})\s*(am|pm)'
        match = re.match(pattern, time_str)
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2))
            period = match.group(3)
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}"
        else:
            return time_str
    except Exception:
        return time_str

def calculate_end_time(start_time, duration):
    try:
        start_hour, start_minute = map(int, start_time.split(':'))
        duration_str = duration.lower()
        hours = 0
        minutes = 0
        hour_pattern = r'(\d+)\s*hr'
        minute_pattern = r'(\d+)\s*min'
        hour_match = re.search(hour_pattern, duration_str)
        minute_match = re.search(minute_pattern, duration_str)
        if hour_match:
            hours = int(hour_match.group(1))
        if minute_match:
            minutes = int(minute_match.group(1))
        end_minute = start_minute + minutes
        end_hour = start_hour + hours + (end_minute // 60)
        end_minute = end_minute % 60
        return f"{end_hour:02d}:{end_minute:02d}"
    except Exception:
        return start_time

def get_week_range_from_html(html):
    try:
        m = re.search(r'([A-Za-z]{3,9}\s+\d{1,2}\s*-\s*[A-Za-z]{3,9}\s+\d{1,2})', html)
        if m:
            return m.group(1).strip()
    except:
        pass
    return ""

def click_next_week_button(page, wait_timeout=6000):
    try:
        prev_html = page.content()
        prev_range = get_week_range_from_html(prev_html)
        candidates = []
        candidates.extend(page.query_selector_all("button[aria-label], a[aria-label], button[title], a[title], button, a, span"))
        elem_to_click = None
        for el in candidates:
            try:
                text = (el.inner_text() or "").strip()
                aria = (el.get_attribute("aria-label") or "").strip()
                title = (el.get_attribute("title") or "").strip()
                if text in ("›", ">", "»", "→") or re.search(r'\bnext\b', text, re.I) or re.search(r'\bnext\b', aria, re.I) or re.search(r'\bnext\b', title, re.I):
                    try:
                        if not el.is_visible():
                            continue
                    except:
                        pass
                    disabled = el.get_attribute("disabled") == "true" or el.get_attribute("aria-disabled") == "true"
                    if disabled:
                        continue
                    elem_to_click = el
                    break
            except Exception:
                continue

        if not elem_to_click:
            xpath_candidates = page.locator("xpath=//button[normalize-space(.)='›'] | //a[normalize-space(.)='›'] | //span[normalize-space(.)='›']")
            if xpath_candidates.count() > 0:
                el = xpath_candidates.first
                try:
                    if el.is_visible():
                        elem_to_click = el
                except:
                    elem_to_click = el

        if not elem_to_click:
            return False

        try:
            elem_to_click.click()
        except Exception:
            try:
                page.evaluate("(el) => el.click()", elem_to_click)
            except:
                pass

        deadline = time.time() + (wait_timeout/1000)
        while time.time() < deadline:
            html = page.content()
            new_range = get_week_range_from_html(html)
            if new_range and new_range != prev_range:
                time.sleep(0.6)
                return True
            time.sleep(0.3)
        time.sleep(0.5)
        return False

    except Exception as e:
        print("⚠️ click_next_week_button lỗi:", e)
        return False

def find_and_click_date(page, target_date, max_next_clicks=8):
    day_text = str(target_date.day)
    attempts = 0
    while attempts <= max_next_clicks:
        btns = page.locator(f"button:has-text('{day_text}'), a:has-text('{day_text}'), span:has-text('{day_text}')")
        count = btns.count()
        if count > 0:
            for i in range(count):
                try:
                    el = btns.nth(i)
                    try:
                        if not el.is_visible():
                            continue
                    except:
                        pass
                    if el.get_attribute("aria-disabled") == "true" or el.get_attribute("disabled") == "true":
                        continue
                    try:
                        el.click()
                    except Exception:
                        page.evaluate("(e) => e.click()", el)
                    time.sleep(0.8)
                    return True
                except Exception:
                    continue
        attempts += 1
        print(f"🔁 Không thấy ngày {day_text} (attempt {attempts}/{max_next_clicks}) — thử Next Week")
        if not click_next_week_button(page):
            print("✗ Không thể click Next Week (hoặc tuần không đổi).")
            return False
        time.sleep(0.6)
    print(f"✗ Đã thử {max_next_clicks} lần next-week mà vẫn không tìm thấy ngày {day_text}")
    return False

def wait_for_content_change(page, previous_count, timeout_ms=9000):
    try:
        end = time.time() + (timeout_ms / 1000)
        while time.time() < end:
            try:
                if page.locator('text="No Classes Available"').count() > 0:
                    return True
            except:
                pass
            try:
                new_count = page.locator(CLASS_ITEMS_XPATH).count()
                if new_count != previous_count:
                    return True
            except:
                pass
            page.wait_for_timeout(250)
        return False
    except Exception as e:
        print("⚠️ wait_for_content_change lỗi:", e)
        return False

def extract_class_info(page, current_date):
    try:
        try:
            if page.locator('text="No Classes Available"').count() > 0:
                return "NO_CLASSES"
        except:
            pass

        class_items = page.locator(CLASS_ITEMS_XPATH)
        total_classes = class_items.count()
        classes_info = []
        for i in range(total_classes):
            try:
                rich_text_xpath = f"({CLASS_ITEMS_XPATH})[{i+1}]//div[@data-testid='richTextElement']"
                rich_text_elements = page.locator(rich_text_xpath)
                if rich_text_elements.count() >= 4:
                    get_text = lambda idx: (rich_text_elements.nth(idx).inner_text().strip() if rich_text_elements.count() > idx else "").strip()
                    time_text = get_text(0)
                    duration_text = get_text(1)
                    class_name = get_text(2)
                    teacher_name = get_text(3)
                    spots_text = get_text(4) if rich_text_elements.count() > 4 else ""
                    start_time_24h = parse_time_to_24h(time_text)
                    end_time_24h = calculate_end_time(start_time_24h, duration_text)
                    class_info = {
                        "event_date": current_date.strftime('%Y-%m-%d'),
                        "start_time": start_time_24h,
                        "end_time": end_time_24h,
                        "title": class_name,
                        "instructor": teacher_name,
                        "location": "Nosara Blue",
                        "source_url": "https://www.nosarablue.com/classes",
                        "description": f"{class_name} - {duration_text} - {spots_text}".strip(" -"),
                        "category": "",
                        "tags": ""
                    }
                    classes_info.append(class_info)
            except Exception:
                continue
        return classes_info
    except Exception as e:
        print("⚠️ extract_class_info lỗi:", e)
        return []

def save_classes_to_file(classes_info, filename="classes_data.json"):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(classes_info, f, ensure_ascii=False, indent=2)
        print(f"✓ Đã lưu {len(classes_info)} lớp học vào file: {filename}")
        return True
    except Exception as e:
        print(f"✗ Lỗi khi lưu file: {e}")
        return False

def run_scraper():
    """Hàm chạy scraper trong thread riêng"""
    global scraping_status
    
    scraping_status["is_running"] = True
    scraping_status["error"] = None
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)  # headless=True cho production
            context = browser.new_context()
            page = context.new_page()
            url = "https://www.nosarablue.com/classes"
            print(f"🌐 Truy cập: {url}")
            
            try:
                page.goto(url, timeout=60000)
                page.wait_for_load_state('networkidle')
                print("✓ Trang đã load")
                
                current_date = get_cst_date()
                end_date = current_date + timedelta(days=30)
                all_classes_info = []
                
                while current_date <= end_date:
                    print(f"\n🔎 Xử lý ngày: {current_date}")
                    try:
                        prev_count = page.locator(CLASS_ITEMS_XPATH).count()
                    except:
                        prev_count = -1
                    
                    found = find_and_click_date(page, current_date, max_next_clicks=8)
                    if not found:
                        print(f"⚠️ Bỏ qua ngày {current_date} (không tìm thấy trên calendar).")
                        current_date = get_next_day(current_date)
                        continue
                    
                    changed = wait_for_content_change(page, prev_count, timeout_ms=9000)
                    if not changed:
                        print("⚠️ Nội dung có thể chưa cập nhật, vẫn thử extract.")
                    
                    classes_info = extract_class_info(page, current_date)
                    if classes_info == "NO_CLASSES":
                        print(f"✳️ Ngày {current_date}: Không có lớp.")
                    elif isinstance(classes_info, list) and classes_info:
                        print(f"✓ Ngày {current_date}: tìm thấy {len(classes_info)} lớp.")
                        all_classes_info.extend(classes_info)
                    else:
                        print(f"ℹ️ Ngày {current_date}: không lấy được lớp (rỗng).")
                    
                    current_date = get_next_day(current_date)
                    time.sleep(0.3)
                
                if all_classes_info:
                    save_classes_to_file(all_classes_info)
                    scraping_status["total_classes"] = len(all_classes_info)
                else:
                    print("⚠️ Không có dữ liệu thu thập được.")
                    scraping_status["total_classes"] = 0
                
                scraping_status["last_run"] = datetime.now().isoformat()
                
            except Exception as e:
                print("✗ Lỗi chạy:", e)
                scraping_status["error"] = str(e)
            finally:
                browser.close()
                print("🔚 Đóng browser.")
                
    except Exception as e:
        print("✗ Lỗi khởi tạo playwright:", e)
        scraping_status["error"] = str(e)
    finally:
        scraping_status["is_running"] = False

@app.route('/')
def home():
    return jsonify({
        "message": "Nosara Blue Classes Scraper API",
        "status": "running",
        "endpoints": {
            "/scrape": "POST - Trigger scraping",
            "/status": "GET - Get scraping status",
            "/data": "GET - Get latest data"
        }
    })

@app.route('/scrape', methods=['POST'])
def trigger_scrape():
    """API endpoint để n8n gọi và trigger scraping"""
    global scraping_status
    
    if scraping_status["is_running"]:
        return jsonify({
            "success": False,
            "message": "Scraping đang chạy, vui lòng đợi",
            "status": scraping_status
        }), 409
    
    # Chạy scraper trong thread riêng
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "success": True,
        "message": "Đã bắt đầu scraping",
        "status": scraping_status
    })

@app.route('/status', methods=['GET'])
def get_status():
    """API endpoint để kiểm tra trạng thái scraping"""
    return jsonify(scraping_status)

@app.route('/data', methods=['GET'])
def get_data():
    """API endpoint để lấy dữ liệu mới nhất"""
    try:
        if os.path.exists('classes_data.json'):
            with open('classes_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify({
                "success": True,
                "total_classes": len(data),
                "data": data
            })
        else:
            return jsonify({
                "success": False,
                "message": "Chưa có dữ liệu"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Lỗi đọc dữ liệu: {str(e)}"
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
