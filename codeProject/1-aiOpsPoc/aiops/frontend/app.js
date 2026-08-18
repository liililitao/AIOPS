/**
 * AIOps Alert Agent - 前端主逻辑
 * SPA 单页面应用，无框架依赖
 */

// ==========================================
// 全局状态
// ==========================================
const state = {
    alerts: [],
    selectedAlertId: null,
    activeDetailTab: 'alert-data',
    schedulerRunning: true,
    isAdmin: false,
};

// ==========================================
// 初始化
// ==========================================
document.addEventListener('DOMContentLoaded', async () => {
    await applyNavigationPermissions();
    initNavigation();
    initDetailTabs();
    initApplicationSimulator();
    loadAlerts();
    if (state.isAdmin) {
        initKnowledgeBase();
        loadConfig();
        pollSchedulerStatus();
    }
});

async function applyNavigationPermissions() {
    try {
        const res = await fetch('/api/v1/session');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const session = await res.json();
        state.isAdmin = session.is_admin === true;
    } catch (err) {
        // 权限接口不可用时保持最小权限展示，避免普通用户看到管理入口。
        console.error('加载页面权限失败:', err);
        state.isAdmin = false;
    }

    if (state.isAdmin) {
        document.querySelectorAll('.admin-only').forEach(element => {
            element.hidden = false;
        });
    } else {
        const resultsTab = document.querySelector('.nav-tab[data-tab="results"]');
        if (resultsTab) resultsTab.textContent = '📊 告警分析';
    }
}

// ==========================================
// 导航切换
// ==========================================
function initNavigation() {
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            // 切换导航激活
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            // 切换内容
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.getElementById(`tab-${tabName}`).classList.add('active');
            // 加载数据
            if (tabName === 'results') loadAlerts();
            if (tabName === 'kbchat') loadKBStats();
            if (tabName === 'knowledge') loadDocs();
            if (tabName === 'config') loadConfig();
        });
    });

    // 刷新按钮
    document.getElementById('btn-refresh')?.addEventListener('click', refreshAlerts);
    document.getElementById('btn-scan-now')?.addEventListener('click', triggerScan);

    // 筛选
    document.getElementById('filter-risk')?.addEventListener('change', renderAlertList);
    document.getElementById('filter-search')?.addEventListener('input', renderAlertList);
}

async function initApplicationSimulator() {
    const select = document.getElementById('simulation-rule');
    const button = document.getElementById('btn-generate-application-alert');
    if (!select || !button) return;
    try {
        const res = await fetch('/api/v1/alerts/simulation/application-rules');
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        select.innerHTML = (data.rules || []).map(rule =>
            `<option value="${rule.id}">${escHtml(rule.system)} · ${escHtml(rule.alert_name)}</option>`
        ).join('') || '<option value="">没有可用规则</option>';
    } catch (err) {
        console.error('加载应用告警规则失败:', err);
        select.innerHTML = '<option value="">规则加载失败</option>';
        button.disabled = true;
    }
    button.addEventListener('click', generateApplicationAlert);
}

async function generateApplicationAlert() {
    const select = document.getElementById('simulation-rule');
    const countInput = document.getElementById('simulation-count');
    const button = document.getElementById('btn-generate-application-alert');
    const ruleId = Number(select?.value);
    const count = Number(countInput?.value || 10);
    if (!ruleId || !Number.isInteger(count) || count < 1 || count > 1000) {
        alert('请选择应用规则，并填写 1 到 1000 的日志条数。');
        return;
    }
    const original = button.textContent;
    button.disabled = true;
    button.textContent = '⏳ 生成中...';
    try {
        const res = await fetch('/api/v1/alerts/simulation/application-alert', {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({rule_id: ruleId, count}),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        await loadAlerts({ sync: false });
        state.selectedAlertId = data.alert_id;
        renderAlertList();
        await renderDetailPanel();
    } catch (err) {
        alert(`生成模拟应用告警失败：${err.message}`);
    } finally {
        button.disabled = false;
        button.textContent = original;
    }
}

// ==========================================
// 详情面板 Tab 切换
// ==========================================
function initDetailTabs() {
    document.querySelectorAll('.detail-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            state.activeDetailTab = tab.dataset.detail;
            document.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            renderDetailPanel();
        });
    });
}

