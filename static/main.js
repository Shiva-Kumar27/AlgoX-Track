// ============================================================
//  AlgoX Track — main.js
// ============================================================

// ---- Toast ----
function showToast(message, type = 'info', duration = 3000) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.className = `toast ${type}`;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), duration);
}

// ---- Form Validation ----
function initFormValidation() {
    const form = document.querySelector('.problem-form');
    if (!form) return;
    const required = ['title', 'topic', 'difficulty', 'result'];
    const inputs = required.map(id => document.getElementById(id)).filter(Boolean);

    function validateField(input) {
        const group = input.closest('.form-group');
        if (!input.value.trim()) { group.classList.add('error'); return false; }
        group.classList.remove('error'); return true;
    }

    inputs.forEach(input => {
        input.addEventListener('blur', () => validateField(input));
    });

    form.addEventListener('submit', (e) => {
        let valid = true;
        inputs.forEach(input => { if (!validateField(input)) valid = false; });
        if (!valid) {
            e.preventDefault();
            showToast('Please fill all required fields', 'error');
        } else {
            const btn = form.querySelector('button[type="submit"]');
            btn.disabled = true;
            btn.textContent = 'Submitting...';
        }
    });
}

// ---- Textarea auto-resize ----
document.querySelectorAll('textarea').forEach(ta => {
    ta.addEventListener('input', function () {
        this.style.height = 'auto';
        this.style.height = this.scrollHeight + 'px';
    });
});

// ---- Load More Leaderboard ----
let lbOffset = 20, lbLoading = false, lbDone = false;

