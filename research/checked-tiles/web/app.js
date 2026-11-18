'use strict';
const el = (id) => document.getElementById(id);
const labels = {
  cpu_1: 'CPU · 1 thread',
  cpu_4: 'CPU · 4 threads',
  cpu_lookup: 'CPU · byte lookup',
  gpu_whole_call: 'OpenCL · whole call',
};
let state,
  tag,
  sending = false,
  online = false;
function text(id, value) {
  el(id).textContent = value;
}
function duration(ms) {
  if (ms >= 1000) return (ms / 1000).toFixed(2) + ' s';
  return ms < 1 ? (ms * 1000).toFixed(1) + ' µs' : ms.toFixed(2) + ' ms';
}
function connection() {
  const busy = state?.job.status === 'checking';
  el('connection').dataset.state = online ? (busy ? 'checking' : 'ready') : 'offline';
  text(
    'connection',
    online ? (busy ? 'Workstation checking' : 'Workstation ready') : 'Workstation offline',
  );
  for (const id of ['check', 'rehearse', 'run-actors']) el(id).disabled = !online || busy || sending;
}
function verdict(title, message, status) {
  text('verdict', title);
  text('message', message);
  el('feedback').dataset.status = status;
}
function showRun(job) {
  const completed = job.finished
    ? ' Run time ' + duration((job.finished - job.started) * 1000) + '.'
    : '';
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - job.started));
  if (job.mode === 'actors') {
    let message;
    if (job.status === 'checking') {
      message = 'Building and running on the workstation · ' + seconds + ' s';
    } else if (job.status === 'exercised') {
      const result = job.actors;
      const choice = (policy) => result.revision.find((r) => r.arm === 'queue' && r.policy === policy);
      const mixed = result.compiler.find((r) => r.policy === 'latest');
      message = 'Pinned A consumed ' + choice('pinned').selected + '. Looking up B at wake consumed '
        + choice('latest').selected + '. The mixed compiler emitted ' + mixed.pending_output
        + ' and evaluation failed.';
      text('actor-data', JSON.stringify(result, null, 2));
      el('actor-detail').hidden = false;
    } else {
      message = job.error || 'Native run ended.';
    }
    text('actor-result', message);
    verdict(job.status === 'exercised' ? 'Native experiment passed' : 'Native actor lab', message, job.status);
    el('job-detail').hidden = true;
    return;
  }
  switch (job.status) {
    case 'ready':
      verdict('Ready to check', 'Choose a starting point or edit the BL function.', 'ready');
      break;
    case 'checking':
      verdict(
        job.mode === 'edit' ? 'Checking candidate' : 'Running live-edit rehearsal',
        'Elapsed ' + seconds + ' s · The accepted frame stays on screen.',
        'checking',
      );
      break;
    case 'rejected':
      verdict(
        'Candidate rejected',
        'Lean checked the counterexample. Input ' +
          job.witness.input +
          ' produced ' +
          job.witness.output +
          '. The accepted revision is still serving.' +
          completed,
        'rejected',
      );
      break;
    case 'accepted':
      verdict(
        job.exercise ? 'Rehearsal passed' : 'Candidate accepted',
        (job.exercise
          ? 'The stale frame was discarded, the old ELF was released, and the broken edit was rejected. Posterize is serving.'
          : 'Lean checked all 256 inputs. The published frame matches the compiled BEAM reference.') +
          completed,
        'accepted',
      );
      break;
    case 'failed':
      verdict('Run failed', job.error, 'failed');
      break;
  }
  const details = job.exercise || (job.witness && { witness: job.witness, lean: job.proof });
  el('job-detail').hidden = !details;
  text(
    'job-data',
    details
      ? job.witness
        ? JSON.stringify(job.witness, null, 2) + '\n\n' + job.proof
        : JSON.stringify(details, null, 2)
      : '',
  );
}
function display(next) {
  const a = next.accepted,
    r = a.receipt;
  if (!state) {
    el('source').value = localStorage.getItem('checked-tiles-draft') ?? next.presets.wash;
    el('preset').value =
      Object.keys(next.presets).find((k) => next.presets[k] === el('source').value) || 'custom';
  }
  el('input').src = a.original;
  el('output').src = a.frame;
  text('frame-label', a.origin + ' · accepted');
  text('dims', r.width + ' × ' + r.height + ' RGB');
  text('rev', r.revision.slice(0, 12));
  text('backend', labels[r.backend] || r.backend);
  text('lean-time', duration(r.lean_process_ms));
  text('beam-time', duration(r.beam_frame_ms));
  text('accepted-source', a.source);
  text('proof', a.proof);
  text('axioms', a.lean);
  text('receipt', JSON.stringify(r, null, 2));
  text(
    'device',
    r.gpu ? r.gpu.device + ' · driver ' + r.gpu.driver : r.gpu_unavailable || 'CPU execution',
  );
  const body = el('timings');
  body.replaceChildren();
  for (const [name, timing] of Object.entries(r.timings)) {
    const row = body.insertRow();
    row.insertCell().textContent = labels[name] || name;
    row.insertCell().textContent = duration(timing.median_ms);
  }
  const preparation = el('preparation');
  preparation.replaceChildren();
  for (const [key, label] of Object.entries({
    beam_capture_process_ms: 'BEAM capture process',
    lean_process_ms: 'Lean process',
    cpu_compile_ms: 'Native compilation',
    gpu_setup_ms: 'OpenCL setup',
  })) {
    if (r[key] === undefined) continue;
    const row = preparation.insertRow();
    row.insertCell().textContent = label;
    row.insertCell().textContent = duration(r[key]);
  }
  state = next;
  showRun(state.job);
}
async function refresh() {
  try {
    const response = await fetch('/api/state', { headers: tag ? { 'If-None-Match': tag } : {} });
    if (response.status === 304) {
      if (state.job.status === 'checking') showRun(state.job);
    } else {
      if (!response.ok) throw Error('HTTP ' + response.status);
      display(await response.json());
      tag = response.headers.get('ETag');
    }
    online = true;
  } catch {
    online = false;
  }
  connection();
}
async function submit(mode) {
  if (sending || !state) return;
  sending = true;
  connection();
  try {
    const response = await fetch('/api/runs', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Checked-Tiles': '1' },
      body: JSON.stringify({
        base: state.accepted.receipt.revision,
        source: el('source').value,
        placement: el('placement').value,
        mode,
      }),
    });
    const result = await response.json();
    if (!response.ok) throw Error(result.error || 'HTTP ' + response.status);
    state.job = result;
    showRun(result);
  } catch (error) {
    verdict('Request could not start', error.message, 'failed');
  } finally {
    sending = false;
    connection();
  }
}
el('preset').onchange = () => {
  el('source').value = state.presets[el('preset').value];
  localStorage.setItem('checked-tiles-draft', el('source').value);
};
el('source').oninput = () => {
  el('preset').value = 'custom';
  localStorage.setItem('checked-tiles-draft', el('source').value);
};
el('wipe').oninput = () => el('screen').style.setProperty('--wipe', el('wipe').value + '%');
el('check').onclick = () => submit('edit');
el('run-actors').onclick = () => submit('actors');
el('rehearse').onclick = () => submit('rehearsal');
(async function poll() {
  await refresh();
  setTimeout(poll, 1200);
})();
