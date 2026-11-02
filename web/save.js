// SAVE AS / SAVE / SAVE! front end. Pure helpers (describeResult, describeError) are unit-tested under node; DOM part only runs in a browser.
export function describeResult(j) {
  const lines = [`${j.ok ? 'Saved' : 'Not saved'}: ${j.dest}`, `${j.size} bytes, sha256 ${j.sha256}..., Revit ${j.version}`];
  lines.push(j.backup ? `backup of the previous file: ${j.backup}` : 'no previous file at the destination, no backup needed');
  const r = j.verify || {};
  lines.push(`verify: passed, ${r.objects_src ?? '?'} source objects / ${r.objects_out ?? '?'} output objects, ${r.n_unexpected || 0} undeclared differences, structure ${r.validate || 'ok'}`);
  (j.warnings || []).forEach(w => lines.push('WARNING: ' + w));
  return lines;
}
export function describeError(j, status) {
  const code = (j && j.code) || 'error';
  const head = { workshared: 'Overwrite refused: this is a workshared (central or local) model. Use SAVE AS and check the copy in Revit.', group_or_option: 'Overwrite refused: the edit touches a group or design-option element. Use SAVE AS and check the copy in Revit.', conflict: 'The file changed on disk since it was loaded.', gate_closed: 'Overwrite is not enabled for this Revit version (oracle test matrix not green). Use SAVE AS.',
    overwrite_disabled: 'Overwrite is disabled in the configuration. Use SAVE AS.', exists: 'The destination already exists.', read_only: 'Overwrite refused: the file is read-only. Clear the read-only flag or use SAVE AS.', locked: 'The file is being saved by another process. Try again in a moment; nothing was written.', too_big: 'This model is too large to verify on this machine. Nothing was written.', cloud_placeholder: 'The file is an online-only cloud placeholder: make it available offline first. Nothing was written.', bad_dest: 'The destination path is not usable.', layout_changed: 'Overwrite refused: this edit changes the file layout in a way that is not confirmed to open in Revit. Use SAVE AS and check the copy.',  output_unreadable: 'The edited file could not be read back, so it was not saved. The original is untouched.', 
    verify_failed: 'Verification failed: the output differs from the source outside the declared edit. Nothing was written; the original is untouched.',
    unsupported_version: 'This Revit version cannot be saved.', disk_error: 'Disk error: nothing was written.', unavailable: 'Saving is not available (savegate missing).', no_source: 'The source file of this model is not available.' }[code] || `Save failed (HTTP ${status}).`;
  const lines = [head];
  if (j && j.error && !head.includes(j.error)) lines.push(j.error);
  const na = j && j.report && (j.report.unexpected || []).filter(x => x[0] === 'not_applied'); if (na && na.length) lines.push(`An edit had no effect on ${na.length} element(s) (${na.slice(0, 3).map(x => x[1]).join(', ')}): the file would NOT have been changed as you asked, so nothing was saved.`);
  const d = j && j.report && j.report.unexpected; if (Array.isArray(d) && d.length) lines.push(`${j.report.n_unexpected} differences, first: ` + d.slice(0, 5).map(x => x.join(' ')).join('; '));
  const cd = j && j.changed_detail; if (Array.isArray(cd) && cd.length) lines.push('changed outside the declared edit: ' + cd.slice(0, 6).map(x => `${x.cls || '?'} ${x.id}${x.name ? ' "' + x.name + '"' : ''}`).join(', '));
  const ed = j && j.edits; if (Array.isArray(ed) && ed.length) lines.push('pending edits: ' + ed.map(o => `${o.field} of element ${o.eid}`).join('; '));
  return lines;
}
export function describeBackup(b) { return `#${b.n}  ${b.mtime}  ${b.size} bytes  ${b.name}`; }
export const NOT_EDITABLE = /^(UniqueId|IfcGUID|Type IfcGUID|Family|Type Id|Type|Family and Type|Name|Category\|ElementId|Design Option\|String)$/;
export function paramEditable(name, value) { return typeof value === 'string' && !NOT_EDITABLE.test(name); }
export function actions(info) {   // which buttons are enabled and why not
  const a = { overrides: (info && info.safety_overrides) || [], saveas: { on: !!(info && info.open), why: info && info.open ? '' : (info && info.error) || 'saving unavailable for this model' } };
  a.save = { on: !!(info && info.open && info.allow_overwrite && info.gate_open), why: '' };
  if (a.save.on && info.workshared) { a.save.on = false; a.save.why = 'workshared model: overwrite is refused, use Save as'; return a; }
  if (!a.save.on) a.save.why = !info || !info.open ? a.saveas.why : !info.allow_overwrite ? 'overwrite disabled in the configuration' : 'overwrite gate closed for this version';
  return a;
}

