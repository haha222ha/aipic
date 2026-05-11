document.addEventListener('DOMContentLoaded', () => {
    checkAdminLogin();
    initAdminTabs();
    document.getElementById('loginForm').addEventListener('submit', handleAdminLogin);
});

async function checkAdminLogin() {
    const res = await apiGet('/api/admin/config');
    if (res.code === 200) {
        showAdminContent();
    } else {
        showLoginBox();
    }
}

function showLoginBox() {
    document.getElementById('loginBox').style.display = 'block';
    document.getElementById('adminContent').style.display = 'none';
}

function showAdminContent() {
    document.getElementById('loginBox').style.display = 'none';
    document.getElementById('adminContent').style.display = 'block';
    loadDashboard();
}

async function handleAdminLogin(e) {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value.trim();

    const res = await apiPost('/api/auth/admin/login', { username, password });
    if (res.code === 200) {
        showAdminContent();
    } else {
        const errDiv = document.getElementById('loginError');
        errDiv.textContent = res.msg;
        errDiv.style.display = 'block';
    }
}

async function adminLogout() {
    await apiPost('/api/auth/admin/logout', {});
    showLoginBox();
}

function initAdminTabs() {
    document.querySelectorAll('.tabs').forEach(tabContainer => {
        tabContainer.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                tabContainer.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const tabName = tab.dataset.tab;
                const parent = tabContainer.parentElement;
                parent.querySelectorAll('.tab-content').forEach(tc => tc.style.display = 'none');
                const target = parent.querySelector(`#tab-${tabName}`);
                if (target) target.style.display = 'block';

                if (tabName === 'dashboard') loadDashboard();
                if (tabName === 'users') loadUsers();
                if (tabName === 'codes') { loadCodes(); loadBatches(); }
                if (tabName === 'queue') loadAdminQueue();
                if (tabName === 'styles') loadStyles();
                if (tabName === 'config') loadConfig();
                if (tabName === 'logs') loadLogs();
            });
        });
    });
}

async function loadDashboard() {
    const res = await apiGet('/api/admin/stats');
    if (res.code !== 200) return;

    const d = res.data;
    document.getElementById('statsGrid').innerHTML = `
        <div class="stat-card"><div class="stat-value">${d.total_users}</div><div class="stat-label">总用户数</div></div>
        <div class="stat-card"><div class="stat-value">${d.active_users}</div><div class="stat-label">活跃用户</div></div>
        <div class="stat-card"><div class="stat-value">${d.today_completed}</div><div class="stat-label">今日生成</div></div>
        <div class="stat-card"><div class="stat-value">${d.pending_tasks}</div><div class="stat-label">排队中</div></div>
        <div class="stat-card"><div class="stat-value">${d.running_tasks}</div><div class="stat-label">执行中</div></div>
        <div class="stat-card"><div class="stat-value">${Object.entries(d.package_distribution || {}).map(([k,v]) => `${k}:${v}`).join(' ')}</div><div class="stat-label">套餐分布</div></div>
    `;
}

async function loadUsers() {
    const res = await apiGet('/api/admin/users');
    if (res.code !== 200) return;

    const tbody = document.querySelector('#userTable tbody');
    tbody.innerHTML = '';
    res.data.users.forEach(u => {
        const statusClass = u.status === '正常' ? 'active' : 'frozen';
        const statusText = u.status === '正常' ? '正常' : '冻结';
        const actionBtn = u.status === '正常'
            ? `<button class="action-btn danger" onclick="freezeUser('${u.user_id}')">冻结</button>`
            : `<button class="action-btn" onclick="unfreezeUser('${u.user_id}')">解冻</button>`;
        tbody.innerHTML += `
            <tr>
                <td>${u.user_id}</td>
                <td>${u.username}</td>
                <td>${u.package_type}</td>
                <td>${u.today_generated_count || 0}/${u.daily_generate_limit}</td>
                <td>${u.expire_time ? u.expire_time.substring(0, 10) : '-'}</td>
                <td><span class="status-badge ${statusClass}">${statusText}</span></td>
                <td>${actionBtn}</td>
            </tr>
        `;
    });
}

async function freezeUser(userId) {
    if (!confirm('确定冻结该用户？')) return;
    await apiPost(`/api/admin/users/${userId}/freeze`, {});
    loadUsers();
}

async function unfreezeUser(userId) {
    await apiPost(`/api/admin/users/${userId}/unfreeze`, {});
    loadUsers();
}

