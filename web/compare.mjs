import {validateReport, parseInputText} from './comparison-report.mjs';
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = value => value.toLocaleString('en');
const hex = value => '0x' + value.toString(16).padStart(8, '0');
let runner = {enabled:false}, sources = {}, result, selected, failuresOnly = false, imported = false, busy = false;
function error(message) { $('#comparison-error').hidden = !message; $('#comparison-error').textContent = message; }
function readiness() {
  $('#run-comparison').disabled = busy || !runner.enabled || !sources.reference || !sources.candidate || !$('#trusted').checked;
  $('#run-hint').textContent = busy ? 'Compiling C, then running both programs. This can take up to 30 seconds.' :
    !runner.enabled ? 'Start the local runner to enable execution.' : !sources.reference || !sources.candidate ? 'Choose both files, or load the starter files.' :
    !$('#trusted').checked ? 'Confirm that you trust the selected programs to enable the run.' : 'Ready. Your programs will run on this computer.';
}
function invalidate() {
  if (result) { result = null; $('#result-content').innerHTML = '<div class="comparison-empty"><p class="empty-title">Programs or inputs changed.</p><p>Run the comparison again to see results for these selections.</p></div>'; }
  error(''); readiness();
}
async function selectSource(kind, file) {
  if (!file) return;
  if (file.size > 256 * 1024) throw new Error('Choose a source file smaller than 256 KiB.');
  const text = await file.text();
  if (!text.trim()) throw new Error('The selected source file is empty.');
  sources[kind] = {text, name:file.name};
  $(`#${kind}-name`).textContent = file.name;
  $('#load-corrected').hidden = true;
  invalidate();
}
for (const kind of ['reference','candidate']) $(`#${kind}-file`).addEventListener('change', async event => {
  delete sources[kind]; $(`#${kind}-name`).textContent = 'No file selected.'; invalidate();
  try { await selectSource(kind, event.target.files[0]); } catch (cause) { error(cause.message); }
});
$('#trusted').addEventListener('change', readiness);
for (const id of ['function-name','case-inputs','random-count','random-seed']) $(`#${id}`).addEventListener('input', invalidate);
$('#load-starter').addEventListener('click', async () => {
  try {
    const read = async name => { const response = await fetch(`starter/${name}`); if (!response.ok) throw new Error('Starter files could not load. Reload this page and try again.'); return response.text(); };
    const [reference,candidate,inputs] = await Promise.all([read('reference.c'),read('candidate.py'),read('inputs.txt')]);
    sources = {reference:{text:reference,name:'reference.c'},candidate:{text:candidate,name:'candidate.py'}};
    $('#reference-file').value = ''; $('#candidate-file').value = '';
    $('#reference-name').textContent = 'reference.c · starter'; $('#candidate-name').textContent = 'candidate.py · deliberate missing-wrap bug';
    $('#function-name').value = 'evaluate'; $('#case-inputs').value = inputs; $('#random-count').value = '0';
    $('#load-corrected').hidden = false; $('#trusted').checked = false; invalidate();
  } catch (cause) { error(cause.message); }
});
$('#load-corrected').addEventListener('click', async () => {
  try {
    const response = await fetch('starter/corrected.py'); if (!response.ok) throw new Error('Corrected starter could not load.');
    sources.candidate = {text:await response.text(),name:'corrected.py'};
    $('#candidate-file').value = ''; $('#candidate-name').textContent = 'corrected.py · one-byte wrap restored'; invalidate();
  } catch (cause) { error(cause.message); }
});
$('#compare-form').addEventListener('submit', async event => {
  event.preventDefault(); if ($('#run-comparison').disabled) return;
  error('');
  try {
    const count = Number($('#random-count').value), seed = Number($('#random-seed').value);
    const total = parseInputText($('#case-inputs').value) + count;
    if (!Number.isInteger(count) || count < 0 || count > 200 || !Number.isInteger(seed) || seed < 0 || seed > 0xffffffff)
      throw new Error('Check the random input count and seed.');
    if (total < 1 || total > 256) throw new Error('Provide between 1 and 256 total inputs.');
    busy = true; $('#program-fields').disabled = true; $('#report-file').disabled = true; readiness();
    const response = await fetch('/api/compare', {method:'POST',headers:{'Content-Type':'application/json','X-ReverseLab-Token':runner.token},
      body:JSON.stringify({reference:sources.reference.text,candidate:sources.candidate.text,referenceName:sources.reference.name,
        candidateName:sources.candidate.name,function:$('#function-name').value,inputs:$('#case-inputs').value,count,seed,trusted:true})});
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || 'Comparison failed.');
    showReport(validateReport(payload), false);
  } catch (cause) { error(cause instanceof TypeError ? 'The local runner could not be reached. Keep its terminal running, then try again.' : cause.message); }
  finally { busy = false; $('#program-fields').disabled = false; $('#report-file').disabled = false; readiness(); }
});
$('#report-file').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  try {
    if (file.size > 1024 * 1024) throw new Error('Report exceeds the 1 MiB limit.');
    showReport(validateReport(JSON.parse(await file.text())), true); error('');
  } catch (cause) { error(cause instanceof SyntaxError ? 'The report is not valid JSON. Choose the downloaded comparison report.' : cause.message); }
  event.target.value = '';
});
function showReport(report, isImported) {
  result = report; imported = isImported; failuresOnly = false;
  selected = report.cases.find(row => !row.passed)?.id || report.cases[0].id;
  renderResult(); $('#results-title').focus();
}
function download(name, text, type) {
  const url = URL.createObjectURL(new Blob([text],{type})); const link = document.createElement('a');
  link.href = url; link.download = name; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}
