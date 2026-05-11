import sqlite3
conn = sqlite3.connect('global_config.db')
conn.row_factory = sqlite3.Row
c = conn.cursor()

print('=== 积分消费日志(全部) ===')
c.execute('SELECT * FROM global_credits_log ORDER BY create_time DESC')
rows = c.fetchall()
print(f'总记录数: {len(rows)}')
for r in rows:
    ct = r['create_time'] or ''
    uid = r['user_id'] or ''
    tp = r['change_type'] or ''
    amt = r['change_amount']
    ba = r['balance_after']
    desc = r['description'] or ''
    print(f'  [{ct}] user={uid}, type={tp}, amount={amt}, balance_after={ba}, desc={desc}')

print()
print('=== 生成队列(全部) ===')
c.execute('SELECT id, user_id, task_id, prompt, quality_tier, credits_cost, task_status, submit_time, finish_time, output_image_path, fail_reason FROM global_generate_queue ORDER BY submit_time DESC')
rows = c.fetchall()
print(f'总任务数: {len(rows)}')
for r in rows:
    st = r['submit_time'] or ''
    tid = r['task_id'] or ''
    status = r['task_status'] or ''
    quality = r['quality_tier'] or ''
    cost = r['credits_cost']
    prompt = (r['prompt'] or '')[:50]
    output = (r['output_image_path'] or 'NONE')[:80]
    fail = r['fail_reason'] or ''
    print(f'  [{st}] status={status}, quality={quality}, cost={cost}积分, prompt={prompt}..., output={output}')
    if fail:
        print(f'    fail_reason: {fail}')

print()
print('=== 用户列表 ===')
c.execute('SELECT user_id, username, package_type, credits, total_credits_purchased, total_credits_used, status, expire_time FROM global_user_info ORDER BY create_time')
rows = c.fetchall()
for r in rows:
    print(f'  {r["user_id"]} | pkg={r["package_type"]} | credits={r["credits"]} | purchased={r["total_credits_purchased"]} | used={r["total_credits_used"]} | status={r["status"]}')

conn.close()
