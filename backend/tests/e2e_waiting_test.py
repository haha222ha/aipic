import httpx
import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.auth import create_auth_code
from core.database import init_global_db, global_db_conn
from datetime import datetime

base = "http://localhost:8800"
passed = 0
failed = 0


def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name} {detail}")


print("=" * 60)
print("E2E Test - Waiting Experience + Real Image Generation")
print("=" * 60)

print("\n=== 1. Verify Frontend Assets ===")
r = httpx.get(base + "/static/css/index.css")
test("CSS loads", r.status_code == 200)
css_text = r.text
test("Waiting overlay CSS present", ".waiting-overlay" in css_text)
test("Paint blob animation present", "blobFloat" in css_text)
test("Stage progress CSS present", ".waiting-stages" in css_text)
test("Tip carousel CSS present", ".waiting-tip" in css_text)
test("Timer CSS present", ".waiting-timer" in css_text)
test("Success flash CSS present", "success-flash" in css_text)

r = httpx.get(base + "/static/js/index.js")
test("JS loads", r.status_code == 200)
js_text = r.text
test("WAITING_TIPS array present", "WAITING_TIPS" in js_text)
test("Stage durations present", "STAGE_DURATIONS" in js_text)
test("showWaitingOverlay function present", "showWaitingOverlay" in js_text)
test("hideWaitingOverlay function present", "hideWaitingOverlay" in js_text)
test("autoAdvanceStage function present", "autoAdvanceStage" in js_text)
test("updateTip function present", "updateTip" in js_text)

r = httpx.get(base + "/")
html_text = r.text
test("Waiting overlay HTML present", "waitingOverlay" in html_text)
test("Paint blobs HTML present", "paint-blob" in html_text)
test("Stage dots HTML present", "stage-0" in html_text)
test("Tip text element present", "tipText" in html_text)
test("Timer element present", "waitingTimer" in html_text)
test("Prompt preview present", "promptPreview" in html_text)

print("\n=== 2. Create User & Submit Task ===")
init_global_db()
test_auth_code = create_auth_code()
with global_db_conn() as conn:
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO global_auth_codes (auth_code, package_type, valid_days, status, create_time) VALUES (?, ?, ?, ?, ?)",
        (test_auth_code, "专业版", 30, "未激活", datetime.now().isoformat())
    )
    conn.commit()

r = httpx.post(base + "/api/auth/activate", json={"auth_code": test_auth_code})
data = r.json()
test("Auth code activation", data["code"] == 200)

user_cookies = {}
for cookie_name, cookie_value in r.cookies.items():
    user_cookies[cookie_name] = cookie_value

r = httpx.post(base + "/api/generate/text2img", json={
    "prompt": "a magical forest with glowing mushrooms and fireflies at night",
    "model": "gpt-image-2",
    "width": 1024,
    "height": 1024,
    "seed": -1,
    "style": "",
}, cookies=user_cookies)
data = r.json()
test("Task submission", data["code"] == 200)

if data["code"] == 200:
    task_id = data["data"]["task_id"]
    print(f"  Task ID: {task_id}")

    print("\n=== 3. Wait for Generation (testing waiting experience timing) ===")
    start = time.time()
    final_status = None
    for i in range(60):
        r = httpx.get(base + f"/api/generate/status/{task_id}", cookies=user_cookies)
        poll_data = r.json()
        if poll_data["code"] == 200:
            status = poll_data["data"]["status"]
            elapsed = round(time.time() - start, 1)
            print(f"  [{elapsed}s] Status: {status}")
            if status in ["已完成", "失败"]:
                final_status = status
                break
        time.sleep(3)

    total_time = round(time.time() - start, 1)
    test(f"Task finished in {total_time}s", final_status is not None)

    if final_status == "已完成":
        test("Image generated successfully", True)
        output_path = poll_data["data"].get("output_image_path", "")
        if output_path:
            filename = output_path.split("/")[-1].split("\\")[-1]
            img_r = httpx.get(base + f"/static/outputs/{filename}")
            test("Image downloadable", img_r.status_code == 200)
            test("Image has content", len(img_r.content) > 5000, f"Size: {len(img_r.content)} bytes")
    else:
        fail_reason = poll_data["data"].get("fail_reason", "unknown")
        test("Generation succeeded", False, f"Reason: {fail_reason}")

print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

if failed > 0:
    sys.exit(1)
