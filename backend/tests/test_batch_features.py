import sys
import os
import time
import httpx

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

BASE_URL = "http://127.0.0.1:8800"
client = httpx.Client(base_url=BASE_URL, timeout=30, follow_redirects=True)

def login_admin():
    res = client.post("/api/auth/admin/login", json={"username": "admin", "password": "admin123"})
    data = res.json()
    if data["code"] == 200:
        print("✅ 管理员登录成功")
        return True
    else:
        print(f"⚠️ 管理员登录失败: {data['msg']}，请先创建管理员账号")
        return False

def test_batch_generate():
    print("\n=== 测试批量生成授权码 ===")
    res = client.post("/api/admin/codes/batch-generate", json={
        "package_type": "基础版",
        "count": 10,
        "valid_days": 30,
        "batch_name": "测试批次-电商A店",
        "export_tag": "电商A店"
    })
    data = res.json()
    assert data["code"] == 200, f"批量生成失败: {data}"
    d = data["data"]
    print(f"✅ 批量生成成功")
    print(f"   批次号: {d['batch_no']}")
    print(f"   批次名: {d['batch_name']}")
    print(f"   套餐: {d['package_type']}")
    print(f"   数量: {d['count']}")
    print(f"   积分: {d['credits']}")
    print(f"   标签: {d['export_tag']}")
    return d["batch_no"]

def test_batch_generate_2():
    print("\n=== 测试批量生成授权码（第二批） ===")
    res = client.post("/api/admin/codes/batch-generate", json={
        "package_type": "专业版",
        "count": 5,
        "valid_days": 90,
        "batch_name": "测试批次-渠道B",
        "export_tag": "渠道B"
    })
    data = res.json()
    assert data["code"] == 200, f"批量生成失败: {data}"
    d = data["data"]
    print(f"✅ 批量生成成功")
    print(f"   批次号: {d['batch_no']}")
    print(f"   批次名: {d['batch_name']}")
    print(f"   套餐: {d['package_type']}")
    print(f"   数量: {d['count']}")
    return d["batch_no"]

def test_list_batches():
    print("\n=== 测试批次列表 ===")
    res = client.get("/api/admin/codes/batches")
    data = res.json()
    assert data["code"] == 200, f"批次列表查询失败: {data}"
    batches = data["data"]["batches"]
    print(f"✅ 批次列表正常，共 {len(batches)} 个批次")
    for b in batches[:3]:
        print(f"   {b['batch_no']} | {b['batch_name']} | {b['package_type']} | 总数:{b['total_count']} | 未激活:{b['unused_count']} | 已激活:{b['used_count']}")

def test_export_codes():
    print("\n=== 测试导出授权码 ===")
    res = client.get("/api/admin/codes/export?format=csv")
    assert res.status_code == 200, f"导出失败: {res.status_code}"
    content = res.text
    lines = content.strip().split('\n')
    print(f"✅ 导出成功，共 {len(lines)-1} 条记录")
    print(f"   表头: {lines[0]}")
    print(f"   示例: {lines[1][:80]}...")

def test_export_by_batch(batch_no):
    print(f"\n=== 测试按批次导出: {batch_no} ===")
    res = client.get(f"/api/admin/codes/export?format=csv&batch_no={batch_no}")
    assert res.status_code == 200, f"批次导出失败: {res.status_code}"
    content = res.text
    lines = content.strip().split('\n')
    print(f"✅ 批次导出成功，共 {len(lines)-1} 条记录")

def test_export_by_package():
    print("\n=== 测试按套餐导出: 基础版 ===")
    res = client.get("/api/admin/codes/export?format=csv&package_type=基础版")
    assert res.status_code == 200, f"套餐导出失败: {res.status_code}"
    content = res.text
    lines = content.strip().split('\n')
    print(f"✅ 套餐导出成功，共 {len(lines)-1} 条记录")

def test_codes_list():
    print("\n=== 测试授权码列表（含批次信息） ===")
    res = client.get("/api/admin/codes")
    data = res.json()
    assert data["code"] == 200, f"授权码列表查询失败: {data}"
    codes = data["data"]["codes"]
    print(f"✅ 授权码列表正常，共 {len(codes)} 个授权码")
    for c in codes[:3]:
        print(f"   {c['auth_code'][:16]}... | {c['package_type']} | 批次:{c.get('batch_no', '-')} | 标签:{c.get('export_tag', '-')} | {c['status']}")

if __name__ == "__main__":
    print("=" * 60)
    print("  授权码批量生成与导出功能测试")
    print("=" * 60)

    if not login_admin():
        print("\n请先运行: python -c \"from core.database import init_global_db; init_global_db()\"")
        print("然后通过管理后台创建管理员账号")
        sys.exit(1)

    batch1 = test_batch_generate()
    time.sleep(0.5)
    batch2 = test_batch_generate_2()
    time.sleep(0.5)

    test_list_batches()
    test_codes_list()
    test_export_codes()
    test_export_by_batch(batch1)
    test_export_by_package()

    print("\n" + "=" * 60)
    print("  所有测试通过 ✅")
    print("=" * 60)
