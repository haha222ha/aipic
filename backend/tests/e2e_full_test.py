import os
import sys
import time
import json
import httpx
import pytest
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = "http://127.0.0.1:8800"
TEST_CODE = "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"

client = httpx.Client(base_url=BASE_URL, timeout=30, follow_redirects=True)

def test_01_homepage():
    res = client.get("/")
    assert res.status_code == 200
    assert "AI" in res.text or "ArtForge" in res.text
    print("✅ 首页加载正常")

def test_02_models_api():
    res = client.get("/api/generate/models")
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 200
    assert "quality_tiers" in data["data"]
    assert "preset_ratios" in data["data"]
    assert "standard" in data["data"]["quality_tiers"]
    assert "hd" in data["data"]["quality_tiers"]
    assert "ultra" in data["data"]["quality_tiers"]
    assert "square" in data["data"]["preset_ratios"]
    assert "portrait_34" in data["data"]["preset_ratios"]
    print("✅ 模型API正常")

def test_03_pricing_api():
    res = client.get("/api/generate/pricing")
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 200
    assert "quality_tiers" in data["data"]
    assert "credit_packages" in data["data"]
    print("✅ 定价API正常")

def test_04_styles_api():
    res = client.get("/api/generate/styles")
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 200
    print("✅ 风格API正常")

def test_05_verify_not_logged_in():
    res = client.get("/api/auth/verify")
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 401
    print("✅ 未登录状态正常")

def test_06_activate_auth_code():
    res = client.post("/api/auth/activate", json={"auth_code": TEST_CODE})
    data = res.json()
    assert data["code"] == 200, f"激活失败: {data}"
    assert "credits" in data["data"]
    assert data["data"]["credits"] > 0
    print(f"✅ 授权码激活正常，获得{data['data']['credits']}积分")

def test_07_verify_logged_in():
    res = client.get("/api/auth/verify")
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 200
    assert data["data"]["credits"] > 0
    print(f"✅ 登录验证正常，当前积分: {data['data']['credits']}")

def test_08_user_info():
    res = client.get("/api/user/info")
    assert res.status_code == 200
    data = res.json()
    assert data["code"] == 200
    assert "credits" in data["data"]
    print(f"✅ 用户信息正常，积分: {data['data']['credits']}")

def test_09_submit_generate_task():
    res = client.post("/api/generate/text2img", json={
        "prompt": "一只可爱的猫咪在阳光下玩耍，高清画质",
        "ratio": "square",
        "quality": "standard",
        "seed": -1,
    })
    data = res.json()
    assert data["code"] == 200, f"提交失败: {data}"
    assert "task_id" in data["data"]
    assert "credits_cost" in data["data"]
    task_id = data["data"]["task_id"]
    print(f"✅ 任务提交正常，task_id: {task_id}")
    return task_id

def test_10_poll_task_status():
    task_id = test_09_submit_generate_task()
    max_attempts = 60
    for i in range(max_attempts):
        time.sleep(3)
        res = client.get(f"/api/generate/status/{task_id}")
        data = res.json()
        assert data["code"] == 200
        status = data["data"]["status"]
        print(f"  第{i+1}次查询: {status}")
        if status == "已完成":
            assert data["data"]["output_image_path"]
            print(f"✅ 任务完成，图片路径: {data['data']['output_image_path']}")
            return True
        elif status == "失败":
            print(f"⚠️ 任务失败: {data['data'].get('fail_reason', '未知')}")
            return False
    print("⏱️ 任务超时")
    return False

def test_11_user_works():
    time.sleep(2)
    res = client.get("/api/user/works?page=1&size=10")
    data = res.json()
    assert data["code"] == 200
    print(f"✅ 用户作品查询正常，共{data['data']['total']}个作品")

def test_12_credits_log():
    res = client.get("/api/user/credits/log?page=1&size=20")
    data = res.json()
    assert data["code"] == 200
    print(f"✅ 积分日志正常，共{data['data']['total']}条记录")

def test_13_credits_summary():
    res = client.get("/api/user/credits/summary")
    data = res.json()
    assert data["code"] == 200
    assert "current_credits" in data["data"]
    assert "total_generated" in data["data"]
    print(f"✅ 积分汇总正常，当前{data['data']['current_credits']}积分，生成{data['data']['total_generated']}张")

def test_14_queue_status():
    res = client.get("/api/generate/queue")
    data = res.json()
    assert data["code"] == 200
    assert "pending_count" in data["data"]
    print(f"✅ 队列状态正常，待执行: {data['data']['pending_count']}")

def test_15_logout():
    res = client.post("/api/auth/logout")
    data = res.json()
    assert data["code"] == 200
    print("✅ 退出登录正常")

def test_16_verify_after_logout():
    res = client.get("/api/auth/verify")
    data = res.json()
    assert data["code"] == 401
    print("✅ 退出后验证正常")

if __name__ == "__main__":
    print("=" * 60)
    print("AI智能作图系统 - 端到端测试")
    print("=" * 60)
    
    tests = [
        test_01_homepage,
        test_02_models_api,
        test_03_pricing_api,
        test_04_styles_api,
        test_05_verify_not_logged_in,
        test_06_activate_auth_code,
        test_07_verify_logged_in,
        test_08_user_info,
        test_10_poll_task_status,
        test_11_user_works,
        test_12_credits_log,
        test_13_credits_summary,
        test_14_queue_status,
        test_15_logout,
        test_16_verify_after_logout,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} 失败: {e}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试完成: {passed}通过, {failed}失败")
    print("=" * 60)