async function loadCodes() {
    const status = document.getElementById('codeStatusFilter').value;
    const res = await apiGet(`/api/admin/codes${status ? '?status=' + status : ''}`);
    if (res.code !== 200) return;

    const tbody = document.querySelector('#codeTable tbody');
    tbody.innerHTML = '';
    res.data.codes.forEach(c => {
        const statusClass = c.status === '未激活' ? 'pending' : c.status === '已激活' ? 'active' : 'frozen';
        const deleteBtn = c.status === '未激活'
            ? `<button class="action-btn danger" onclick="deleteCode('${c.auth_code}')">删除</button>`
            : '';
        tbody.innerHTML += `
            <tr>
                <td class="code-text">${c.auth_code}</td>
                <td>${c.package_type}</td>
                <td>${c.credits}</td>
                <td>${c.valid_days}天</td>
                <td>${c.batch_no || '-'}</td>
                <td>${c.export_tag || '-'}</td>
                <td><span class="status-badge ${statusClass}">${c.status}</span></td>
                <td>${c.create_time ? c.create_time.substring(0, 16) : '-'}</td>
                <td>${c.activate_user_id || '-'}</td>
                <td>${deleteBtn}</td>
            </tr>
        `;
    });
}

async function loadBatches() {
    const res = await apiGet('/api/admin/codes/batches');
    if (res.code !== 200) return;

    const tbody = document.querySelector('#batchTable tbody');
    tbody.innerHTML = '';
    res.data.batches.forEach(b => {
        tbody.innerHTML += `
            <tr>
                <td class="code-text">${b.batch_no}</td>
                <td>${b.batch_name}</td>
                <td>${b.package_type}</td>
                <td>${b.export_tag || '-'}</td>
                <td>${b.total_count}</td>
                <td>${b.unused_count}</td>
                <td>${b.used_count}</td>
                <td>${b.create_time ? b.create_time.substring(0, 16) : '-'}</td>
                <td>
                    <button class="action-btn" onclick="exportByBatch('${b.batch_no}')">导出</button>
                </td>
            </tr>
        `;
    });

    const exportSelect = document.getElementById('exportBatchNo');
    exportSelect.innerHTML = '<option value="">全部批次</option>';
    res.data.batches.forEach(b => {
        exportSelect.innerHTML += `<option value="${b.batch_no}">${b.batch_name} (${b.batch_no})</option>`;
    });
}

function showBatchGenerateForm() {
    document.getElementById('batchGenerateForm').style.display = 'block';
    document.getElementById('exportForm').style.display = 'none';
}

function hideBatchGenerateForm() {
    document.getElementById('batchGenerateForm').style.display = 'none';
}

function showExportForm() {
    document.getElementById('exportForm').style.display = 'block';
    document.getElementById('batchGenerateForm').style.display = 'none';
    loadBatches();
}

function hideExportForm() {
    document.getElementById('exportForm').style.display = 'none';
}

async function batchGenerateCodes() {
    const packageType = document.getElementById('batchPackageType').value;
    const count = parseInt(document.getElementById('batchCount').value) || 1;
    const validDays = parseInt(document.getElementById('batchValidDays').value) || 30;
    const batchName = document.getElementById('batchName').value.trim();
    const exportTag = document.getElementById('batchExportTag').value.trim();

    if (!batchName) {
        alert('请填写批次名称，便于后续区分');
        return;
    }

    const res = await apiPost('/api/admin/codes/batch-generate', {
        package_type: packageType,
        count,
        valid_days: validDays,
        batch_name: batchName,
        export_tag: exportTag,
    });

    if (res.code === 200) {
        const d = res.data;
        alert(`成功生成${d.count}个授权码\n批次号: ${d.batch_no}\n批次名: ${d.batch_name}\n套餐: ${d.package_type}\n积分: ${d.credits}/个\n有效期: ${d.valid_days}天`);
        document.getElementById('batchGenerateForm').style.display = 'none';
        document.getElementById('batchName').value = '';
        document.getElementById('batchExportTag').value = '';
        loadCodes();
        loadBatches();
    } else {
        alert(res.msg);
    }
}

async function exportCodes() {
    const batchNo = document.getElementById('exportBatchNo').value;
    const packageType = document.getElementById('exportPackageType').value;
    const status = document.getElementById('exportStatus').value;

    let url = '/api/admin/codes/export?format=csv';
    if (batchNo) url += `&batch_no=${encodeURIComponent(batchNo)}`;
    if (packageType) url += `&package_type=${encodeURIComponent(packageType)}`;
    if (status) url += `&status=${encodeURIComponent(status)}`;

    window.open(url, '_blank');
    document.getElementById('exportForm').style.display = 'none';
}

