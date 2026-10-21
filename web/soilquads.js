// Extend each retained segment to y0 as two independent triangles.
export function soilQuads(seg, y0) {
  const out = [];
  for (let i = 0; i + 5 < seg.length; i += 6) {
    const ax = seg[i], ay = seg[i + 1], az = seg[i + 2];
    const bx = seg[i + 3], by = seg[i + 4], bz = seg[i + 5];
    if (!Number.isFinite(ax) || !Number.isFinite(ay) ||
        !Number.isFinite(az) || !Number.isFinite(bx) ||
        !Number.isFinite(by) || !Number.isFinite(bz)) continue;
    if (ay <= y0 && by <= y0) continue;

    out.push(
      ax, ay, az, bx, by, bz, bx, y0, bz,
      ax, ay, az, bx, y0, bz, ax, y0, az,
    );
  }
  return new Float32Array(out);
}