export const LIMITED_WARNING = 'Limited verification: the copy is checked for structure only (all untouched parts identical, only a few blocks of the edited part changed). It is NOT checked element by element, so it cannot prove that only your edit changed, and Revit has not been asked to open it. Open the copy in Revit before relying on it. Continue?';
export function initSave($, getMid) {
  const top = document.getElementById('top'); const sp = top.querySelector('.sp');
  const mk = (id, txt) => { const b = document.createElement('button'); b.id = id; b.textContent = txt; b.disabled = true; top.insertBefore(b, sp.nextSibling); return b; };
  const bUndo = mk('bUndoEdit', 'Undo edit'); bUndo.disabled = false; bUndo.hidden = true; bUndo.title = 'Remove the last pending edit (nothing is written until you Save or Save as)';
  let canNameEdit = false, pendingEdits = 0;
  window.addEventListener('beforeunload', (ev) => { if (pendingEdits > 0) { ev.preventDefault(); ev.returnValue = ''; } });      // edits live in the server's memory until Save: closing the window may end the server and drop them
  const bBk = mk('bBackups', 'Backups'), bOver = mk('bSaveOver', 'Save'), bAs = mk('bSaveAs', 'Save as');
  const panel = document.createElement('div'); panel.id = 'savepanel'; panel.hidden = true; document.body.appendChild(panel);
  const show = (lines, bad, extra) => { panel.replaceChildren(); panel.className = bad ? 'bad' : 'ok'; lines.forEach(l => { const d = document.createElement('div'); d.textContent = l; panel.appendChild(d); }); if (extra) panel.appendChild(extra); const x = document.createElement('button'); x.textContent = 'close'; x.onclick = () => { panel.hidden = true; }; panel.appendChild(x); panel.hidden = false; };
  const post = async (path, body) => { const r = await fetch(`/api/m/${getMid()}/${path}`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) }); let j = null; try { j = await r.json(); } catch (e) {} return [r, j]; };
  async function refresh() {
    const mid = getMid(); if (!mid) return; let info = null; try { info = await (await fetch(`/api/m/${mid}/saveinfo`)).json(); } catch (e) {}
    if (mid !== getMid()) return;      // the user switched models while saveinfo ran: do not set the buttons from the old model
    canNameEdit = !!(info && info.open && info.name_edit); const pe = (info && info.pending_edits) || 0; bUndo.hidden = !pe; bUndo.textContent = `Undo edit (${pe} pending)`; pendingEdits = pe;
    const a = actions(info); bBk.disabled = !a.saveas.on; bAs.disabled = !a.saveas.on; bAs.title = a.saveas.on ? 'Save a copy under a new name (never touches the original)' : a.saveas.why;
    bOver.disabled = !a.save.on; bOver.title = a.save.on ? 'Overwrite the source file (a backup is kept)' + (a.overrides.length ? ' - WARNING: safety checks switched off by the server environment: ' + a.overrides.join(', ') : '') : a.save.why;
  }
  async function doSave(path, body, force) {
    let live = true; const poll = async () => { while (live) { try { const p = await (await fetch(`/api/m/${getMid()}/saveprogress`)).json(); if (live && p.busy && p.stage) show([`Saving... ${p.stage} (${p.elapsed} s)`], false); } catch (e) {} await new Promise(r => setTimeout(r, 700)); } };
    poll(); let r, j; try { [r, j] = await post(path, body); } catch (e) { live = false; show(['The save request did not complete (' + e + ').', 'Do not assume the file was written: check the file and the Backups list before retrying.'], true); return; } finally { live = false; }
    if (r.ok && j && j.ok) { show(describeResult(j), false); refresh(); return; }      // refresh: SAVE clears the server's pending edits, SAVE AS keeps them
    if (j && j.code === 'conflict' && !force) {
      const b = document.createElement('button'); b.textContent = 'Overwrite anyway'; b.onclick = () => { if (confirm('Overwrite the changed file with the loaded version? A backup is kept.')) doSave(path, { ...body, force: true, confirm: true }, true); };
      const rl = document.createElement('button'); rl.textContent = 'Reload'; rl.onclick = () => location.reload(); const w = document.createElement('span'); w.append(b, rl);
      show(describeError(j, r.status), true, w); return;
    }
    if (j && j.code === 'too_big' && path === 'saveas' && body.dest) {      // too large for the element-level verify: offer the clearly labelled weaker option, never silently
      const b = document.createElement('button'); b.textContent = 'Save with limited verification';
      b.title = 'Structure-only check: untouched streams identical, only the edited part changed. It cannot prove that only the declared element changed.';
      b.onclick = () => { if (confirm(LIMITED_WARNING)) doSave('saveas', { ...body, light_verify: true, confirm: true }, true); };
      const w = document.createElement('span'); w.append(b); show(describeError(j, r.status), true, w); return;
    }
    show(describeError(j, r.status), true);
  }
  bBk.onclick = async () => {
    const bl = await (await fetch(`/api/m/${getMid()}/backups`)).json(); const box = document.createElement('div');
    if (!bl.length) { show(['No backups exist for this file yet (one is made before every overwrite).'], false); return; }
    bl.forEach(b => { const r = document.createElement('div'); r.textContent = describeBackup(b) + ' '; const x = document.createElement('button'); x.textContent = 'Restore';
      x.onclick = async () => { if (!confirm(`Restore backup #${b.n} over the current file? The current file is backed up first.`)) return;
        const [rr, j] = await post('restore', { n: b.n, confirm: true }); show(rr.ok && j && j.ok ? [`Restored backup #${b.n}: ${j.size} bytes, sha256 ${j.sha256}...`, 'Reload the page to see the restored content.'] : describeError(j, rr.status), !(rr.ok && j && j.ok)); refresh(); };
      r.appendChild(x); box.appendChild(r); });
    show(['Backups (newest first):'], false, box);
  };
  bAs.onclick = async () => { const dest = prompt('Save as (full path of the new .rvt):'); if (dest) doSave('saveas', { dest }); };
  bOver.onclick = () => { if (confirm('Overwrite the source file? A backup of the original is kept.')) doSave('save', {}); };
  bUndo.onclick = async () => { const r = await fetch(`/api/m/${getMid()}/edit/undo`, { method: 'POST' }); const j = await r.json().catch(() => null); show(r.ok ? [`Removed the last pending edit (${j.n} pending).`] : describeError(j, r.status), !r.ok); refresh(); };
  // pencil on editable string parameter rows of the inspector; the server resolves the NAME to the one parameter stored on the element and refuses anything else
  function decorate(eid, table) {
    if (!canNameEdit || !table) return;
    table.querySelectorAll('tr').forEach(tr => {
      const tds = tr.querySelectorAll('td'); if (tds.length < 2) return; const name = tds[0].textContent, cur = tds[1].textContent;
      if (tr.dataset.t !== 'string' || !paramEditable(name, cur)) return;      // only values that are STRINGS in the file (numbers are shown as text too, and their displayed units must not be edited as text)
      const b = document.createElement('button'); b.textContent = '\u270e'; b.title = `Edit ${name} (recorded as a pending edit; nothing is written until Save / Save as)`; b.className = 'pedit'; b.style.marginLeft = '6px';
      b.onclick = async () => { const v = prompt(`New value for "${name}" of element ${eid}:`, cur); if (v === null) return;
        const [r, j] = await post('edit', { op: 'set_string', eid, param: name, value: v });
        if (r.ok && j && j.ok) { show([`Pending edit recorded: ${name} of element ${eid} = ${JSON.stringify(v)} (${j.n} pending). Use Save as / Save to write it.`], false); } else show(describeError(j, r.status), true); refresh(); };
      tds[1].appendChild(b);
    });
    // placement / removal ops of the whole element: the server validates and refuses (with the reason) whatever the backend / policy does not allow
    if (table.parentNode && !table.parentNode.querySelector('.opbar')) {
      const bar = document.createElement('div'); bar.className = 'opbar'; bar.style.margin = '6px 0';
      const rec = async (body, what) => { const [r, j] = await post('edit', body); if (r.ok && j && j.ok) show([`Pending edit recorded: ${what} of element ${eid} (${j.n} pending). Use Save as / Save to write it.`], false); else show(describeError(j, r.status), true); refresh(); };
      const mk2 = (label, title, fn) => { const x = document.createElement('button'); x.textContent = label; x.title = title; x.style.marginRight = '6px'; x.onclick = fn; bar.appendChild(x); };
      mk2('Move\u2026', 'Move this element by dx, dy, dz in feet (recorded as a pending edit)', async () => {
        const t = prompt(`Move element ${eid} by dx, dy, dz (feet), e.g. 1, 0, 0:`, '1, 0, 0'); if (t === null) return;
        const v = t.split(',').map(x => Number(x.trim())); if (v.length < 1 || v.length > 3 || v.some(x => !Number.isFinite(x))) { show(['Enter up to three numbers separated by commas.'], true); return; }
        rec({ op: 'move', eid, dx: v[0] || 0, dy: v[1] || 0, dz: v[2] || 0 }, `move by ${v.join(', ')} ft`); });
      mk2('Rotate\u2026', 'Rotate this element about its origin by an angle in degrees (recorded as a pending edit)', async () => {
        const t = prompt(`Rotate element ${eid} by (degrees):`, '30'); if (t === null) return; const d = Number(t.trim());
        if (!Number.isFinite(d)) { show(['Enter a number of degrees.'], true); return; }
        rec({ op: 'rotate', eid, deg: d }, `rotate by ${d} degrees`); });
      mk2('Delete\u2026', 'Delete this element (off by default; the server says why when it refuses)', async () => {
        if (!confirm(`Delete element ${eid}? This is recorded as a pending edit and written only on Save / Save as.`)) return; rec({ op: 'delete', eid }, 'delete'); });
      table.parentNode.insertBefore(bar, table.nextSibling);
    }
  }
  return { refresh, decorate };
}