async function exportByBatch(batchNo) {
    const url = `/api/admin/codes/export?format=csv&batch_no=${encodeURIComponent(batchNo)}`;
    window.open(url, '_blank');
}

async function deleteCode(authCode) {
    if (!confirm('确定删除该授权码？')) return;
    const res = await apiDelete(`/api/admin/codes/${authCode}`);
    if (res.code === 200) loadCodes();
    else alert(res.msg);
}

async function loadAdminQueue() {
    const res = await apiGet('/api/admin/stats');
    if (res.code !== 200) return;
    document.getElementById('adminQueueStats').innerHTML = `
        <div class="queue-stat-card"><div class="stat-value">${res.data.pending_tasks}</div><div class="stat-label">等待中</div></div>
        <div class="queue-stat-card"><div class="stat-value">${res.data.running_tasks}</div><div class="stat-label">执行中</div></div>
        <div class="queue-stat-card"><div class="stat-value">${res.data.today_completed}</div><div class="stat-label">今日完成</div></div>
    `;
}

async function loadStyles() {
    const res = await apiGet('/api/admin/styles');
    if (res.code !== 200) return;

    const tbody = document.querySelector('#styleTable tbody');
    tbody.innerHTML = '';
    res.data.styles.forEach(s => {
        const typeText = s.is_preset ? '预设' : '自定义';
        const deleteBtn = s.is_preset ? '' : `<button class="action-btn danger" onclick="deleteStyle('${s.style_name}')">删除</button>`;
        tbody.innerHTML += `
            <tr>
                <td>${s.style_name}</td>
                <td>${s.category}</td>
                <td>${s.style_prompt.substring(0, 60)}${s.style_prompt.length > 60 ? '...' : ''}</td>
                <td><span class="status-badge ${s.is_preset ? 'active' : 'pending'}">${typeText}</span></td>
                <td>${deleteBtn}</td>
            </tr>
        `;
    });
}

function showAddStyleForm() {
    const form = document.getElementById('addStyleForm');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

async function addStyle() {
    const styleName = document.getElementById('styleName').value.trim();
    const stylePrompt = document.getElementById('stylePrompt').value.trim();
    const negPrompt = document.getElementById('styleNegPrompt').value.trim();
    const category = document.getElementById('styleCategory').value.trim();

    if (!styleName || !stylePrompt) {
        alert('请填写风格名称和提示词');
        return;
    }

    const res = await apiPost('/api/admin/styles', {
        style_name: styleName,
        style_prompt: stylePrompt,
        negative_prompt: negPrompt,
        category: category || '通用',
    });

    if (res.code === 200) {
        alert('风格添加成功');
        document.getElementById('addStyleForm').style.display = 'none';
        document.getElementById('styleName').value = '';
        document.getElementById('stylePrompt').value = '';
        document.getElementById('styleNegPrompt').value = '';
        loadStyles();
    } else {
        alert(res.msg);
    }
}

async function deleteStyle(styleName) {
    if (!confirm(`确定删除风格"${styleName}"？`)) return;
    const res = await apiDelete(`/api/admin/styles/${encodeURIComponent(styleName)}`);
    if (res.code === 200) loadStyles();
    else alert(res.msg);
}

async function loadConfig() {
    const res = await apiGet('/api/admin/config');
    if (res.code !== 200) return;
    const c = res.data;
    document.getElementById('configForm').innerHTML = `
        <div class="form-row">
            <div class="form-group">
                <label>默认模型</label>
                <input type="text" id="cfgDefaultModel" value="${c.default_model}">
            </div>
            <div class="form-group">
                <label>全局日生成上限</label>
                <input type="number" id="cfgDailyLimit" value="${c.daily_generate_limit}">
            </div>
        </div>
        <button class="btn-primary" onclick="saveConfig()" style="margin-top:12px;">保存配置</button>
    `;
}

async function saveConfig() {
    const data = {
        default_model: document.getElementById('cfgDefaultModel').value,
        daily_generate_limit: parseInt(document.getElementById('cfgDailyLimit').value),
    };
    const res = await apiPost('/api/admin/config', data);
    alert(res.msg);
}

async function loadLogs() {
    const res = await apiGet('/api/admin/logs');
    if (res.code !== 200) return;

    const tbody = document.querySelector('#logTable tbody');
    tbody.innerHTML = '';
    res.data.logs.forEach(log => {
        tbody.innerHTML += `
            <tr>
                <td>${log.admin_username}</td>
                <td>${log.operation_type}</td>
                <td>${log.operation_content}</td>
                <td>${log.operation_time ? log.operation_time.substring(0, 16) : '-'}</td>
                <td>${log.operation_ip}</td>
            </tr>
        `;
    });
}
