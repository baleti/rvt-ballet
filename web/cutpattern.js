const F = 0.3048;

// Group drafting patterns by their complete, unscaled grid definitions.
export function buildCutGroups(mats) {
  const groups = [];
  const matGroup = new Float32Array(Math.max(1, mats.length));
  const indices = new Map();

  for (let i = 0; i < mats.length; i++) {
    const pattern = mats[i].cut_pattern;
    if (!pattern || pattern.target !== 0 || !pattern.grids || pattern.grids.length === 0) continue;

    const key = JSON.stringify(pattern.grids);
    if (!indices.has(key)) {
      const grids = pattern.grids.slice(0, 2).map(grid => {
        const sp = Math.abs(grid.deltas[1]) * F;
        const segs = (grid.segs || []).map(Math.abs);
        const dash = segs.length >= 2 ? segs[0] * F : 0;
        const gap = segs.length >= 2 ? segs[1] * F : 0;
        return {
          a: [grid.angle, sp, grid.deltas[0] * F, sp > 1e-6 ? 1 : 0],
          b: [dash, gap, grid.origin[0] * F, grid.origin[1] * F],
        };
      });
      groups.push({ name: pattern.name, grids });
      indices.set(key, groups.length);
    }
    matGroup[i] = indices.get(key);
  }

  return { groups, matGroup };
}

export function scaleGrid(q, N) {
  return {
    a: [q.a[0], q.a[1] * N, q.a[2] * N, q.a[3]],
    b: [q.b[0] * N, q.b[1] * N, q.b[2] * N, q.b[3] * N],
  };
}

export function viewScaleN(view) {
  return view && view.scale > 0 ? Math.min(500, Math.max(1, 1 / view.scale)) : 50;
}