// ==========================================
// 加载告警列表
// ==========================================
async function loadAlerts({ sync = false } = {}) {
    const listEl = document.getElementById('alert-list');
    listEl.innerHTML = '<div class="loading"><div class="spinner"></div> 加载中...</div>';
    let syncError = null;

    try {
        if (sync) {
            try {
                const syncRes = await fetch('/api/v1/alerts/sync', { method: 'POST' });
                if (!syncRes.ok) {
                    const error = await syncRes.json().catch(() => ({}));
                    throw new Error(error.detail || `同步失败（HTTP ${syncRes.status}）`);
                }
            } catch (err) {
                // 同步失败时仍展示最近一次成功同步的缓存和本地告警。
                syncError = err;
                console.error('Splunk 告警同步失败:', err);
            }
        }
        const res = await fetch('/api/v1/alerts');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        state.alerts = data.alerts || [];
        renderAlertList();
        return { syncError };
    } catch (err) {
        console.error('加载告警列表失败:', err);
        listEl.innerHTML = '<div class="empty-state">加载失败，请确认后端服务已启动</div>';
    }
}

async function refreshAlerts() {
    const btn = document.getElementById('btn-refresh');
    if (!btn) return;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '⏳ 刷新中...';
    try {
        await loadAlerts();
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

function renderAlertList() {
    const listEl = document.getElementById('alert-list');
    const riskFilter = document.getElementById('filter-risk')?.value || 'all';
    const searchText = (document.getElementById('filter-search')?.value || '').toLowerCase();

    let filtered = state.alerts;
    if (riskFilter !== 'all') {
        filtered = filtered.filter(a => a.risk_level === riskFilter);
    }
    if (searchText) {
        filtered = filtered.filter(a =>
            (a.hostname || '').toLowerCase().includes(searchText) ||
            (a.alert_name || '').toLowerCase().includes(searchText)
        );
    }

    if (filtered.length === 0) {
        listEl.innerHTML = '<div class="empty-state">暂无告警数据</div>';
        return;
    }

    listEl.innerHTML = filtered.map(a => {
        const riskClass = `risk-${a.risk_level === '高' ? 'high' : a.risk_level === '中' ? 'medium' : 'low'}`;
        const isActive = state.selectedAlertId === a.id ? 'active' : '';
        return `
            <div class="alert-item ${isActive}" data-id="${a.id}" onclick="selectAlert('${a.id}')">
                <span class="alert-risk ${riskClass}">${a.risk_level || '?'}</span>
                <button class="alert-delete" title="删除告警" onclick="deleteAlert(event, '${a.id}')">✕</button>
                <div class="alert-title">${escHtml(a.alert_name || 'Unknown')}</div>
                <div class="alert-meta">
                    ${escHtml(a.hostname || '-')} · ${escHtml(a.trigger_time || '-')}
                </div>
            </div>
        `;
    }).join('');
}

async function deleteAlert(event, alertId) {
    event.stopPropagation();
    if (!confirm('确定删除这条模拟应用告警吗？其 AI 风险结果、分析报告和处理建议也会删除；原始 CSV 日志会保留。')) return;
    try {
        const res = await fetch(`/api/v1/alerts/${encodeURIComponent(alertId)}`, { method: 'DELETE' });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
        if (state.selectedAlertId === alertId) {
            state.selectedAlertId = null;
            document.getElementById('detail-content').innerHTML = '<div class="empty-state">请选择一条告警查看详情</div>';
        }
        await loadAlerts();
    } catch (err) {
        alert(`删除告警失败：${err.message}`);
    }
}

// ==========================================
// 选择告警
// ==========================================
async function selectAlert(alertId) {
    state.selectedAlertId = alertId;
    renderAlertList();
    await renderDetailPanel();
}

async function renderDetailPanel() {
    const container = document.getElementById('detail-content');
    if (!state.selectedAlertId) {
        container.innerHTML = '<div class="empty-state">请选择一条告警查看详情</div>';
        return;
    }

    container.innerHTML = '<div class="loading"><div class="spinner"></div> 加载详情...</div>';

    try {
        const res = await fetch(`/api/v1/alerts/${state.selectedAlertId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const detail = await res.json();

        switch (state.activeDetailTab) {
            case 'alert-data':
                renderAlertData(container, detail);
                break;
            case 'analysis':
                renderMarkdownContent(container, detail.analysis_report, 'AI 分析尚未完成，请稍后刷新。');
                break;
            case 'suggestion':
                renderMarkdownContent(container, detail.suggestion, 'AI 分析尚未完成，请稍后刷新。');
                break;
            case 'chat':
                renderChatPanel(container, detail);
                break;
        }
    } catch (err) {
        console.error('加载详情失败:', err);
        container.innerHTML = '<div class="empty-state">加载详情失败</div>';
    }
}

function renderAlertData(container, detail) {
    const alert = detail.alert || {};
    const risk = detail.risk_details || {};
    const matchInfo = detail.from_sample
        ? `<p>🧠 已复用告警分类：${escHtml(detail.match_sample_id || '-')}（匹配度 ${escHtml(String(detail.match_score ?? '-'))}%）</p>`
        : '';
    container.innerHTML = `
        <div class="report-content">
            <h2>告警数据</h2>
            <table>
                <tr><th>字段</th><th>值</th></tr>
                <tr><td>告警名称</td><td>${escHtml(alert.alert_name || '-')}</td></tr>
                <tr><td>触发时间</td><td>${escHtml(alert.trigger_time || '-')}</td></tr>
                <tr><td>事件数量</td><td>${alert.event_count || '-'}</td></tr>
                <tr><td>风险等级</td><td><strong>${escHtml(alert.risk_level || detail.risk_level || '-')}</strong></td></tr>
            </table>

            <h3>风险判定详情</h3>
            ${alert.risk_level === '待分析'
                ? '<p>AI 正在自动分析该告警；完成后会自动生成风险判定、分析报告和处理建议。</p>'
                : `<table>
                    <tr><th>维度</th><th>判定</th></tr>
                    <tr><td>环境风险</td><td>${escHtml(risk.environment_risk || '-')} (${escHtml(risk.environment || '-')})</td></tr>
                    <tr><td>数量风险</td><td>${escHtml(risk.count_risk || '-')} (count: ${risk.count_value || '-'})</td></tr>
                    <tr><td>攻击类型风险</td><td>${escHtml(risk.attack_type_risk || '-')}</td></tr>
                    <tr><td>攻击类型</td><td>${escHtml((risk.attack_types || []).join(', ') || '-')}</td></tr>
                </table>`}

            <h3>受影响资源</h3>
            ${(alert.results || []).map(r => `
                <table>
                    <tr><td>资源ID</td><td>${escHtml(r.id || '-')}</td></tr>
                    <tr><td>域名</td><td>${escHtml(r.properties_hostname || '-')}</td></tr>
                    <tr><td>请求URI</td><td style="word-break:break-all;font-size:12px">${escHtml((r.properties_requestUri || '').substring(0, 500))}</td></tr>
                    <tr><td>动作</td><td>${escHtml(r.properties_action || '-')}</td></tr>
                    <tr><td>数量</td><td>${escHtml(r.count || '-')}</td></tr>
                </table>
            `).join('')}

            ${alert.splunk_url ? `<p><a href="${escHtml(alert.splunk_url)}" target="_blank">🔗 在 Splunk 中查看</a></p>` : ''}

            ${matchInfo}

            ${renderTokenUsage(detail.token_usage)}
        </div>
    `;
}

function isApplicationSimulationAlert() {
    return (state.selectedAlertId || '').startsWith('appsim_');
}

function hasGeneratedAnalysis(detail) {
    if (isApplicationSimulationAlert()) return Boolean(detail?.risk_details);
    const report = detail?.analysis_report || '';
    return Boolean(report) && !report.startsWith('此告警直接从 Splunk 同步；');
}

function renderMarkdownContent(container, content, emptyText) {
    if (!content) {
        container.innerHTML = `<div class="empty-state">${emptyText}</div>`;
        return;
    }
    // 兼容历史模型输出：整篇 Markdown 被 ```markdown 包裹时应显示为正文而非代码块。
    const normalized = unwrapMarkdownFence(content);
    container.innerHTML = `<div class="report-content">${marked.parse(normalized)}</div>`;
}

function unwrapMarkdownFence(content) {
    const text = String(content || '').trim();
    if (!/^```(?:markdown|md)\s*\n/i.test(text) || !/\n```\s*$/.test(text)) return text;
    return text.replace(/^```(?:markdown|md)\s*\n/i, '').replace(/\n```\s*$/, '');
}

function renderChatPanel(container, detail) {
    container.innerHTML = `
        <div class="chat-container">
            <div class="chat-messages" id="chat-messages">
                <div class="chat-msg assistant">
                    <span class="msg-bubble">你好！我是 Splunk AI Alert Handling 助手，你可以就当前告警向我提问。例如：<br>
                    • 这个告警严重吗？<br>
                    • 我应该怎么做？<br>
                    • 攻击路径有什么特征？</span>
                </div>
            </div>
            <div class="chat-input-row">
                <input type="text" id="chat-input" placeholder="输入你的问题..."
                       onkeydown="if(event.key==='Enter')sendChat()">
                <button class="btn btn-primary" onclick="sendChat()">发送</button>
            </div>
        </div>
    `;
}

// ==========================================
// AI 问答
// ==========================================
async function sendChat() {
    const input = document.getElementById('chat-input');
    const question = input.value.trim();
    if (!question) return;
    input.value = '';

    const messagesEl = document.getElementById('chat-messages');
    messagesEl.innerHTML += `
        <div class="chat-msg user"><span class="msg-bubble">${escHtml(question)}</span></div>
        <div class="chat-msg assistant" id="chat-loading">
            <span class="msg-bubble"><div class="spinner"></div> 思考中...</span>
        </div>
    `;
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
        const res = await fetch('/api/v1/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: question,
                alert_id: state.selectedAlertId,
            }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        document.getElementById('chat-loading')?.remove();
        messagesEl.innerHTML += `
            <div class="chat-msg assistant">
                <span class="msg-bubble">${marked.parse(data.answer)}</span>
            </div>
        `;
        messagesEl.scrollTop = messagesEl.scrollHeight;
    } catch (err) {
        document.getElementById('chat-loading')?.remove();
        messagesEl.innerHTML += `
            <div class="chat-msg assistant">
                <span class="msg-bubble" style="color:var(--danger)">请求失败: ${escHtml(err.message)}</span>
            </div>
        `;
    }
}

// ==========================================
// AIOps 知识库问答
// ==========================================
async function loadKBStats() {
    try {
        const res = await fetch('/api/v1/documents');
        const data = await res.json();
        const docs = data?.data?.documents || [];
        const totalChunks = docs.reduce((sum, d) => sum + (d.chunk_count || 0), 0);
        // 更新头部统计数字 (如果存在占位符)
        const header = document.querySelector('#tab-kbchat .panel-header span');
        if (header && docs.length > 0) {
            header.textContent = `基于知识库 ${docs.length} 篇文档 · ${totalChunks} 个知识块`;
        }
    } catch (e) {
        console.log('KB stats load failed:', e);
    }
}

async function sendKBChat() {
    const input = document.getElementById('kb-chat-input');
    const question = input.value.trim();
    if (!question) return;
    input.value = '';

    const messagesEl = document.getElementById('kb-chat-messages');
    messagesEl.innerHTML += `
        <div class="chat-msg user"><span class="msg-bubble">${escHtml(question)}</span></div>
        <div class="chat-msg assistant" id="kb-chat-loading">
            <span class="msg-bubble"><div class="spinner"></div> 检索知识库中...</span>
        </div>
    `;
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
        const res = await fetch('/api/v1/kb-chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: question }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        document.getElementById('kb-chat-loading')?.remove();
        const sourcesHtml = data.sources && data.sources.length > 0
            ? `<div class="kb-sources">📚 参考: ${data.sources.map(s =>
                `<span class="kb-source-tag" title="相关度: ${(s.score*100).toFixed(0)}%">${escHtml(s.source)}</span>`
              ).join(' ')}</div>`
            : '';
        messagesEl.innerHTML += `
            <div class="chat-msg assistant">
                <span class="msg-bubble">${marked.parse(data.answer)}${sourcesHtml}</span>
            </div>
        `;
        messagesEl.scrollTop = messagesEl.scrollHeight;
    } catch (err) {
        document.getElementById('kb-chat-loading')?.remove();
        messagesEl.innerHTML += `
            <div class="chat-msg assistant">
                <span class="msg-bubble" style="color:var(--danger)">请求失败: ${escHtml(err.message)}</span>
            </div>
        `;
    }
}

// ==========================================
// 立即扫描
// ==========================================
async function triggerScan() {
    const btn = document.getElementById('btn-scan-now');
    btn.disabled = true;
    btn.textContent = '⏳ 扫描中...';
    try {
        const res = await fetch('/api/v1/scheduler/scan', { method: 'POST' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        if (data.status !== 'ok') throw new Error(data.message || '扫描失败');
        const message = data.sync_warning
            ? `${data.message}\n\n${data.sync_warning}`
            : (data.message || '扫描已触发');
        alert(message);
        await loadAlerts();
        await refreshSchedulerStatus();
    } catch (err) {
        alert('触发扫描失败: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '⚡ 立即扫描';
    }
}

// ==========================================
// 配置页逻辑
// ==========================================
async function loadConfig() {
    try {
        const res = await fetch('/api/v1/config');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const cfg = await res.json();
        document.getElementById('cfg-interval').value = cfg.scan_interval_minutes || 5;
        document.getElementById('cfg-cmdb-type').value = cfg.cmdb_type || 'xlsx';
        document.getElementById('cfg-cmdb-path').value = cfg.cmdb_type === 'splunk_csv'
            ? (cfg.cmdb_csv_path || '-')
            : (cfg.cmdb_xlsx_path || '-');
        const sync = cfg.cmdb_splunk_sync_status || {};
        document.getElementById('cfg-cmdb-sync-status').textContent =
            sync.status === 'ok'
                ? `成功：${sync.rows || 0} 条，${sync.synced_at || ''}`
                : (sync.message || '尚未同步');
    } catch (err) {
        console.error('加载配置失败:', err);
    }

    const cmdbSyncButton = document.getElementById('btn-cmdb-sync');
    if (cmdbSyncButton) cmdbSyncButton.onclick = async () => {
        const btn = cmdbSyncButton;
        btn.disabled = true;
        btn.textContent = '同步中...';
        try {
            const res = await fetch('/api/v1/config/cmdb/sync', { method: 'POST' });
            const data = await res.json();
            if (!res.ok || data.status !== 'ok') throw new Error(data.message || `HTTP ${res.status}`);
            alert(data.message);
            await loadConfig();
        } catch (err) {
            alert('CMDB 同步失败：' + err.message);
        } finally {
            btn.disabled = false;
            btn.textContent = '立即从 Splunk 同步 CMDB';
        }
    };

    // 配置保存按钮
    document.getElementById('btn-save-interval')?.addEventListener('click', async () => {
        const interval = parseInt(document.getElementById('cfg-interval').value);
        try {
            await fetch('/api/v1/config', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scan_interval_minutes: interval }),
            });
            alert('扫描间隔已更新');
        } catch (err) {
            alert('保存失败: ' + err.message);
        }
    });

    document.getElementById('btn-pause')?.addEventListener('click', async () => {
        await fetch('/api/v1/scheduler/pause', { method: 'POST' });
        document.getElementById('cfg-scheduler-status').textContent = '⏸️ 已暂停';
    });
    document.getElementById('btn-resume')?.addEventListener('click', async () => {
        await fetch('/api/v1/scheduler/resume', { method: 'POST' });
        document.getElementById('cfg-scheduler-status').textContent = '● 运行中';
    });
}

async function refreshSchedulerStatus() {
    try {
        const res = await fetch('/api/v1/config/scheduler/status');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        document.getElementById('nav-status').textContent = data.running ? '● 运行中' : '⏸️ 已暂停';
        document.getElementById('cfg-scheduler-status').textContent = data.running ? '● 运行中' : '⏸️ 已暂停';
        document.getElementById('cfg-last-scan').textContent = data.last_scan || '-';
        document.getElementById('cfg-next-scan').textContent = data.next_scan || '-';
    } catch (err) { /* ignore */ }
}

async function pollSchedulerStatus() {
    await refreshSchedulerStatus();
    setTimeout(pollSchedulerStatus, 30000);
}

// ==========================================
// 工具函数
// ==========================================
// ==========================================
// 知识库 (Knowledge Base)
// ==========================================
const KB_TOKEN_KEY = "aiops_kb_admin_token";

function initKnowledgeBase() {
    try {
        const uploadZone = document.getElementById("upload-zone");
        const uploadInput = document.getElementById("upload-input");
        if (!uploadZone || !uploadInput) {
            console.warn("KB: upload-zone or upload-input not found");
            return;
        }

        // File selected via click (label) or drag-drop
        uploadInput.addEventListener("change", () => {
            if (uploadInput.files && uploadInput.files[0]) {
                uploadFile(uploadInput.files[0]);
                uploadInput.value = ""; // allow re-upload of same file
            }
        });

        // Drag and drop
        uploadZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.add("dragover");
        });
        uploadZone.addEventListener("dragleave", (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.remove("dragover");
        });
        uploadZone.addEventListener("drop", (e) => {
            e.preventDefault();
            e.stopPropagation();
            uploadZone.classList.remove("dragover");
            const files = e.dataTransfer?.files;
            if (files && files.length > 0) {
                uploadFile(files[0]);
            }
        });

        console.log("KB: initialized");
    } catch (e) {
        console.error("KB init error:", e);
    }
}

async function uploadFile(file) {
    const resultEl = document.getElementById("upload-result");
    resultEl.innerHTML = `<span style="color:var(--primary)">上传中: ${escHtml(file.name)} ...</span>`;

    const formData = new FormData();
    formData.append("file", file);

    try {
        const r = await fetch("/api/v1/documents/upload", {
            method: "POST",
            headers: { "X-KB-Admin-Token": getKbAdminToken() },
            body: formData,
        });
        const data = await r.json().catch(() => null);
        if (!r.ok) {
            if (r.status === 401 || r.status === 403) sessionStorage.removeItem(KB_TOKEN_KEY);
            throw new Error(data?.detail || `HTTP ${r.status}`);
        }
        if (data.code === "SUCCESS") {
            resultEl.innerHTML = `<span style="color:var(--success)">已索引: ${data.data.chunks_indexed} chunks (${data.data.bytes} bytes)</span>`;
            loadDocs();
        } else {
            resultEl.innerHTML = `<span style="color:var(--danger)">${escHtml(data?.message || "上传失败")}</span>`;
        }
    } catch (e) {
        resultEl.innerHTML = `<span style="color:var(--danger)">${escHtml(e.message)}</span>`;
    }
}

async function loadDocs() {
    const listEl = document.getElementById("docs-list");
    if (!listEl) return;
    listEl.innerHTML = '<div class="docs-loading">加载中...</div>';

    try {
        const r = await fetch("/api/v1/documents");
        const data = await r.json();
        const docs = data?.data?.documents || [];

        if (docs.length === 0) {
            listEl.innerHTML = '<div class="docs-loading">暂无文档，请先上传</div>';
            return;
        }

        listEl.innerHTML = docs.map(d => `
            <div class="doc-card">
                <div class="doc-info">
                    <div class="doc-name">${escHtml(d.source)}</div>
                    <div class="doc-meta">${d.chunk_count} 个 chunk · ${(d.bytes / 1024).toFixed(1)} KB · ${(d.uploaded_at || '').substring(0, 16)}</div>
                </div>
                <button class="doc-delete" onclick="deleteDoc('${escHtml(d.source)}')">删除</button>
            </div>
        `).join("");
    } catch (e) {
        listEl.innerHTML = `<div style="text-align:center;color:var(--danger);font-size:13px;padding:20px 0;">加载失败: ${e.message}</div>`;
    }
}

async function deleteDoc(source) {
    if (!confirm(`确认删除 "${source}"?`)) return;
    try {
        const r = await fetch(`/api/v1/documents/${encodeURIComponent(source)}`, {
            method: "DELETE",
            headers: { "X-KB-Admin-Token": getKbAdminToken() },
        });
        const data = await r.json().catch(() => null);
        if (!r.ok || data?.code !== "SUCCESS") {
            if (r.status === 401 || r.status === 403) sessionStorage.removeItem(KB_TOKEN_KEY);
            throw new Error(data?.detail || `HTTP ${r.status}`);
        }
        loadDocs();
    } catch (e) {
        alert(`删除失败: ${e.message}`);
    }
}

function getKbAdminToken() {
    let token = sessionStorage.getItem(KB_TOKEN_KEY) || "";
    if (!token) {
        token = prompt("请输入知识库管理员 Token") || "";
        token = token.trim();
        if (!token) throw new Error("未输入管理员 Token");
        sessionStorage.setItem(KB_TOKEN_KEY, token);
    }
    return token;
}

// ==========================================
// 工具函数
// ==========================================

function escHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

function renderTokenUsage(tokenUsage) {
    if (!tokenUsage) return '';
    const t = tokenUsage;
    const fmt = (n) => n != null ? n.toLocaleString() : '0';

    let html = '<h3>Token 消耗统计</h3><table><tr><th>阶段</th><th>Prompt</th><th>Completion</th><th>小计</th></tr>';

    if (t.analysis_report) {
        html += `<tr>
            <td>分析报告</td>
            <td>${fmt(t.analysis_report.prompt_tokens)}</td>
            <td>${fmt(t.analysis_report.completion_tokens)}</td>
            <td>${fmt(t.analysis_report.total_tokens)}</td>
        </tr>`;
    }

    if (t.suggestion) {
        html += `<tr>
            <td>处理建议</td>
            <td>${fmt(t.suggestion.prompt_tokens)}</td>
            <td>${fmt(t.suggestion.completion_tokens)}</td>
            <td>${fmt(t.suggestion.total_tokens)}</td>
        </tr>`;
    }

    if (t.total && (t.total.total_tokens > 0)) {
        html += `<tr style="font-weight:bold;background:#f8f9fc">
            <td>本次总计</td>
            <td>${fmt(t.total.prompt_tokens)}</td>
            <td>${fmt(t.total.completion_tokens)}</td>
            <td>${fmt(t.total.total_tokens)}</td>
        </tr>`;
    }

    html += '</table>';
    return html;
}