async function loadMoreLeaderboard() {
    if (lbLoading || lbDone) return;
    const btn = document.getElementById('load-more');
    if (!btn) return;
    lbLoading = true;
    btn.disabled = true;
    btn.textContent = 'Loading...';

    try {
        const res = await fetch(`/api/leaderboard/page?limit=20&offset=${lbOffset}`);
        const rows = await res.json();
        if (!rows.length) {
            lbDone = true;
            btn.style.display = 'none';
            showToast('All entries loaded', 'info');
            return;
        }
        const tbody = document.querySelector('#leaderboard-table tbody');
        rows.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><span class="rank-badge">${row.badge}</span></td>
                <td style="color:var(--text-primary);font-weight:600">${row.username}</td>
                <td>${row.total_solved}</td>
                <td class="difficulty-easy">${row.easy_solved || 0}</td>
                <td class="difficulty-medium">${row.medium_solved || 0}</td>
                <td class="difficulty-hard">${row.hard_solved || 0}</td>
                <td style="font-family:'Roboto',sans-serif">${row.score}</td>
                <td>${row.streak_days > 0 ? row.streak_days + 'd streak' : '—'}</td>
                <td style="font-family:'Roboto',sans-serif;color:var(--text-secondary)">${row.today_solved || 0}</td>
                <td>${row.success_rate}%</td>
            `;
            tbody.appendChild(tr);
        });
        lbOffset += rows.length;
    } catch (err) {
        showToast('Failed to load more', 'error');
    } finally {
        lbLoading = false;
        btn.disabled = false;
        btn.textContent = 'Load More';
    }
}

// ---- Charts ----
const CHART_DEFAULTS = {
    color: '#8A8F98',
    gridColor: 'rgba(42,47,56,0.8)',
    font: { family: "'Roboto', sans-serif", size: 11 }
};

async function initCharts() {
    // Topic doughnut
    const topicCtx = document.getElementById('topicChart')?.getContext('2d');
    if (topicCtx) {
        const data = await fetch('/api/analytics/topic').then(r => r.json());
        new Chart(topicCtx, {
            type: 'doughnut',
            data: {
                labels: data.map(d => d.topic),
                datasets: [{
                    data: data.map(d => d.count),
                    backgroundColor: [
                        '#C5C9D1', '#8A8F98', '#6B7280', '#4B5563',
                        '#374151', '#9CA3AF', '#D1D5DB', '#F3F4F6'
                    ],
                    borderWidth: 0,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'right',
                        labels: { color: '#8A8F98', font: CHART_DEFAULTS.font, boxWidth: 10, padding: 12 }
                    }
                },
                cutout: '72%'
            }
        });
    }

    // Difficulty bar
    const diffCtx = document.getElementById('difficultyChart')?.getContext('2d');
    if (diffCtx) {
        const data = await fetch('/api/analytics/difficulty').then(r => r.json());
        new Chart(diffCtx, {
            type: 'bar',
            data: {
                labels: ['Easy', 'Medium', 'Hard'],
                datasets: [{
                    data: [data.Easy, data.Medium, data.Hard],
                    backgroundColor: ['rgba(74,222,128,0.8)', 'rgba(251,191,36,0.8)', 'rgba(248,113,113,0.8)'],
                    borderRadius: 8,
                    borderSkipped: false
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: CHART_DEFAULTS.gridColor },
                        ticks: { color: CHART_DEFAULTS.color, font: CHART_DEFAULTS.font }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: CHART_DEFAULTS.color, font: CHART_DEFAULTS.font }
                    }
                }
            }
        });
    }

    // Platform Activity (horizontal bar chart)
    await initPlatformActivity();
}

// ---- Platform Activity ----
const PLATFORM_COLORS = {
    'Leetcode': { bar: '#fbbf24', bg: 'rgba(251,191,36,0.12)', text: '#fbbf24' },
    'Codeforces': { bar: '#f87171', bg: 'rgba(248,113,113,0.12)', text: '#f87171' },
    'Manual': { bar: '#60a5fa', bg: 'rgba(96,165,250,0.12)', text: '#60a5fa' },
};
const PLATFORM_DEFAULT = { bar: '#9ca3af', bg: 'rgba(156,163,175,0.12)', text: '#9ca3af' };

async function initPlatformActivity() {
    const container = document.getElementById('platform-activity');
    if (!container) return;
    try {
        const data = await fetch('/api/analytics/platform').then(r => r.json());
        if (!data.length) {
            container.innerHTML = '<div class="text-gray-500 text-sm">No platform data yet — link your accounts in Profile.</div>';
            return;
        }
        container.innerHTML = '';
        data.forEach(item => {
            const colors = PLATFORM_COLORS[item.platform] || PLATFORM_DEFAULT;
            const row = document.createElement('div');
            row.style.cssText = 'margin-bottom:18px';
            row.innerHTML = `
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">
                    <div style="display:flex;align-items:center;gap:8px">
                        <div style="width:8px;height:8px;border-radius:50%;background:${colors.bar}"></div>
                        <span style="color:#e5e7eb;font-size:14px;font-weight:500">${item.platform}</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:10px">
                        <span style="color:${colors.text};font-size:13px;font-weight:600">${item.count} solved</span>
                        <span style="color:#6b7280;font-size:12px;min-width:34px;text-align:right">${item.pct}%</span>
                    </div>
                </div>
                <div style="background:#1f2937;border-radius:6px;height:8px;overflow:hidden">
                    <div class="platform-bar-fill" data-pct="${item.pct}"
                         style="height:100%;width:0%;border-radius:6px;background:${colors.bar};transition:width 0.8s ease"></div>
                </div>
            `;
            container.appendChild(row);
        });
        // Animate bars
        requestAnimationFrame(() => {
            document.querySelectorAll('.platform-bar-fill').forEach(bar => {
                bar.style.width = bar.dataset.pct + '%';
            });
        });
    } catch (e) {
        container.innerHTML = '<div class="text-gray-500 text-sm">Could not load platform data.</div>';
    }
}

// ---- Heatmap Calendar ----
async function initHeatmap() {
    const container = document.getElementById('heatmap-container');
    if (!container) return;

    let heatData = {};
    try {
        const res = await fetch('/api/analytics/heatmap');
        const arr = await res.json();
        arr.forEach(d => { heatData[d.date] = d.count; });
    } catch (e) {
        console.warn('Heatmap data unavailable');
    }

    const today = new Date();
    const startDate = new Date(today);
    startDate.setFullYear(today.getFullYear() - 1);

    // Align to Sunday
    startDate.setDate(startDate.getDate() - startDate.getDay());

    const weeks = [];
    let current = new Date(startDate);

    while (current <= today) {
        const week = [];
        for (let i = 0; i < 7; i++) {
            const dateStr = current.toISOString().split('T')[0];
            const count = heatData[dateStr] || 0;
            week.push({ date: dateStr, count });
            current.setDate(current.getDate() + 1);
        }
        weeks.push(week);
    }

    // Render
    const monthRow = container.querySelector('.heatmap-months');
    const grid = container.querySelector('.heatmap-grid');
    if (!grid) return;

    let lastMonth = -1;
    weeks.forEach((week, wi) => {
        const weekEl = document.createElement('div');
        weekEl.className = 'heatmap-week';

        const firstDay = new Date(week[0].date);
        if (firstDay.getMonth() !== lastMonth) {
            lastMonth = firstDay.getMonth();
            const monthLabel = document.createElement('span');
            monthLabel.style.cssText = `width:${(weeks.length - wi) < 3 ? '0' : '14'}px;overflow:hidden`;
            monthLabel.textContent = firstDay.toLocaleString('default', { month: 'short' });
            if (monthRow) monthRow.appendChild(monthLabel);
        }

        week.forEach(({ date, count }) => {
            const d = new Date(date);
            const cell = document.createElement('div');
            cell.className = 'heatmap-day';
            cell.dataset.count = Math.min(count, 3);
            if (count >= 5) cell.dataset.level = 'max';
            else if (count >= 3) cell.dataset.level = 'high';
            cell.dataset.date = date;
            cell.dataset.fullCount = count;

            // Only show future days as empty
            if (d > today) {
                cell.style.opacity = '0.2';
            }

            cell.addEventListener('mouseenter', (e) => showHMTooltip(e, date, count));
            cell.addEventListener('mouseleave', hideHMTooltip);
            weekEl.appendChild(cell);
        });
        grid.appendChild(weekEl);
    });
}

let hmTooltip = null;
function showHMTooltip(e, date, count) {
    if (!hmTooltip) {
        hmTooltip = document.createElement('div');
        hmTooltip.className = 'hm-tooltip';
        document.body.appendChild(hmTooltip);
    }
    const d = new Date(date);
    const label = d.toLocaleDateString('default', { month: 'short', day: 'numeric', year: 'numeric' });
    hmTooltip.textContent = count ? `${count} problem${count > 1 ? 's' : ''} — ${label}` : `No activity — ${label}`;
    hmTooltip.style.display = 'block';
    positionTooltip(e);
}

function positionTooltip(e) {
    if (!hmTooltip) return;
    hmTooltip.style.left = (e.clientX + 12) + 'px';
    hmTooltip.style.top = (e.clientY - 28) + 'px';
    document.addEventListener('mousemove', (ev) => {
        if (hmTooltip) {
            hmTooltip.style.left = (ev.clientX + 12) + 'px';
            hmTooltip.style.top = (ev.clientY - 28) + 'px';
        }
    }, { once: true });
}

function hideHMTooltip() {
    if (hmTooltip) hmTooltip.style.display = 'none';
}

// ---- XP Bar Animation ----
function animateXPBar() {
    const bar = document.querySelector('.xp-bar-fill');
    if (!bar) return;
    const target = parseInt(bar.dataset.pct || '0');
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = target + '%'; }, 300);
}

function animateAGIBar() {
    const bar = document.querySelector('.agi-bar-fill');
    if (!bar) return;
    const target = parseInt(bar.dataset.score || '0');
    bar.style.width = '0%';
    setTimeout(() => { bar.style.width = target + '%'; }, 500);
}

// ---- Nav highlight ----
function highlightCurrentPage() {
    const path = window.location.pathname;
    document.querySelectorAll('.nav-links a').forEach(link => {
        link.classList.toggle('active', link.getAttribute('href') === path);
    });
}

// ---- Init ----
// ---- Dashboard Refresh ----
function refreshStats() {
    const button = document.querySelector('[onclick="refreshStats()"]');
    if (button) {
        button.disabled = true;
        button.innerHTML = `
            <svg class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
            Refreshing...
        `;
    }

    fetch("/api/stats-refresh")
        .then(response => response.json())
        .then(data => {
            if (data.ok) {
                location.reload();
            } else {
                showToast("Failed to refresh stats", "error");
                if (button) {
                    button.disabled = false;
                    button.innerHTML = `
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                        </svg>
                        Refresh
                    `;
                }
            }
        })
        .catch(error => {
            showToast("Network error while refreshing", "error");
            if (button) {
                button.disabled = false;
                button.innerHTML = `
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                    </svg>
                    Refresh
                `;
            }
        });
}

// ---- Animations for Tailwind Components ----
function animateXPBar() {
    const xpBars = document.querySelectorAll('[data-pct]');
    xpBars.forEach(bar => {
        const pct = bar.getAttribute('data-pct');
        setTimeout(() => {
            bar.style.width = pct + '%';
        }, 100);
    });
}

function animateAGIBar() {
    const agiBars = document.querySelectorAll('[data-score]');
    agiBars.forEach(bar => {
        const score = bar.getAttribute('data-score');
        setTimeout(() => {
            bar.style.width = score + '%';
        }, 100);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    highlightCurrentPage();
    initFormValidation();
    initCharts();
    initHeatmap();
    initRecentSolves();
    animateXPBar();
    animateAGIBar();

    const lbBtn = document.getElementById('load-more');
    if (lbBtn) lbBtn.addEventListener('click', loadMoreLeaderboard);
});

// ---- Recent Solves ----
async function initRecentSolves() {
    const list = document.getElementById('recent-solves-list');
    if (!list) return;
    try {
        const res = await fetch('/api/recent-solves');
        if (!res.ok) return;
        const data = await res.json();
        if (!data.length) {
            list.innerHTML = '<li class="recent-solves-empty">No platform solves yet — link your accounts in Profile to see them here.</li>';
            return;
        }
        list.innerHTML = '';
        data.forEach(p => {
            const platform = p.platform.toLowerCase();
            const li = document.createElement('li');
            li.className = 'recent-solve-item';
            li.innerHTML = `<span class="recent-solve-dot ${platform}"></span><span class="recent-solve-title">${p.title}</span><span class="recent-solve-platform ${platform}">${p.platform}</span>`;
            list.appendChild(li);
        });
    } catch (e) { console.warn('Recent solves unavailable:', e); }
}