function renderResult() {
  const row = result.cases.find(item => item.id === selected);
  const rows = result.cases.filter(item => !failuresOnly || !item.passed);
  $('#result-content').innerHTML = `<p class="report-origin">${imported ? 'Imported report · not rerun or authenticated' : 'Executed locally · C compiled and Python run separately'}</p>
    <div class="custom-verdict ${result.failed ? 'has-differences' : ''}"><h3>${result.failed ? `${fmt(result.failed)} of ${fmt(result.total)} inputs differ.` : `Both programs agree on ${fmt(result.total)} inputs.`}</h3><p>${result.errors ? `${fmt(result.errors)} Python input${result.errors === 1 ? '' : 's'} raised an error. ` : ''}${result.failed ? 'Inspect an input below to see the two answers.' : 'No disagreement was found in this test set. Other inputs may behave differently.'}</p></div>
    <div class="report-actions"><button id="download-report" class="btn" type="button">Download report</button><button id="download-inputs" class="text-button" type="button">Download exact inputs</button></div>
    <div class="custom-case-inspector"><p class="explanation-step">${esc(row.label)} · ${row.passed ? 'Same output' : row.error ? 'Python error' : 'Different outputs'}</p><h3>Same input to both programs</h3><pre class="custom-input">${esc(row.hex ? row.hex.match(/../g).join(' ') : '(empty input)')}</pre><div class="decoder-columns"><div class="decoder-output"><h3>Reference · C</h3><p class="custom-output">${fmt(row.expected)}</p><p class="decoded-hex">${hex(row.expected)}</p></div><div class="decoder-output"><h3>Rewrite · Python</h3>${row.error ? `<p class="custom-python-error">${esc(row.error)}</p>` : `<p class="custom-output">${fmt(row.actual)}</p><p class="decoded-hex">${hex(row.actual)}</p>`}</div></div></div>
    <div class="case-table-heading"><h3>All tested inputs</h3><label><input id="failures-only" type="checkbox" ${failuresOnly ? 'checked' : ''}> Differences only</label></div><div class="table-scroll"><table><thead><tr><th scope="col">Input</th><th scope="col">Bytes</th><th scope="col">Result</th></tr></thead><tbody>${rows.length ? rows.map(item => `<tr class="${item.id === selected ? 'selected' : ''}"><td><button class="case-button" type="button" data-case="${esc(item.id)}" ${item.id === selected ? 'aria-current="true"' : ''}>${esc(item.label)}</button></td><td class="mono">${item.hex.length / 2}</td><td>${item.error ? 'Python error' : item.passed ? 'Same' : 'Different'}</td></tr>`).join('') : '<tr><td colspan="3">No differences in this report.</td></tr>'}</tbody></table></div>
    <details class="run-receipt"><summary>Files, environment and diagnostics</summary><dl class="definition-list"><dt>C file</dt><dd>${esc(result.reference.name)}</dd><dt>C source SHA-256</dt><dd class="hash">${result.reference.sha256}</dd><dt>Binary SHA-256</dt><dd class="hash">${result.reference.artifactSha256}</dd><dt>Python file</dt><dd>${esc(result.candidate.name)} · ${esc(result.candidate.entryPoint)}()</dd><dt>Python SHA-256</dt><dd class="hash">${result.candidate.sha256}</dd><dt>Run environment</dt><dd>${esc(result.environment.system)} ${esc(result.environment.architecture)} · Python ${esc(result.environment.python)}</dd><dt>Created</dt><dd>${esc(result.createdAt)}</dd><dt>Random inputs</dt><dd>${result.generation.randomCount} · seed ${result.generation.seed}</dd></dl><h3>Compiler</h3><pre class="command">${esc(result.environment.compiler)}
${esc(result.environment.compilerFlags.join(' '))}</pre>${['compiler','reference','candidate'].map(kind => `<h3>${kind === 'compiler' ? 'Compiler warnings' : kind === 'reference' ? 'C stderr' : 'Python stderr'}</h3><pre class="command">${esc(result.diagnostics[kind] || 'No diagnostics.')}</pre>`).join('')}<p class="form-help">Use Download exact inputs to rerun this corpus, including generated inputs. Select the same source files and set extra random inputs to 0. Hashes identify content; they do not authenticate a report.</p></details>`;
  $('#download-report').addEventListener('click', () => download('reverselab-comparison.json', JSON.stringify(result,null,2)+'\n','application/json'));
  $('#download-inputs').addEventListener('click', () => download('reverselab-inputs.txt', result.cases.map(item => item.hex || '-').join('\n')+'\n','text/plain'));
  $('#failures-only').addEventListener('change', event => { failuresOnly = event.target.checked; renderResult(); $('#failures-only').focus(); });
  document.querySelectorAll('[data-case]').forEach(button => button.addEventListener('click', () => { selected = button.dataset.case; renderResult(); document.querySelector(`[data-case="${CSS.escape(selected)}"]`).focus(); }));
}
async function connect() {
  try {
    if (location.hostname !== '127.0.0.1') throw new Error('Hosted');
    const response = await fetch('/api/status'); if (!response.ok) throw new Error('Unavailable');
    runner = await response.json();
    if (runner.enabled !== true || typeof runner.token !== 'string') throw new Error('Disabled');
    $('#runner-status').textContent = 'Local runner connected. Programs run on this computer; no source files are sent to a hosted service.';
  } catch {
    runner = {enabled:false}; $('#runner-status').textContent = 'Report viewer · local execution is not connected.'; $('#local-setup').hidden = false;
  }
  readiness();
}
$('#results-title').tabIndex = -1;
connect();
