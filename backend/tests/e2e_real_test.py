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
print("E2E Test - Full Image Generation with PackyAPI")
print("=" * 60)

print("\n=== 1. API Endpoints Check ===")
r = httpx.get(base + "/api/generate/models")
data = r.json()
test("Models API", data["code"] == 200)
test("gpt-image-2 model", "gpt-image-2" in data["data"]["models"])

r = httpx.get(base + "/api/generate/styles")
data = r.json()
test("Styles API", data["code"] == 200)

print("\n=== 2. Admin Login ===")
r = httpx.post(base + "/api/auth/admin/login", json={"username": "admin", "password": "admin123"})
data = r.json()
test("Admin login", data["code"] == 200)

print("\n=== 3. Create & Activate Auth Code ===")
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
test("Auth code activation", data["code"] == 200, str(data.get("msg", "")))

user_cookies = {}
for cookie_name, cookie_value in r.cookies.items():
    user_cookies[cookie_name] = cookie_value

if data["code"] != 200:
    print("  FATAL: Cannot activate auth code, aborting")
    sys.exit(1)

print(f"  User: {data['data'].get('username', 'N/A')}, Package: {data['data'].get('package_type', 'N/A')}")

print("\n=== 4. Verify User Session ===")
r = httpx.get(base + "/api/auth/verify", cookies=user_cookies)
data = r.json()
test("User session valid", data["code"] == 200)

print("\n=== 5. Submit Text2Img Task (Real API Call) ===")
r = httpx.post(base + "/api/generate/text2img", json={
    "prompt": "a cute orange cat sitting in autumn maple forest, warm healing illustration style",
    "negative_prompt": "blurry, low quality",
    "model": "gpt-image-2",
    "width": 1024,
    "height": 1024,
    "seed": -1,
    "style": "",
}, cookies=user_cookies)
data = r.json()
test("Text2img submission", data["code"] == 200, str(data.get("msg", "")))

if data["code"] != 200:
    print("  FATAL: Cannot submit task, aborting")
    sys.exit(1)

task_id = data["data"]["task_id"]
print(f"  Task ID: {task_id}")

print("\n=== 6. Poll Task Status (up to 180s) ===")
final_status = None
poll_data = None
for i in range(60):
    r = httpx.get(base + f"/api/generate/status/{task_id}", cookies=user_cookies)
    poll_data = r.json()
    if poll_data["code"] == 200:
        status = poll_data["data"]["status"]
        elapsed = (i + 1) * 3
        print(f"  Poll {i+1}: status={status} ({elapsed}s)")
        if status in ["已完成", "失败"]:
            final_status = status
            break
    time.sleep(3)

if final_status == "已完成":
    test("Task completed successfully", True)
    output_path = poll_data["data"].get("output_image_path", "")
    test("Output image path exists", bool(output_path), f"path={output_path}")
    if output_path:
        filename = output_path.split("/")[-1].split("\\")[-1]
        img_url = base + f"/static/outputs/{filename}"
        img_r = httpx.get(img_url)
        test("Output image downloadable", img_r.status_code == 200)
        test("Output image has content", len(img_r.content) > 5000, f"Size: {len(img_r.content)} bytes")
        if len(img_r.content) > 5000:
            local_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static", "outputs", filename)
            print(f"  Image saved to: {os.path.abspath(local_path)}")
elif final_status == "失败":
    fail_reason = poll_data["data"].get("fail_reason", "unknown")
    test("Task succeeded", False, f"Failed: {fail_reason}")
else:
    test("Task completed within timeout", False, "Still processing after 180s")

print("\n=== 7. User Works ===")
r = httpx.get(base + "/api/user/works?page=1&size=10", cookies=user_cookies)
data = r.json()
test("Works API accessible", data["code"] == 200)
if data["code"] == 200:
    works_count = len(data["data"]["works"])
    test("Works list has entries", works_count > 0, f"Count: {works_count}")

print("\n=== 8. Queue Status ===")
r = httpx.get(base + "/api/generate/queue", cookies=user_cookies)
data = r.json()
test("Queue API accessible", "pending_count" in data or data.get("code") == 200)

print("\n" + "=" * 60)
print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")
print("=" * 60)

if failed > 0:
    sys.exit(1)
