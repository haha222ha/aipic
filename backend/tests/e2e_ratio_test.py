import httpx
import time
import sys

BASE = "http://localhost:8800"

passed = 0
failed = 0

def test(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} {detail}")

print("=" * 60)
print("端到端测试 - 预设比例 + 画质分级 + 积分体系")
print("=" * 60)

# 1. 测试API端点返回预设比例
print("\n--- 测试1: API返回预设比例和画质信息 ---")
with httpx.Client(timeout=30) as anon:
    r = anon.get(f"{BASE}/api/generate/models")
    data = r.json()
    test("models API返回200", data['code'] == 200)
    tiers = data['data']['quality_tiers']
    ratios = data['data']['preset_ratios']
    test("4个画质档次", len(tiers) == 4 and 'master' in tiers)
    test("5个预设比例", len(ratios) == 5 and 'square' in ratios and 'portrait_34' in ratios)
    test("master标记为不可用", tiers['master']['available'] == False)
    test("master积分为6", tiers['master']['credits_per_image'] == 6)
    test("standard积分为1", tiers['standard']['credits_per_image'] == 1)
    test("hd积分为3", tiers['hd']['credits_per_image'] == 3)
    test("ultra积分为10", tiers['ultra']['credits_per_image'] == 10)

# 2. 测试定价API
print("\n--- 测试2: 定价API ---")
with httpx.Client(timeout=30) as anon:
    r = anon.get(f"{BASE}/api/generate/pricing")
    data = r.json()
    test("pricing API返回200", data['code'] == 200)
    test("pricing包含preset_ratios", 'preset_ratios' in data['data'])
    test("pricing包含master档次", 'master' in data['data']['quality_tiers'])

# 3. 管理员登录 + 创建授权码
print("\n--- 测试3: 管理员操作 ---")
with httpx.Client(timeout=30) as admin_client:
    r = admin_client.post(f"{BASE}/api/auth/admin/login", json={"username": "admin", "password": "admin123"})
    admin_data = r.json()
    test("管理员登录", admin_data['code'] == 200, str(admin_data.get('msg', '')))

    r = admin_client.post(f"{BASE}/api/admin/codes/generate", json={"package_type": "专业版", "count": 1})
    code_data = r.json()
    test("创建专业版授权码", code_data['code'] == 200, str(code_data.get('msg', '')))
    pro_code = code_data['data']['codes'][0] if code_data['code'] == 200 else ''

    r = admin_client.post(f"{BASE}/api/admin/codes/generate", json={"package_type": "免费版", "count": 1})
    free_code_data = r.json()
    free_code = free_code_data['data']['codes'][0] if free_code_data['code'] == 200 else ''

# 4. 用户注册激活（专业版）
print("\n--- 测试4: 专业版用户激活 ---")
with httpx.Client(timeout=30) as user_client:
    r = user_client.post(f"{BASE}/api/auth/activate", json={"auth_code": pro_code})
    reg_data = r.json()
    test("专业版激活成功", reg_data['code'] == 200, str(reg_data.get('msg', '')))
    if reg_data['code'] == 200:
        test("获得350积分", reg_data['data'].get('credits') == 350, f"实际: {reg_data['data'].get('credits')}")
        user_id = reg_data['data']['user_id']
    else:
        user_id = ''

    # 5. 验证积分
    print("\n--- 测试5: 积分验证 ---")
    r = user_client.get(f"{BASE}/api/auth/verify")
    verify_data = r.json()
    test("验证接口返回积分", verify_data['code'] == 200)
    if verify_data['code'] == 200:
        credits = verify_data['data'].get('credits', 0)
        test("专业版350积分", credits == 350, f"实际: {credits}")

    # 6. 提交生成任务（预设比例）
    print("\n--- 测试6: 提交生成任务（预设比例） ---")
    r = user_client.post(f"{BASE}/api/generate/text2img",
        json={"prompt": "a cute orange cat", "quality": "standard", "ratio": "square"})
    task1 = r.json()
    test("square+standard任务提交", task1['code'] == 200, str(task1.get('msg', '')))
    if task1['code'] == 200:
        test("返回ratio字段", 'ratio' in task1.get('data', {}))
        test("ratio为square", task1['data'].get('ratio') == 'square')
        test("credits_cost为1", task1['data'].get('credits_cost') == 1)
        test("返回ratio_label", 'ratio_label' in task1.get('data', {}))

    time.sleep(1)

    r = user_client.post(f"{BASE}/api/generate/text2img",
        json={"prompt": "小红书爆款美食图", "quality": "hd", "ratio": "portrait_34"})
    task2 = r.json()
    test("portrait_34+hd任务提交", task2['code'] == 200, str(task2.get('msg', '')))
    if task2['code'] == 200:
        test("ratio为portrait_34", task2['data'].get('ratio') == 'portrait_34')
        test("credits_cost为3", task2['data'].get('credits_cost') == 3)

    # 7. 测试master画质降级
    print("\n--- 测试7: 大师画质不可用/降级 ---")
    r = user_client.post(f"{BASE}/api/generate/text2img",
        json={"prompt": "test master", "quality": "master", "ratio": "square"})
    master_task = r.json()
    if master_task['code'] == 200:
        actual_quality = master_task['data'].get('quality')
        test("master降级处理", actual_quality != 'master', f"实际quality: {actual_quality}")
    else:
        test("master拒绝/降级", True, "任务被拒绝或降级")

    # 8. 消费记录
    print("\n--- 测试8: 消费记录查询 ---")
    r = user_client.get(f"{BASE}/api/user/credits/log")
    log_data = r.json()
    test("消费记录API返回200", log_data['code'] == 200)
    if log_data['code'] == 200:
        logs = log_data.get('data', {}).get('logs', [])
        test("有消费记录", len(logs) > 0, f"记录数: {len(logs)}")

    r = user_client.get(f"{BASE}/api/user/credits/summary")
    summary_data = r.json()
    test("积分汇总API返回200", summary_data['code'] == 200)

    # 9. 无效比例回退
    print("\n--- 测试9: 无效比例回退 ---")
    r = user_client.post(f"{BASE}/api/generate/text2img",
        json={"prompt": "test invalid ratio", "quality": "standard", "ratio": "invalid_ratio"})
    invalid_task = r.json()
    if invalid_task['code'] == 200:
        test("无效比例回退到square", invalid_task['data'].get('ratio') == 'square')
    else:
        test("无效比例处理", False, str(invalid_task.get('msg', '')))

# 10. 免费用户画质限制
print("\n--- 测试10: 免费用户画质限制 ---")
with httpx.Client(timeout=30) as free_client:
    r = free_client.post(f"{BASE}/api/auth/activate", json={"auth_code": free_code})
    free_reg = r.json()
    test("免费版激活", free_reg['code'] == 200, str(free_reg.get('msg', '')))
    if free_reg['code'] == 200:
        r = free_client.post(f"{BASE}/api/generate/text2img",
            json={"prompt": "test free ultra", "quality": "ultra", "ratio": "square"})
        free_task = r.json()
        if free_task['code'] == 200:
            actual_q = free_task['data'].get('quality')
            test("免费用户ultra降级", actual_q != 'ultra', f"实际quality: {actual_q}")
        else:
            test("免费用户画质限制", True, "任务被拒绝")

print("\n" + "=" * 60)
print(f"测试结果: ✅ {passed} 通过  ❌ {failed} 失败")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
