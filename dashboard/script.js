document.addEventListener('DOMContentLoaded', () => {
    fetchData();
    setupIRGenerator();
    setupRefreshButton();
});

// ── Data fetching ────────────────────────────────────────────────────────────

async function fetchData() {
    try {
        const response = await fetch('../outputs/secomd_results.json');
        if (!response.ok) throw new Error('Data not found');
        const data = await response.json();
        renderDashboard(data);
        setLastUpdated();
    } catch (error) {
        showListError('tests-ul',   '❌ Could not load data. Run ./run.sh first, then serve via HTTP.');
        showListError('repairs-ul', '');
        console.error(error);
    }
}

function showListError(id, msg) {
    const el = document.getElementById(id);
    if (el) el.innerHTML = msg ? `<li class="loading-row">${msg}</li>` : '';
}

function setLastUpdated() {
    const el = document.getElementById('last-updated');
    if (el) el.textContent = 'Updated ' + new Date().toLocaleTimeString();
}

// ── Dashboard rendering ──────────────────────────────────────────────────────

function renderDashboard(data) {
    const sum = data.summary;

    // Stat counters
    animateCount('stat-total',       sum.total);
    animateCount('stat-passed',      sum.passed);
    animateCount('stat-failed',      sum.failed);
    animateCount('stat-sem-correct', sum.semantically_correct);
    animateCount('stat-sem-wrong',   sum.semantically_wrong);

    // Pass rate bar
    if (sum.total > 0) {
        const pct = Math.round((sum.passed / sum.total) * 100);
        const card = document.getElementById('pass-rate-card');
        const bar  = document.getElementById('progress-bar');
        const pctEl = document.getElementById('pass-rate-pct');
        const sub   = document.getElementById('pass-rate-sub');

        card.style.display = 'block';
        pctEl.textContent  = pct + '%';
        sub.textContent    = `${sum.passed} of ${sum.total} tests passed syntax validation`;
        // Defer so transition fires
        requestAnimationFrame(() => { bar.style.width = pct + '%'; });
    }

    // Test cases
    const testsUl = document.getElementById('tests-ul');
    testsUl.innerHTML = '';
    let delay = 0;
    for (const [name, result] of Object.entries(data.tests)) {
        const statusClass   = result.status   === 'PASS'    ? 'pass'    : 'fail';
        const semanticClass = result.semantic === 'CORRECT' ? 'correct'
                            : result.semantic === 'WRONG'   ? 'wrong'   : 'unknown';
        const semanticText  = result.semantic || 'N/A';

        const li = document.createElement('li');
        li.style.animationDelay = `${delay}s`;
        li.innerHTML = `
            <span class="name" title="${name}">${name}</span>
            <span><span class="badge ${statusClass}">${result.status}</span></span>
            <span><span class="badge ${semanticClass}">${semanticText}</span></span>
            <span class="attempts-col">${result.attempts}</span>
        `;
        testsUl.appendChild(li);
        delay += 0.04;
    }

    // Repair loop
    const repairsUl = document.getElementById('repairs-ul');
    repairsUl.innerHTML = '';
    delay = 0;
    for (const [errorType, result] of Object.entries(data.repair_results)) {
        const statusClass = result.status === 'REPAIRED' ? 'repaired' : 'unrepaired';
        const li = document.createElement('li');
        li.style.animationDelay = `${delay}s`;
        li.innerHTML = `
            <span class="name" title="${errorType}">${errorType}</span>
            <span><span class="badge ${statusClass}">${result.status}</span></span>
            <span class="attempts-col">${result.attempts}</span>
        `;
        repairsUl.appendChild(li);
        delay += 0.08;
    }
}

// ── Live IR Generator ────────────────────────────────────────────────────────

function setupIRGenerator() {
    const btn     = document.getElementById('generate-ir-btn');
    const textarea = document.getElementById('c-code-input');
    const pre     = document.getElementById('ir-output-pre');
    const code    = document.getElementById('ir-output-display');
    const copyBtn = document.getElementById('copy-btn');
    const clearBtn = document.getElementById('clear-btn');

    // Ctrl+Enter shortcut
    textarea.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            btn.click();
        }
    });

    // Tab key inserts spaces instead of blurring
    textarea.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = textarea.selectionStart;
            const end   = textarea.selectionEnd;
            textarea.value = textarea.value.substring(0, start) + '    ' + textarea.value.substring(end);
            textarea.selectionStart = textarea.selectionEnd = start + 4;
        }
    });

    // Generate button
    btn.addEventListener('click', async () => {
        const cCode = textarea.value.trim();
        if (!cCode) {
            showIRError(pre, code, 'Please enter some C code.');
            return;
        }

        setGenerating(btn, true);
        pre.className = '';
        code.textContent = 'Generating…';

        try {
            const response = await fetch('/compile', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ c_code: cCode }),
            });
            const data = await response.json();

            if (data.status === 'success') {
                pre.className = '';
                code.textContent = data.ir;
            } else {
                showIRError(pre, code, 'Compilation Error:\n\n' + data.error);
            }
        } catch (err) {
            showIRError(pre, code,
                'Network Error: Could not reach the compilation server.\n' +
                'Make sure serve_dashboard.sh is running (starts server.py).'
            );
            console.error(err);
        } finally {
            setGenerating(btn, false);
        }
    });

    // Copy button
    copyBtn.addEventListener('click', async () => {
        const text = code.textContent;
        if (!text || text === 'Output will appear here...') return;
        try {
            await navigator.clipboard.writeText(text);
            copyBtn.textContent = '✓ Copied';
            copyBtn.style.color = 'var(--green)';
            setTimeout(() => {
                copyBtn.innerHTML = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg> Copy`;
                copyBtn.style.color = '';
            }, 2000);
        } catch {}
    });

    // Clear button
    clearBtn.addEventListener('click', () => {
        textarea.value = '';
        textarea.focus();
        pre.className = '';
        code.textContent = 'Output will appear here...';
    });
}

function showIRError(pre, code, msg) {
    pre.className = 'error-state';
    code.textContent = msg;
}

function setGenerating(btn, loading) {
    const icon    = btn.querySelector('.btn-icon');
    const spinner = btn.querySelector('.btn-spinner');
    btn.disabled = loading;
    if (icon)    icon.style.display    = loading ? 'none' : '';
    if (spinner) spinner.style.display = loading ? ''     : 'none';
}

// ── Refresh button ───────────────────────────────────────────────────────────

function setupRefreshButton() {
    const btn = document.getElementById('refresh-btn');
    if (!btn) return;
    btn.addEventListener('click', () => {
        btn.style.transform = 'rotate(360deg)';
        btn.style.transition = 'transform 0.6s ease';
        fetchData();
        setTimeout(() => {
            btn.style.transform = '';
            btn.style.transition = '';
        }, 650);
    });
}

// ── Counter animation ────────────────────────────────────────────────────────

function animateCount(id, end) {
    const el = document.getElementById(id);
    if (!el) return;
    if (end === 0) { el.textContent = '0'; return; }

    const duration  = 900;
    const fps       = 60;
    const increment = end / (duration / (1000 / fps));
    let current = 0;

    function step() {
        current += increment;
        if (current >= end) {
            el.textContent = end;
        } else {
            el.textContent = Math.floor(current);
            requestAnimationFrame(step);
        }
    }
    requestAnimationFrame(step);
}
