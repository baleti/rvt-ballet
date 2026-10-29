// SAVE AS / SAVE / SAVE! front end. Pure helpers (describeResult, describeError) are unit-tested under node; DOM part only runs in a browser.
export function describeResult(j) {
  const lines = [`${j.ok ? 'Saved' : 'Not saved'}: ${j.dest}`, `${j.size} bytes, sha256 ${j.sha256}..., Revit ${j.version}`];
  lines.push(j.backup ? `backup of the previous file: ${j.backup}` : 'no previous file at the destination, no backup needed');
  const r = j.verify || {};
  lines.push(`verify: passed, ${r.objects_src ?? '?'} source objects / ${r.objects_out ?? '?'} output objects, ${r.n_unexpected || 0} undeclared differences, structure ${r.validate || 'ok'}`);
  return lines;
}
export function describeError(j, status) {
  const code = (j && j.code) || 'error';
  const head = { conflict: 'The file changed on disk since it was loaded.', gate_closed: 'Overwrite is not enabled for this Revit version (oracle test matrix not green). Use SAVE AS.',
    overwrite_disabled: 'Overwrite is disabled in the configuration. Use SAVE AS.', exists: 'The destination already exists.', bad_dest: 'The destination path is not usable.', locked: 'Another process is saving this file.',
    verify_failed: 'Verification failed: the output differs from the source outside the declared edit. Nothing was written; the original is untouched.',
    unsupported_version: 'This Revit version cannot be saved.', disk_error: 'Disk error: nothing was written.', unavailable: 'Saving is not available (savegate missing).', no_source: 'The source file of this model is not available.' }[code] || `Save failed (HTTP ${status}).`;
  const lines = [head];
  if (j && j.error && !head.includes(j.error)) lines.push(j.error);
  const d = j && j.report && j.report.unexpected; if (Array.isArray(d) && d.length) lines.push(`${j.report.n_unexpected} differences, first: ` + d.slice(0, 5).map(x => x.join(' ')).join('; '));
  return lines;
}
export function actions(info) {   // which buttons are enabled and why not
  const a = { saveas: { on: !!(info && info.open), why: info && info.open ? '' : (info && info.error) || 'saving unavailable for this model' } };
  a.save = { on: !!(info && info.open && info.allow_overwrite && info.gate_open), why: '' };
  if (!a.save.on) a.save.why = !info || !info.open ? a.saveas.why : !info.allow_overwrite ? 'overwrite disabled in the configuration' : 'overwrite gate closed for this version';
  return a;
}

export function initSave($, getMid) {
  const top = document.getElementById('top'); const sp = top.querySelector('.sp');
  const mk = (id, txt) => { const b = document.createElement('button'); b.id = id; b.textContent = txt; b.disabled = true; top.insertBefore(b, sp.nextSibling); return b; };
  const bOver = mk('bSaveOver', 'Save'), bAs = mk('bSaveAs', 'Save as');
  const panel = document.createElement('div'); panel.id = 'savepanel'; panel.hidden = true; document.body.appendChild(panel);
  const show = (lines, bad, extra) => { panel.replaceChildren(); panel.className = bad ? 'bad' : 'ok'; lines.forEach(l => { const d = document.createElement('div'); d.textContent = l; panel.appendChild(d); }); if (extra) panel.appendChild(extra); const x = document.createElement('button'); x.textContent = 'close'; x.onclick = () => { panel.hidden = true; }; panel.appendChild(x); panel.hidden = false; };
  const post = async (path, body) => { const r = await fetch(`/api/m/${getMid()}/${path}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }); let j = null; try { j = await r.json(); } catch (e) {} return [r, j]; };
  async function refresh() {
    const mid = getMid(); if (!mid) return; let info = null; try { info = await (await fetch(`/api/m/${mid}/saveinfo`)).json(); } catch (e) {}
    const a = actions(info); bAs.disabled = !a.saveas.on; bAs.title = a.saveas.on ? 'Save a copy under a new name (never touches the original)' : a.saveas.why;
    bOver.disabled = !a.save.on; bOver.title = a.save.on ? 'Overwrite the source file (a backup is kept)' : a.save.why;
  }
  async function doSave(path, body, force) {
    const [r, j] = await post(path, body);
    if (r.ok && j && j.ok) { show(describeResult(j), false); return; }
    if (j && j.code === 'conflict' && !force) {
      const b = document.createElement('button'); b.textContent = 'Overwrite anyway'; b.onclick = () => { if (confirm('Overwrite the changed file with the loaded version? A backup is kept.')) doSave(path, { ...body, force: true, confirm: true }, true); };
      const rl = document.createElement('button'); rl.textContent = 'Reload'; rl.onclick = () => location.reload(); const w = document.createElement('span'); w.append(b, rl);
      show(describeError(j, r.status), true, w); return;
    }
    show(describeError(j, r.status), true);
  }
  bAs.onclick = async () => { const dest = prompt('Save as (full path of the new .rvt):'); if (dest) doSave('saveas', { dest }); };
  bOver.onclick = () => { if (confirm('Overwrite the source file? A backup of the original is kept.')) doSave('save', {}); };
  return { refresh };
}
