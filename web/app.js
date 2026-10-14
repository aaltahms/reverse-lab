const app = document.querySelector('#app');
const views = ['investigation', 'evidence', 'candidate', 'verification', 'build', 'reference'];
const labels = ['Investigation', 'Native evidence', 'Candidate', 'Verification', 'Build record', 'Reference source'];
let data;
let revealed = false;
const state = { fixture: 'checksum', variant: 'O2', view: 'investigation', candidate: 'reconstruct', corpus: 'development', evidence: 'disassembly', filter: 'all', query: '', case: '', codeQuery: '', page: 0 };
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = value => new Intl.NumberFormat('en').format(value);
const hex = value => `0x${value.toString(16).padStart(8, '0')}`;
const tag = (text, kind = '') => `<span class="tag ${kind}">${esc(text)}</span>`;
const code = (text, light = false, compact = false) => `<pre class="code ${light ? 'light' : ''} ${compact ? 'compact' : ''}"><code>${text.split('\n').map((line, i) => `<span data-code-line="${i+1}" class="code-line ${state.codeQuery && line.toLowerCase().includes(state.codeQuery.toLowerCase()) ? 'match' : ''}"><span class="line-number" aria-hidden="true">${i + 1}</span>${esc(line)}</span>`).join('')}</code></pre>`;
function selected() {
  const fixture = data.fixtures.find(f => f.id === state.fixture) || data.fixtures[0];
  const variant = fixture.variants.find(v => v.id === state.variant) || fixture.variants.find(v=>v.id==='O2') || fixture.variants[0];
  if (state.corpus === 'heldout' && !variant.evaluationReports?.length) state.corpus = 'development';
  const reports = state.corpus === 'heldout' ? variant.evaluationReports : variant.reports;
  const report = reports.find(r => r.id === state.candidate) || reports[0];
  return {fixture, variant, report};
}
function readURL() {
  const params = new URLSearchParams(location.search);
  state.corpus = params.get('corpus') === 'heldout' ? 'heldout' : 'development';
  for (const key of ['fixture','variant','view','candidate','case','filter','evidence']) if (params.has(key)) state[key] = params.get(key);
  if (!['disassembly','symbols','artifact','locations','ghidra'].includes(state.evidence)) state.evidence='disassembly';
  if (!views.includes(state.view)) state.view = 'investigation';
  if (!['all','failed','passed','boundary','seeded','held-out'].includes(state.filter)) state.filter = 'all';
  const {fixture, variant, report} = selected();
  if ((state.corpus === 'heldout' && ['boundary','seeded'].includes(state.filter)) || (state.corpus === 'development' && state.filter === 'held-out')) state.filter = 'all';
  state.fixture = fixture.id; state.variant = variant.id; state.candidate = report.id;
}
function change(patch, options = {}) {
  Object.assign(state, patch);
  const params = new URLSearchParams();
  for (const key of ['fixture','variant','view','candidate','case','filter','evidence','corpus']) if (state[key]) params.set(key, state[key]);
  history.pushState(null, '', `?${params}`);
  render(options.focus);
}
function pathButton(number, title, view) {
  return `<button data-view="${view}" class="${state.view === view ? 'active' : ''}" ${state.view === view ? 'aria-current="step"' : ''}><span>${number}</span><strong>${title}</strong></button>`;
}
function render(focus) {
  const {fixture, variant, report} = selected();
  const good = variant.reports[0];
  app.innerHTML = `<div class="shell">
    <aside class="sidebar" aria-label="Fixture navigation">
      <div><div class="brand"><span class="mark" aria-hidden="true">[r]</span> ReverseLab</div><div class="brand-sub">Behavior, recovered.</div></div>
      <div><p class="side-label">Experiment library / ${String(data.fixtures.length).padStart(2,'0')}</p><nav class="fixture-list">${data.fixtures.map((f,i) => `<button class="fixture-button ${f.id === fixture.id ? 'active' : ''}" data-fixture="${f.id}" ${f.id === fixture.id ? 'aria-current="true"' : ''}><span class="fixture-index">0${i+1}</span><span><strong>${esc(f.title)}</strong><small>${esc(f.id)}.c · ${f.variants.length} builds</small></span></button>`).join('')}</nav></div>
      <div class="side-note"><strong><span class="dot"></span> Native pipeline exercised</strong><p>Owned C → Clang → native tools → Python candidate → differential tests.</p><p>Educational experiment. Reference source was known during authorship.</p><a href="data/report.json" download="reverselab-report.json">Download evidence JSON ↗</a></div>
    </aside>
    <div class="workspace"><header class="topbar"><div class="crumb">LAB / <b>${esc(fixture.id.toUpperCase())}</b> / ${esc(variant.id)}</div><div class="record"><span class="dot"></span><span>Evidence recording</span><span class="record-date">· ${esc(new Date(data.generatedAt).toLocaleDateString('en-CA'))}</span></div></header>
      <main id="main" class="main" tabindex="-1"><div class="hero"><div><p class="eyebrow">Experiment ${String(data.fixtures.indexOf(fixture)+1).padStart(2,'0')} / ${esc(data.platform.architecture)} · ${esc(data.platform.system)}</p><h1>${esc(fixture.title)}</h1><p class="subhead">${esc(fixture.subtitle)} Inspect the artifact, follow the interpretation, test the behavior.</p></div><div class="variants"><label>Build variant</label><div class="segmented" role="group" aria-label="Build variant">${fixture.variants.map(v => `<button data-variant="${v.id}" class="${v.id===variant.id?'active':''}" aria-pressed="${v.id===variant.id}">${esc(v.label || `-${v.id}`)}</button>`).join('')}</div><div class="small-muted">${fmt(variant.size)} bytes · ${variant.stripped?'symbols stripped':'debug symbols'}</div></div></div>
      <nav class="path" aria-label="Investigation path">${pathButton('01 / TARGET','Compiled artifact','build')}${pathButton('02 / OBSERVE','Native evidence','evidence')}${pathButton('03 / INTERPRET','Authored candidate','candidate')}${pathButton('04 / CHALLENGE','Behavioral tests','verification')}${pathButton('05 / REVEAL','Reference source','reference')}</nav>
      <div class="tablist" role="tablist" aria-label="Investigation views">${views.map((view,i) => `<button id="tab-${view}" role="tab" aria-selected="${state.view===view}" aria-controls="view-panel" tabindex="${state.view===view?0:-1}" data-view="${view}">${labels[i]}</button>`).join('')}</div>
      <section id="view-panel" role="tabpanel" aria-labelledby="tab-${state.view}" tabindex="0">${content(fixture,variant,report,good)}</section>
      <footer class="foot"><span>Recorded execution · ${fmt(state.view==='verification'?report.total:good.total)} inputs / candidate / build · ${state.view==='verification' && state.corpus==='heldout'?'held-out evaluation':'development corpus'}</span><span>Sampled agreement is evidence, not an equivalence proof.</span></footer></main>
    </div></div>`;
  bind();
  const tablist = document.querySelector('.tablist');
  const activeTab = document.querySelector('[role=tab][aria-selected=true]');
  if (activeTab.offsetLeft + activeTab.offsetWidth > tablist.clientWidth) tablist.scrollLeft = activeTab.offsetLeft + activeTab.offsetWidth - tablist.clientWidth;
  if (focus) document.querySelector(focus)?.focus();
}
function content(f, v, r, good) {
  if (state.view === 'investigation') return overview(f,v,good);
  if (state.view === 'evidence') return evidenceView(f,v);
  if (state.view === 'candidate') return candidateView(f);
  if (state.view === 'verification') return verificationView(f,v,r);
  if (state.view === 'build') return buildView(f,v);
  return referenceView(f);
}
function overview(f,v,r) {
  const mutant = v.reports.find(report => report.intentionalFault);
  return `<div class="section-heading"><h2>A question, backed by evidence.</h2>${tag('SOURCE-KNOWN EXPERIMENT','neutral')}</div><div class="question">${esc(f.question)}</div>
    <div class="grid"><div><div class="panel"><div class="panel-head"><h3>Interpretation ledger</h3><span class="small-muted">${f.claims.length} authored findings</span></div>${f.claims.map((claim,i) => `<article class="claim"><div class="claim-number">INTERPRETATION / 0${i+1}</div><h3>${esc(claim.title)}</h3><p>${esc(claim.detail)}</p><span class="basis">${esc(claim.basis)}</span></article>`).join('')}<div class="panel-footer"><span class="small-muted">Assembly is an observation; meaning is an interpretation.</span><button class="text-button" data-view="evidence">Inspect evidence →</button></div></div><div class="uncertainty"><strong>Still uncertain.</strong> ${esc(f.uncertainty)}</div></div>
    <div><div class="panel"><div class="panel-head"><h3>Observed agreement</h3>${tag('RECOVERED CANDIDATE')}</div><div class="panel-body"><div class="metrics"><strong>${fmt(r.passed)}</strong><span>/ ${fmt(r.total)} cases passed</span></div><div class="bar"><div style="width:${r.passed/r.total*100}%"></div></div><div class="result-line"><span>Directed boundary cases</span><strong>${fmt(r.cases.filter(c=>c.group==='boundary').length)}</strong></div><div class="result-line"><span>Seeded inputs</span><strong>${fmt(r.cases.filter(c=>c.group==='seeded').length)}</strong></div><div class="result-line"><span>Detected mismatches</span><strong class="${r.failed?'fail':'pass'}">${r.failed}</strong></div>${v.evidence.ghidra?.status==='available'?`<div class="callout" style="margin-top:12px;margin-bottom:0"><strong>Decompiler evidence attached.</strong> ${fmt(v.evidence.ghidra.output.split('\n').length)} lines from Ghidra ${esc(v.evidence.ghidra.ghidraVersion)}. <button class="text-button" data-ghidra>Inspect pseudocode →</button></div>`:''}${mutant?`<div class="callout fault" style="margin-top:12px;margin-bottom:0"><strong>Fault detected.</strong> The deliberate endian candidate disagrees on ${mutant.failed} inputs. <button class="text-button" data-mutant>Inspect counterexamples →</button></div>`:''}<p class="note">Compared with actual compiled reference execution. Candidate authored in Python with the reference source known.</p></div><div class="panel-footer"><span class="mono small-muted">${esc(v.artifact)}</span><button class="text-button" data-view="verification">Explore cases →</button></div></div></div></div>`;
}
function evidenceView(f,v) {
  const kind = ['disassembly','symbols','artifact','locations','ghidra'].includes(state.evidence) ? state.evidence : 'disassembly';
  const item = v.evidence[kind] || {status:'unexercised',output:'',error:'No Ghidra recording for this artifact. Analysis is an optional CLI step; select the packet stripped variant when available.',command:'python3 -m lab.decompile',exitCode:null};
  const titles = {disassembly:'Function disassembly',symbols:'Symbol table',artifact:'Artifact information',locations:'Source locations',ghidra:'Ghidra pseudocode'};
  return `<div class="section-heading"><h2>Read what the tools observed.</h2>${tag(item.status.toUpperCase(),item.status==='available'?'':'fault')}</div>
    <div class="evidence-tabs" role="group" aria-label="Evidence type">${Object.keys(titles).map(k => `<button data-evidence="${k}" class="${k===kind?'active':''}" aria-pressed="${k===kind}">${titles[k]}</button>`).join('')}</div>
    ${kind==='ghidra' && item.status==='available'?`<div class="callout"><strong>Actual Ghidra decompiler output through REA.</strong> Inferred pseudocode is not original C or the Python candidate. ${esc(item.selection)}${item.origin==='imported-record'?' Imported recording; this import did not execute a provider.':''}<br><span class="small-muted">${esc(item.ghidraVersion)} · REA ${esc(item.reaVersion)} · procedure ${esc(item.procedure)}${item.rawEvidencePath?` · <a href="${esc(item.rawEvidencePath)}" download>Download complete REA Evidence</a>`:''}</span></div>`:''}
    ${kind==='locations'?'<div class="callout">Debug locations are source-derived information. This view reveals file names and line numbers from the debug build; it is not a source-blind analysis.</div>':''}
    <div class="code-control"><input class="field" id="code-search" aria-label="Highlight text in evidence" placeholder="Highlight an address, instruction, or symbol…" value="${esc(state.codeQuery)}"><span class="search-status" id="code-matches">${state.codeQuery?`${item.output.split('\n').filter(line=>line.toLowerCase().includes(state.codeQuery.toLowerCase())).length} matching lines`:''}</span><button class="btn" id="jump-match" ${state.codeQuery && item.output.toLowerCase().includes(state.codeQuery.toLowerCase())?'':'disabled'}>Jump to match</button><button class="btn" data-copy="evidence">Copy raw output</button></div>
    ${kind==='ghidra' && item.highlights?.length?`<div class="evidence-tabs" role="group" aria-label="Decompiler landmarks">${item.highlights.map(h=>`<button data-code-jump="${h.line}">${esc(h.label)} · L${h.line}</button>`).join('')}</div>`:''}
    <div class="panel"><div class="panel-head"><h3>${titles[kind]}</h3><span class="source-link">${esc(v.artifact)} · ${esc(data.platform.architecture)}</span></div>${item.status==='available'?code(item.output):`<div class="empty">${esc(item.error||'No output retained. This tool was unavailable.')}</div>`}<div class="panel-footer"><span class="mono small-muted">$ ${esc(item.command)}</span><span class="small-muted">exit ${item.exitCode??'—'}</span></div></div>
    <div class="uncertainty"><strong>Provenance.</strong> ${kind==='ghidra'?'Provider pseudocode and unchanged REA JSON are retained for this exact artifact':'Native-tool output (project-root paths normalized to “.”) is retained for this exact artifact'} (SHA-256 <span class="hash">${v.sha256.slice(0,16)}…</span>). ${kind==='ghidra'?'Decompiler text is a static observation; only the separately verified Python candidate has differential results.':v.stripped?'Names and debug information were stripped. The disassembly range was selected from its symbol-bearing twin.':'Labels and debug symbols are present. This native listing is assembly, not decompiler output.'}${item.error?`<p>${esc(item.error)}</p>`:''}${kind==='ghidra' && item.limitations?.length?`<details style="margin-top:12px"><summary>Provider limitations (${item.limitations.length})</summary>${item.limitations.map(value=>`<p>${esc(value)}</p>`).join('')}</details><p class="hash" style="margin-top:12px">Evidence ${esc(item.evidenceId)} · raw JSON SHA-256 ${esc(item.rawEvidenceSha256)}</p>`:''}</div>`;
}
function candidateView(f) {
  return `<div class="section-heading"><h2>A reconstruction you can challenge.</h2>${tag('AGENT-AUTHORED PYTHON','neutral')}</div><div class="callout">${esc(f.reconstruction.authorship)} The candidate uses an independent expression or table model. Its agreement is checked against a compiled C executable.</div><div class="panel"><div class="panel-head"><h3>${esc(f.reconstruction.path)}</h3><button class="text-button" data-copy="candidate">Copy candidate</button></div>${code(f.reconstruction.text)}<div class="panel-footer"><span class="hash">SHA-256 ${f.reconstruction.sha256}</span><button class="text-button" data-view="verification">Test interpretation →</button></div></div><div class="uncertainty"><strong>Behavior contract.</strong> ${esc(f.contract)}</div>`;
}
function verificationView(f,v,r) {
  const heldout = state.corpus === 'heldout';
  let cases = r.cases.filter(c => state.filter === 'failed' ? !c.passed : state.filter === 'passed' ? c.passed : ['boundary','seeded','held-out'].includes(state.filter) ? c.group===state.filter : true);
  const query = state.query.toLowerCase();
  if (query) cases = cases.filter(c=> `${c.id} ${c.label} ${c.hex}`.toLowerCase().includes(query));
  const selectedIndex = cases.findIndex(c=>c.id===state.case);
  if (selectedIndex >= 0) state.page = Math.floor(selectedIndex / 50);
  const pages = Math.max(1, Math.ceil(cases.length / 50));
  state.page = Math.min(state.page, pages-1);
  const visible = cases.slice(state.page*50, (state.page+1)*50);
  const chosen = visible.find(c=>c.id===state.case) || visible[0];
  return `<div class="section-heading"><h2>Challenge the recovered behavior.</h2>${tag(r.failed?'MISMATCHES OBSERVED':'SAMPLED AGREEMENT',r.failed?'fault':'')}</div>
    <div class="evidence-tabs" role="group" aria-label="Test corpus"><button data-corpus="development" class="${heldout?'':'active'}" aria-pressed="${!heldout}">Development corpus</button><button data-corpus="heldout" class="${heldout?'active':''}" aria-pressed="${heldout}" ${v.evaluationReports?.length?'':'disabled'}>Held-out evaluation${v.evaluationReports?.length?'':' · not recorded'}</button></div>
    ${heldout?`<div class="callout"><strong>Candidate frozen before these inputs were generated.</strong> ${fmt(r.total)} unique inputs; zero byte-for-byte overlap with this fixture’s development corpus. Source was known during authorship.<details style="margin-top:10px"><summary>Freeze and evaluation record</summary><dl class="definition-list"><dt>Candidate frozen</dt><dd>${esc(data.evaluation.frozenAt)}</dd><dt>Seed selected</dt><dd>${esc(data.evaluation.seedSelectedAt)}</dd><dt>Evaluation completed</dt><dd>${esc(data.evaluation.evaluatedAt)}</dd><dt>Seed selection</dt><dd>${esc(data.evaluation.seedSelection)}</dd><dt>Freeze SHA-256</dt><dd class="hash">${esc(data.evaluation.freezeSha256)}</dd></dl><a href="${esc(data.evaluation.freezePath)}" download>Download freeze receipt ↗</a><p class="small-muted">${esc(data.evaluation.limitation)} Inputs use the development generator with a different seed; byte uniqueness does not imply unique behavior.</p></details></div>`:'<p class="note">Directed boundaries and seeded inputs used during development. A separate evaluation tests unchanged candidates on previously unused byte sequences.</p>'}
    <div class="toolbar"><label for="candidate-select">Candidate</label><select id="candidate-select" class="field">${v.reports.map(report=>`<option value="${report.id}" ${report.id===r.id?'selected':''}>${esc(report.title)}</option>`).join('')}</select><select class="field" id="case-filter" aria-label="Filter cases">${[['all','All cases'],['failed','Failures only'],['passed','Passing cases'],...(heldout?[['held-out','Held-out inputs']]:[['boundary','Boundary cases'],['seeded','Seeded cases']])].map(([id,label])=>`<option value="${id}" ${state.filter===id?'selected':''}>${label}</option>`).join('')}</select><input id="case-search" class="field" value="${esc(state.query)}" aria-label="Search cases" placeholder="Search ID, label, or hex bytes…"></div>
    <div class="verification-summary" aria-live="polite"><div><div class="metric-value pass">${fmt(r.passed)}</div><small>Passed</small></div><div><div class="metric-value ${r.failed?'fail':''}">${fmt(r.failed)}</div><small>Failed</small></div><div><div class="metric-value">${fmt(r.total)}</div><small>Executed</small></div><span class="small-muted">${fmt(cases.length)} shown</span></div>
    ${r.intentionalFault?'<div class="callout fault"><strong>Deliberate fault candidate.</strong> Sequence bytes are read in little-endian order. This is an educational mutation, not an unintentional defect in the recovered candidate. Symmetric sequences still pass.</div>':''}
    <div class="grid"><div class="panel"><div class="panel-head"><h3>Execution cases</h3><span class="small-muted">Select a case to inspect →</span></div>${cases.length?`<div class="table-scroll"><table><thead><tr><th scope="col">Case / input</th><th scope="col">Class</th><th scope="col">Result</th></tr></thead><tbody>${visible.map(c=>`<tr class="${chosen?.id===c.id?'selected':''}"><td><button class="case-button" data-case="${c.id}" ${chosen?.id===c.id?'aria-current="true"':''}>${esc(c.id)}</button><div class="small-muted">${esc(c.label)}</div></td><td>${c.group}</td><td class="${c.passed?'pass':'fail'}">${c.passed?'✓ PASS':'× FAIL'}</td></tr>`).join('')}</tbody></table></div>`:'<div class="empty">No cases match this filter. Choose “All cases” or clear the search.</div>'}<div class="panel-footer"><span class="small-muted">Page ${state.page+1} / ${pages} · ${fmt(cases.length)} matches</span><div><button class="btn" data-page="prev" ${state.page===0?'disabled':''} aria-label="Previous page of cases">←</button> <button class="btn" data-page="next" ${state.page>=pages-1?'disabled':''} aria-label="Next page of cases">→</button></div></div></div>
    <div class="panel inspector"><div class="panel-head"><h3>Case inspector</h3>${chosen?tag(chosen.passed?'PASS':'FAIL',chosen.passed?'':'fault'):''}</div><div class="panel-body">${chosen?inspectCase(f,v,r,chosen):'<div class="empty">Select an execution case to see its input and outputs.</div>'}</div></div></div>
    <div class="uncertainty"><strong>Replay locally.</strong> These are recorded results, not a live execution service. ${heldout?'The holdout replay checks the frozen candidate, executable, source, harness and case generator, then regenerates the exact evaluation inputs. Rebuilding changes the artifact identity; create a new freeze and evaluation afterward.':`Regenerate native evidence with <span class="inline-code">python3 -m lab.pipeline generate</span>${v.stripped?' followed by <span class="inline-code">python3 -m lab.stripped</span>':''}, then refresh. The CLI checks the executable and source hashes before rerunning recorded inputs.`}</div>`;
}
function inspectCase(f,v,r,c) {
  const bytes = c.hex.match(/.{2}/g) || [];
  const sequenceHint = f.id==='packet' && bytes.length>=6 && c.expected>=2**31;
  const command = `${r.rerun} --case ${c.id}`;
  return `<h3>${esc(c.label)}</h3><div class="small-muted mono">${c.id} · ${bytes.length} bytes · ${c.group}</div><div class="hex-bytes" aria-label="Input bytes with zero-based offsets">${bytes.length?bytes.map((byte,i)=>`<span class="${sequenceHint && [2,3].includes(i)?'sequence':''}"><small>${i.toString(16).padStart(2,'0')}</small>${byte}</span>`).join(''):'<span>∅</span>'}</div>
    ${sequenceHint?`<div class="small-muted">Sequence bytes at offsets 02–03: <span class="mono">${bytes[2]} ${bytes[3]}</span>.<br>Big endian: ${parseInt(bytes[2]+bytes[3],16)} · Little endian: ${parseInt(bytes[3]+bytes[2],16)}.</div>`:''}
    <div class="value-comparison"><div><small>Compiled reference</small><strong>${hex(c.expected)}</strong><em>${c.expected}</em></div><div><small>Python candidate</small><strong class="${c.passed?'pass':'fail'}">${hex(c.actual)}</strong><em>${c.actual}</em></div></div>
    <p class="small-muted">${c.passed?'Outputs agree for this input.':'Outputs disagree for this input. This is a concrete counterexample to the candidate.'}</p><details><summary>Exact execution identity</summary><dl class="definition-list"><dt>Executable</dt><dd class="mono">${esc(v.artifact)}</dd><dt>SHA-256</dt><dd class="hash">${v.sha256}</dd><dt>Case stream</dt><dd class="hash">${r.caseDigest}</dd><dt>Candidate</dt><dd class="hash">${f.reconstruction.sha256}</dd><dt>Seed</dt><dd class="mono">${r.seed}</dd></dl></details><div class="command">${esc(command)}</div><button class="btn" data-copy="rerun">Copy rerun command</button>`;
}
function buildView(f,v) {
  return `<div class="section-heading"><h2>An artifact with a paper trail.</h2>${tag('NATIVE BUILD')}</div><div class="grid"><div class="panel"><div class="panel-head"><h3>Build identity</h3><button class="text-button" data-copy="build">Copy command</button></div><div class="panel-body"><dl class="definition-list"><dt>Artifact</dt><dd class="mono">${esc(v.artifact)}</dd><dt>Format</dt><dd>${esc(v.evidence.artifact.output.trim()||'Unavailable')}</dd><dt>Platform</dt><dd>${esc(data.platform.system)} ${esc(data.platform.release)} / ${esc(data.platform.architecture)}</dd><dt>Artifact hash</dt><dd class="hash">${v.sha256}</dd><dt>Source hash</dt><dd class="hash">${f.source.sha256}</dd><dt>Harness hash</dt><dd class="hash">${v.harnessSha256}</dd>${v.derivedFrom?`<dt>Symbol twin</dt><dd class="mono">${esc(v.derivedFrom.artifact)}</dd><dt>Twin hash</dt><dd class="hash">${v.derivedFrom.sha256}</dd><dt>Procedure</dt><dd class="mono">${esc(v.derivedFrom.procedureAddress)}–${esc(v.derivedFrom.procedureEnd)}</dd>`:''}<dt>Recording</dt><dd>${esc(data.generatedAt)}</dd><dt>Disassembler</dt><dd class="hash">${esc(v.disassemblerVersion)}</dd></dl><div class="command">${esc(v.command)}</div><p class="small-muted">Run from the project root. ${v.stripped?'Symbols/debug information were stripped; ad-hoc signing is recorded where required.':'Debug symbols are retained.'} Binary hashes can differ with compiler version, SDK, platform, or checkout path.</p></div></div><div><div class="panel"><div class="panel-head"><h3>Compiler identity</h3><span class="small-muted">Exact version output</span></div>${code(data.compiler.version,true,true)}<div class="panel-body"><div class="hash">${esc(data.compiler.path)}</div></div></div><div class="panel" style="margin-top:20px"><div class="panel-head"><h3>Optional providers</h3></div><div class="panel-body">${data.providers.map(p=>`<div class="result-line"><span>${esc(p.name)}</span>${tag(p.status,'neutral')}</div><p class="small-muted">${esc(p.detail)}</p>`).join('')}</div></div></div></div><div class="uncertainty"><strong>Reproducibility scope.</strong> Builds preserve commands and inputs. Results are reproducible on this native host; this release does not claim bit-for-bit builds across environments. Transient executables stay in the ignored build directory.</div>`;
}
function referenceView(f) {
  if (!revealed) return `<div class="panel reference-gate"><div class="symbol" aria-hidden="true">{ }</div><h2>Reveal the ground truth.</h2><p>The reference is self-authored C, known when the candidates were written. Keeping it separate helps you explore evidence before comparing the implementation. This is a viewing preference, not a security boundary.</p><button class="btn primary" id="reveal">Reveal reference source</button></div>`;
  return `<div class="section-heading"><h2>The source behind the experiment.</h2>${tag('GROUND TRUTH / SELF-AUTHORED','neutral')}</div><div class="callout">${esc(f.contract)}</div><div class="panel"><div class="panel-head"><h3>${esc(f.source.path)}</h3><button class="text-button" id="hide-source">Hide reference</button></div>${code(f.source.text)}<div class="panel-footer"><span class="hash">SHA-256 ${f.source.sha256}</span></div></div>`;
}
function bind() {
  document.querySelectorAll('[data-fixture]').forEach(button=>button.addEventListener('click',()=>{
    revealed=false; state.query=''; state.codeQuery=''; state.page=0; change({fixture:button.dataset.fixture,variant:data.fixtures.find(f=>f.id===button.dataset.fixture).variants.some(v=>v.id===state.variant)?state.variant:'O2',candidate:'reconstruct',case:'',filter:'all'}, {focus:`[data-fixture="${button.dataset.fixture}"]`});
  }));
  document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>change({view:button.dataset.view},{focus:`#tab-${button.dataset.view}`})));
  document.querySelectorAll('[data-variant]').forEach(button=>button.addEventListener('click',()=>change({variant:button.dataset.variant},{focus:`[data-variant="${button.dataset.variant}"]`})));
  document.querySelectorAll('[data-evidence]').forEach(button=>button.addEventListener('click',()=>{state.codeQuery='';change({evidence:button.dataset.evidence},{focus:`[data-evidence="${button.dataset.evidence}"]`});}));
  document.querySelector('[data-ghidra]')?.addEventListener('click',()=>change({view:'evidence',evidence:'ghidra'},{focus:'[data-evidence="ghidra"]'}));
  const jump = line => {const pane=document.querySelector('.code');if(!line||!pane)return;pane.scrollTop += line.getBoundingClientRect().top-pane.getBoundingClientRect().top-pane.clientHeight/3;pane.scrollIntoView({block:'center',inline:'nearest'});};
  document.querySelector('#jump-match')?.addEventListener('click',()=>jump(document.querySelector('.code-line.match')));
  document.querySelectorAll('[data-code-jump]').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('.code-line').forEach(line=>line.classList.remove('match'));const line=document.querySelector(`[data-code-line="${button.dataset.codeJump}"]`);line?.classList.add('match');jump(line);}));
  document.querySelectorAll('[data-case]').forEach(button=>button.addEventListener('click',()=>change({case:button.dataset.case},{focus:`[data-case="${button.dataset.case}"]`})));
  document.querySelector('[data-mutant]')?.addEventListener('click',()=>change({view:'verification',corpus:'development',candidate:'faulty_endian',filter:'failed',case:'',page:0},{focus:'#candidate-select'}));
  document.querySelector('#candidate-select')?.addEventListener('change',event=>change({candidate:event.target.value,case:'',page:0},{focus:'#candidate-select'}));
  document.querySelectorAll('[data-corpus]').forEach(button=>button.addEventListener('click',()=>{state.query='';change({corpus:button.dataset.corpus,filter:'all',case:'',page:0},{focus:`[data-corpus="${button.dataset.corpus}"]`});}));
  document.querySelector('#case-filter')?.addEventListener('change',event=>change({filter:event.target.value,case:'',page:0},{focus:'#case-filter'}));
  document.querySelector('#case-search')?.addEventListener('input',event=>{
    state.query=event.target.value;state.case='';state.page=0;const position=event.target.selectionStart;render('#case-search');document.querySelector('#case-search').setSelectionRange(position,position);
  });
  document.querySelector('#code-search')?.addEventListener('input',event=>{
    state.codeQuery=event.target.value;
    let matches=0; document.querySelectorAll('.code-line').forEach(line=>{
      const raw=line.textContent.slice(line.querySelector('.line-number').textContent.length);
      const match=!!state.codeQuery && raw.toLowerCase().includes(state.codeQuery.toLowerCase());
      line.classList.toggle('match',match);if(match)matches++;
    });
    document.querySelector('#code-matches').textContent=state.codeQuery?`${matches} matching lines`:'';
    document.querySelector('#jump-match').disabled=matches===0;
  });
  document.querySelectorAll('[data-page]').forEach(button=>button.addEventListener('click',()=>{state.case='';state.page += button.dataset.page==='next'?1:-1;render(`[data-page="${button.dataset.page}"]`);}));
  document.querySelector('#reveal')?.addEventListener('click',()=>{revealed=true;render('#hide-source');});
  document.querySelector('#hide-source')?.addEventListener('click',()=>{revealed=false;render('#reveal');});
  document.querySelectorAll('[data-copy]').forEach(button=>button.addEventListener('click',async()=>{
    const {fixture:f,variant:v,report:r}=selected();
    const values={evidence:v.evidence[state.evidence]?.output||'',candidate:f.reconstruction.text,build:v.command,rerun:document.querySelector('.inspector .command')?.textContent||r.rerun};
    try{await navigator.clipboard.writeText(values[button.dataset.copy]);button.textContent='Copied';}
    catch{button.textContent='Copy unavailable; select the text';}
  }));
  const tabs=document.querySelectorAll('[role=tab]');
  tabs.forEach((tab,i)=>tab.addEventListener('keydown',event=>{
    if(!['ArrowRight','ArrowLeft','Home','End'].includes(event.key))return;
    event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?views.length-1:(i+(event.key==='ArrowRight'?1:-1)+views.length)%views.length;
    change({view:views[next]},{focus:`#tab-${views[next]}`});
  }));
}
window.addEventListener('popstate',()=>{state.query='';readURL();render();});
window.addEventListener('keydown',event=>{
  if(event.key==='/' && !['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)){
    const input=document.querySelector('#case-search,#code-search');if(input){event.preventDefault();input.focus();}
  }
});
async function load() {
  app.innerHTML='<div class="boot" role="status">Opening evidence recording…</div>';
  try{
    const response=await fetch('data/report.json',{cache:'no-store'});
    if(!response.ok)throw new Error(`Evidence fetch returned HTTP ${response.status}`);
    const recording=await response.json();
    if(recording.schemaVersion!==1 || !Array.isArray(recording.fixtures) || !recording.fixtures.length || !recording.fixtures.every(f=>f.variants?.length && f.variants.every(v=>v.reports?.length && v.reports.every(r=>Array.isArray(r.cases) && r.total>0))))throw new Error('Unsupported or empty evidence recording');
    data=recording;readURL();render();
  }catch(error){
    app.innerHTML=`<div class="boot" role="alert"><p class="eyebrow">Recording unavailable</p><h1>We couldn’t open the evidence.</h1><p>${esc(error.message)}</p><p>Start the local server from the project root. If the recording is missing, run <span class="inline-code">python3 -m lab.pipeline generate</span>.</p><button class="btn primary" id="retry">Retry loading</button></div>`;
    document.querySelector('#retry').addEventListener('click',load);
  }
}
load();
