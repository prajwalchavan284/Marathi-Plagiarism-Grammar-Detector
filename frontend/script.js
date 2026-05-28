const API = window.API_BASE || "http://localhost:8000/api";

document.querySelectorAll('.seg-control').forEach(ctrl => {
    ctrl.querySelectorAll('.seg-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            ctrl.querySelectorAll('.seg-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const card = ctrl.closest('.ios-card');
            card.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            document.getElementById(btn.dataset.target).classList.add('active');
        });
    });
});

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

function renderResults(data, previewText) {
    const plag = data.plagiarism || {};
    const gram = data.grammar   || {};

    const pct = Math.round(plag.max_similarity || 0);
    const circ = 2 * Math.PI * 48;

    let ringGradient, ringColor, pillText, pillClass, glowClass;

    if (pct <= 15) {
        ringGradient = 'url(#ring-grad-green)';
        ringColor = '#27ae60';
        pillText = '✓ Original Content';
        pillClass = 'pill-orig';
        glowClass = 'ring-glow-green';
    } else if (pct <= 50) {
        ringGradient = 'url(#ring-grad-yellow)';
        ringColor = '#f39c12';
        pillText = '⚠ Moderate Match';
        pillClass = 'pill-warn';
        glowClass = 'ring-glow-yellow';
    } else {
        ringGradient = 'url(#ring-grad-red)';
        ringColor = '#e74c3c';
        pillText = '⚠ Plagiarism Detected';
        pillClass = 'pill-plag';
        glowClass = 'ring-glow-red';
    }

    const pctEl = document.getElementById('plag-pct');
    pctEl.textContent = `${pct}%`;
    pctEl.style.color = ringColor;

    const pill = document.getElementById('plag-pill');
    pill.textContent = pillText;
    pill.className = `status-pill ${pillClass}`;

    const matchEl = document.getElementById('plag-match');
    const isMatched = pct > 0;
    if (isMatched && plag.matched_document) {
        let txt = plag.matched_document;
        if (plag.matched_sentence) txt += `\n"${plag.matched_sentence.substring(0, 100)}…"`;
        matchEl.textContent = txt;
    } else {
        matchEl.textContent = 'No significant matches found';
    }

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
                    const short = r.length > 40 ? r.substring(0, 40) + '…' : r;
                    return `<span class="sug-pill">${short}</span>`;
                }).join('');
            const headline = e.english || 'Grammar Issue';
            const subtitle = e.message || '';
            const sevLabel = (e.severity || '').toLowerCase();
            const sevClass = sevLabel === 'critical' ? 'sev-critical'
                           : sevLabel === 'warning'  ? 'sev-warning'
                           :                           'sev-suggestion';
            item.innerHTML = `
                <div class="gmsg">${headline} <span class="sev-badge ${sevClass}">${sevLabel}</span></div>
                ${subtitle ? `<div class="gctx" style="color:var(--grey-1);font-style:normal;">${subtitle}</div>` : ''}
                ${sugs ? `<div class="gsug">${sugs}</div>` : ''}`;
            gList.appendChild(item);
        });
        
        if (gram.corrected_text) {
            document.getElementById('grammar-correction-container').style.display = 'block';
            document.getElementById('grammar-corrected-text').textContent = gram.corrected_text;
        } else {
            document.getElementById('grammar-correction-container').style.display = 'none';
        }
    }

    resultsEl.classList.remove('hidden');
    
    setTimeout(() => {
        const fg = document.getElementById('ring-fg');
        fg.setAttribute('stroke-dasharray', circ);
        fg.setAttribute('stroke-dashoffset', circ - (pct / 100) * circ);
        fg.style.stroke = ringGradient;
        
        fg.classList.remove('ring-glow-green', 'ring-glow-yellow', 'ring-glow-red');
        fg.classList.add(glowClass);
        
        resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
}
