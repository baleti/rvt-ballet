// Revit directions point toward the eye; world axes map [x, y, z] to [x, z, -y].
export function drawsGridsAsVertical(view) {
  return !!view && view.kind !== '3d' && view.kind !== 'Plan' && !!view.dir;
}

export function elevGridLines(grids, view, levelElevs, modelMinY) {
  if (!grids || grids.length === 0 || !drawsGridsAsVertical(view)) return [];

  const viewLength = Math.hypot(view.dir[0], view.dir[1]);
  // A zero horizontal direction stays zero, matching the reference normalization.
  const dx = view.dir[0] / (viewLength || 1);
  const dz = -view.dir[1] / (viewLength || 1);
  const origin = view.origin || view.cut.origin;
  const ox = origin[0], oz = -origin[1];
  const y0 = Math.min(modelMinY, ...levelElevs);
  const top = Math.max(...levelElevs, modelMinY);
  const y1 = top + (top - y0) * 0.12 + 1;
  const lines = [];

  for (const grid of grids) {
    const a = grid.pts[0], b = grid.pts[1];
    const ax = a[0], az = -a[1];
    const gx = b[0] - ax, gz = -b[1] - az;
    const length = Math.hypot(gx, gz);
    if (length < 1e-6 || Math.abs((gx / length) * dx + (gz / length) * dz) < 0.95) continue;

    // Move along the view direction to 0.3 m behind the cut plane.
    const offset = (ox - ax) * dx + (oz - az) * dz - 0.3;
    lines.push({ name: grid.name, x: ax + dx * offset, z: az + dz * offset, y0, y1 });
  }

  return lines;
}
