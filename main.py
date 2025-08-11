from playwright.sync_api import sync_playwright
import time
from datetime import datetime, timezone, timedelta
import json
import re
import traceback

CLASS_ITEMS_XPATH = "//div[@role='list']//div[@role='listitem']"

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
    """
    Tìm chuỗi dạng 'Dec 11 - Dec 17' trong HTML (nếu có) để biết week header.
    Trả về string hoặc empty.
    """
    try:
        # match "Dec 11 - Dec 17" or "December 11 - December 17"
        m = re.search(r'([A-Za-z]{3,9}\s+\d{1,2}\s*-\s*[A-Za-z]{3,9}\s+\d{1,2})', html)
        if m:
            return m.group(1).strip()
    except:
        pass
    return ""

def click_next_week_button(page, wait_timeout=6000):
    """
    Tìm phần tử Next Week (nhiều khả năng là button/a/span có text '›', '>', 'Next', '»', ...)
    Click nó và chờ week-range thay đổi. Trả về True nếu tuần thực sự thay đổi.
    """
    try:
        prev_html = page.content()
        prev_range = get_week_range_from_html(prev_html)

        # tìm candidate elements (button, a, span) có text hoặc attribute liên quan tới 'next'
        candidates = []
        # 1) các button, a, span có aria-label/title chứa 'next' (case-insensitive)
        candidates.extend(page.query_selector_all("button[aria-label], a[aria-label], button[title], a[title], button, a, span"))
        # iterate và chọn element phù hợp
        elem_to_click = None
        for el in candidates:
            try:
                text = (el.inner_text() or "").strip()
                aria = (el.get_attribute("aria-label") or "").strip()
                title = (el.get_attribute("title") or "").strip()
                # các ký tự arrow hoặc từ 'next'
                if text in ("›", ">", "»", "→") or re.search(r'\bnext\b', text, re.I) or re.search(r'\bnext\b', aria, re.I) or re.search(r'\bnext\b', title, re.I):
                    # ensure visible and enabled
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
            # fallback: tìm luôn phần tử có chính xác dấu '›' bằng xpath
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

        # click và chờ week-range thay đổi
        try:
            elem_to_click.click()
        except Exception:
            # thử bằng evaluate nếu click() fail
            try:
                page.evaluate("(el) => el.click()", elem_to_click)
            except:
                pass

        # chờ thay đổi week-range (dựa trên HTML content)
        deadline = time.time() + (wait_timeout/1000)
        while time.time() < deadline:
            html = page.content()
            new_range = get_week_range_from_html(html)
            if new_range and new_range != prev_range:
                # success
                time.sleep(0.6)  # thêm 1 chút ổn định
                return True
            time.sleep(0.3)
        # nếu không thay đổi, vẫn có thể đã thay DOM mà week-range không phù hợp - chờ một chút rồi trả False
        time.sleep(0.5)
        return False

    except Exception as e:
        print("⚠️ click_next_week_button lỗi:", e)
        traceback.print_exc()
        return False

def find_and_click_date(page, target_date, max_next_clicks=8):
    """
    Tìm nút chứa ngày (số ngày) visible và click.
    Nếu không thấy trong tuần hiện tại sẽ click next week rồi thử lại (max_next_clicks lần).
    """
    day_text = str(target_date.day)
    attempts = 0
    while attempts <= max_next_clicks:
        # tìm tất cả nút có chứa text day_text
        # (dùng locator button elements)
        btns = page.locator(f"button:has-text('{day_text}'), a:has-text('{day_text}'), span:has-text('{day_text}')")
        count = btns.count()
        if count > 0:
            # tìm nút visible và không bị disabled
            for i in range(count):
                try:
                    el = btns.nth(i)
                    # visible?
                    try:
                        if not el.is_visible():
                            continue
                    except:
                        pass
                    # không disabled
                    if el.get_attribute("aria-disabled") == "true" or el.get_attribute("disabled") == "true":
                        continue
                    # click
                    try:
                        el.click()
                    except Exception:
                        page.evaluate("(e) => e.click()", el)
                    # chờ một chút cho nội dung cập nhật
                    time.sleep(0.8)
                    return True
                except Exception:
                    continue
        # nếu chưa thấy -> click next week và thử lại
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
        traceback.print_exc()
        return []

def save_classes_to_file(classes_info, filename="classes_data.json"):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(classes_info, f, ensure_ascii=False, indent=2)
        print(f"✓ Đã lưu {len(classes_info)} lớp học vào file: {filename}")
    except Exception as e:
        print(f"✗ Lỗi khi lưu file: {e}")

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
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
            else:
                print("⚠️ Không có dữ liệu thu thập được.")
            time.sleep(2)
        except Exception as e:
            print("✗ Lỗi chạy:", e)
            traceback.print_exc()
        finally:
            browser.close()
            print("🔚 Đóng browser.")

if __name__ == "__main__":
    main()
