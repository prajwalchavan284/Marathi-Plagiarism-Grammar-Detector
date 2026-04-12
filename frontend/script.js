const API = window.API_BASE || "http://localhost:8000/api";

// ── Segmented Controls ─────────────────────────────────────────────────────
document.querySelectorAll('.seg-control').forEach(ctrl => {
    ctrl.querySelectorAll('.seg-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            ctrl.querySelectorAll('.seg-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // Hide all panels in the parent card and show the targeted one
            const card = ctrl.closest('.ios-card');
            card.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.getElementById(btn.dataset.target).classList.add('active');
        });
    });
});

// ── File Drop Setup ────────────────────────────────────────────────────────
function setupFile(inputId, chipId) {
    const input = document.getElementById(inputId);
    const chip  = document.getElementById(chipId);
    let file = null;

    input.addEventListener('change', () => {
        file = input.files[0] || null;
        if (file) {
            chip.textContent = file.name;
            chip.classList.remove('hidden');
        } else {
            chip.classList.add('hidden');
        }
    });

    return () => file;
}

const getRefFile    = setupFile('ref-file-input',    'ref-file-name');
const getTargetFile = setupFile('target-file-input', 'target-file-name');

// ── Core Elements ──────────────────────────────────────────────────────────
const analyzeBtn = document.getElementById('analyze-btn');
const btnLabel   = document.getElementById('btn-label');
const btnIcon    = document.getElementById('btn-icon');
const btnSpinner = document.getElementById('btn-spinner');
const errorMsg   = document.getElementById('error-msg');
const resultsEl  = document.getElementById('results');

function setLoading(on) {
    analyzeBtn.disabled = on;
    btnLabel.classList.toggle('hidden', on);
    btnIcon.classList.toggle('hidden', on);
    btnSpinner.classList.toggle('hidden', !on);
    errorMsg.textContent = '';
}

// ── Analyze ────────────────────────────────────────────────────────────────
analyzeBtn.addEventListener('click', async () => {
    const refText    = document.getElementById('ref-text-input').value.trim();
    const targetText = document.getElementById('target-text-input').value.trim();
    const refFile    = getRefFile();
    const targetFile = getTargetFile();

    const isTargetFile = document.querySelector('#target-seg .seg-btn[data-target="target-file-panel"]').classList.contains('active');
    const isRefFile    = document.querySelector('#ref-seg .seg-btn[data-target="ref-file-panel"]').classList.contains('active');

    if (isTargetFile && !targetFile) {
        errorMsg.textContent = 'Please choose a target file to upload.';
        return;
    }
    if (!isTargetFile && !targetText) {
        errorMsg.textContent = 'Please enter the text you want to analyze.';
        return;
    }

    setLoading(true);
    resultsEl.classList.add('hidden');

    try {
        let response;
        const hasFile = isTargetFile || (isRefFile && refFile);

        if (hasFile) {
            const fd = new FormData();
            if (isTargetFile) {
                fd.append('file', targetFile);
            } else {
                fd.append('file', new File([targetText], 'target.txt', { type: 'text/plain' }));
            }
            if (isRefFile && refFile) {
                fd.append('reference_file', refFile);
            } else if (refText) {
                fd.append('reference_text', refText);
            }
            response = await fetch(`${API}/analyze/file`, { method: 'POST', body: fd });
        } else {
            const payload = { text: targetText };
            if (refText) payload.reference_text = refText;
            response = await fetch(`${API}/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
        }

        if (!response.ok) {
            const e = await response.json();
            throw new Error(e.detail || 'Server error');
        }

        const data = await response.json();
        renderResults(data, isTargetFile ? (data.text || '') : targetText);

    } catch (e) {
        errorMsg.textContent = e.message;
    } finally {
        setLoading(false);
    }
});

// ── Render ─────────────────────────────────────────────────────────────────
function renderResults(data, previewText) {
    const plag = data.plagiarism || {};
    const gram = data.grammar   || {};

    // --- Plagiarism Ring ---
    const pct    = Math.round(plag.max_similarity || 0);
    const isPlag = plag.is_plagiarized;
    const circ   = 2 * Math.PI * 50;   // r=50 → 314.16

    const fg = document.getElementById('ring-fg');
    fg.style.strokeDasharray  = circ;
    fg.style.strokeDashoffset = circ - (pct / 100) * circ;
    fg.style.stroke = isPlag ? 'var(--ios-red)' : 'var(--ios-green)';

    const pctEl = document.getElementById('plag-pct');
    pctEl.textContent = `${pct}%`;
    pctEl.style.color = isPlag ? 'var(--ios-red)' : 'var(--ios-green)';

    const pill = document.getElementById('plag-pill');
    pill.textContent = isPlag ? '⚠ Plagiarism Detected' : '✓ Original Content';
    pill.className   = `status-pill ${isPlag ? 'pill-plag' : 'pill-orig'}`;

    const matchEl = document.getElementById('plag-match');
    if (isPlag && plag.matched_document) {
        let txt = plag.matched_document;
        if (plag.matched_sentence) txt += `\n"${plag.matched_sentence.substring(0, 100)}…"`;
        matchEl.textContent = txt;
    } else {
        matchEl.textContent = 'No significant matches found';
    }

    // --- Grammar ---
    const errors = gram.errors || [];
    const countEl = document.getElementById('gram-count');
    countEl.textContent = errors.length;
    countEl.style.color = errors.length > 0 ? 'var(--ios-red)' : 'var(--ios-green)';

    const gList = document.getElementById('grammar-list');
    gList.innerHTML = '';
    if (errors.length === 0) {
        gList.innerHTML = '<div class="no-issues"><i class="bi bi-check-circle-fill"></i> No issues found</div>';
        document.getElementById('grammar-correction-container').style.display = 'none';
    } else {
        errors.forEach(e => {
            const item = document.createElement('div');
            item.className = 'grammar-item';
            const sugs = (e.replacements || []).slice(0, 3)
                .map(r => {
                    // shorten long replacement suggestions
                    const short = r.length > 40 ? r.substring(0, 40) + '…' : r;
                    return `<span class="sug-pill">${short}</span>`;
                }).join('');
            // Show English description as headline, Marathi as subtitle
            const headline = e.english || e.message || 'Grammar issue';
            const subtitle = e.english && e.message ? e.message : '';
            const ctx      = e.context || '';
            item.innerHTML = `
                <div class="gmsg">${headline}</div>
                ${subtitle ? `<div class="gctx" style="color:var(--grey-1);font-style:normal;">${subtitle}</div>` : ''}
                ${ctx ? `<div class="gctx">${ctx}</div>` : ''}
                ${sugs ? `<div class="gsug">${sugs}</div>` : ''}`;
            gList.appendChild(item);
        });
        
        // Show corrected text
        if (gram.corrected_text) {
            document.getElementById('grammar-correction-container').style.display = 'block';
            document.getElementById('grammar-corrected-text').textContent = gram.corrected_text;
        } else {
            document.getElementById('grammar-correction-container').style.display = 'none';
        }
    }

    // --- Preview ---
    const previewCard = document.getElementById('preview-card');
    const pre = document.getElementById('text-preview');
    if (previewText && previewText.trim()) {
        pre.textContent = previewText.trim();
        previewCard.style.display = '';
    } else {
        previewCard.style.display = 'none';
    }

    resultsEl.classList.remove('hidden');
    setTimeout(() => resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50);
}
