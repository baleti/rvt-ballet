export function catKey(c) {
  return String(c);
}

export function typeKey(e) {
  if (!e || !e.typeName) return null;
  return (e.familyName ? e.familyName + ' : ' : '') + e.typeName;
}

export function primVisible(state, elements, m) {
  if (state.layers?.[m.layer] === false) return false;
  if (m.cat != null && state.cats?.[catKey(m.cat)]?.vis === false) return false;

  const e = elements[m.eid];
  if (e && e.parent != null && state.cats?.[catKey(e.parent)]?.vis === false) return false;
  if (m.eid != null && state.elems?.[m.eid]?.vis === false) return false;
  if (m.cls && state.classes?.[m.cls] === false) return false;
  if (m.part && state.parts?.[m.part] === false) return false;
  if (m.hang && state.hideHang) return false;
  if (e && e.typeName && state.types?.[typeKey(e)] === false) return false;
  if (m.t === 'text' && !state.textOn) return false;
  return true;
}

export function enrichTypes(elements, rows, indexOf) {
  if (rows === undefined) return elements;

  for (const [eid, e] of Object.entries(elements)) {
    if (e.typeName) continue;
    const i = indexOf(eid);
    const r = i != null ? rows[i] : null;
    if (r && r[4]) {
      e.typeName = r[4];
      if (r[8] && !e.familyName) e.familyName = r[8];
      if (r[5] && !e.levelName) e.levelName = r[5];
    }
  }
  return elements;
}
