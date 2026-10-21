// Frame full screen-space rectangle extents with a small margin.
export function fitDistance(w, h, aspect, fovDeg) {
  return Math.max(w / aspect, h) / 2 /
    Math.tan(fovDeg * Math.PI / 360) * 1.08 + 1;
}

export function boxFrame(min, max, dir, planeOrigin, aspect, fovDeg) {
  const c = min.map((value, axis) => (value + max[axis]) / 2);
  const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
  const offset = dot(dir, planeOrigin) - dot(dir, c);
  const target = c.map((value, axis) => value + dir[axis] * offset);

  // cross([0, 1, 0], dir), normalized.
  const rightLength = Math.hypot(dir[2], dir[0]);
  const right = [dir[2] / rightLength, 0, -dir[0] / rightLength];
  let hw = 1;
  let hh = 1;
  for (const x of [min[0], max[0]]) {
    for (const y of [min[1], max[1]]) {
      for (const z of [min[2], max[2]]) {
        hw = Math.max(hw, Math.abs(dot([x - c[0], y - c[1], z - c[2]], right)));
        hh = Math.max(hh, Math.abs(y - c[1]));
      }
    }
  }

  const dist = Math.max(hw / aspect, hh) /
    Math.tan(fovDeg * Math.PI / 360) * 1.08 + 1;
  const eye = target.map((value, axis) => value + dir[axis] * dist);
  return { target, dist, eye };
}
