// Crop corners and the unit view direction use a y-up world.
export function cropExtent(pts, axis) {
  const c = [0, 1, 2].map(i =>
    (pts[0][i] + pts[1][i] + pts[2][i] + pts[3][i]) / 4
  );
  const dx = pts[1][0] - pts[0][0];
  const dy = pts[1][1] - pts[0][1];
  const dz = pts[1][2] - pts[0][2];
  const e1 = Math.hypot(dx, dy, dz);
  const e2 = Math.hypot(
    pts[2][0] - pts[1][0],
    pts[2][1] - pts[1][1],
    pts[2][2] - pts[1][2]
  );
  const horiz1 = Math.abs(axis[1]) > 0.9
    ? Math.abs(dx) >= Math.abs(dz)
    : Math.abs(dy) < 0.5 * e1;
  return { c, w: horiz1 ? e1 : e2, h: horiz1 ? e2 : e1 };
}
