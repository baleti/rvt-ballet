// Clip against the nonnegative half-space of each plane.
export function clipSegment(p, q, planes) {
  let t0 = 0;
  let t1 = 1;
  for (let i = 0; i < planes.length; i++) {
    const { nx, ny, nz, c } = planes[i];
    const d0 = nx * p[0] + ny * p[1] + nz * p[2] + c;
    const d1 = nx * q[0] + ny * q[1] + nz * q[2] + c;
    if (d0 < 0 && d1 < 0) return null;
    if (d0 < 0) t0 = Math.max(t0, d0 / (d0 - d1));
    else if (d1 < 0) t1 = Math.min(t1, d0 / (d0 - d1));
    if (t0 >= t1) return null;
  }
  const dx = q[0] - p[0];
  const dy = q[1] - p[1];
  const dz = q[2] - p[2];
  return [
    p[0] + dx * t0, p[1] + dy * t0, p[2] + dz * t0,
    p[0] + dx * t1, p[1] + dy * t1, p[2] + dz * t1,
  ];
}

// Return independent triangle/plane intersections in mesh and triangle order.
export function cutSegments(meshes, plane, others = []) {
  const out = [];
  const { nx, ny, nz, c } = plane;
  const vertices = [0, 0, 0];
  const p = [0, 0, 0];
  const q = [0, 0, 0];

  for (let meshIndex = 0; meshIndex < meshes.length; meshIndex++) {
    const { pos, index, matrix: m, accept } = meshes[meshIndex];
    const count = pos.length / 3;
    // Cache shared vertices once. Keep double precision until output conversion
    // so rounding cannot change which side of the plane a vertex occupies.
    const world = m ? new Float64Array(pos.length) : pos;
    const distances = new Float64Array(count);
    for (let i = 0; i < count; i++) {
      const offset = 3 * i;
      let x = pos[offset], y = pos[offset + 1], z = pos[offset + 2];
      if (m) {
        // Match Vector3.applyMatrix4, including homogeneous division.
        const w = 1 / (m[3] * x + m[7] * y + m[11] * z + m[15]);
        const wx = (m[0] * x + m[4] * y + m[8] * z + m[12]) * w;
        const wy = (m[1] * x + m[5] * y + m[9] * z + m[13]) * w;
        const wz = (m[2] * x + m[6] * y + m[10] * z + m[14]) * w;
        x = world[offset] = wx;
        y = world[offset + 1] = wy;
        z = world[offset + 2] = wz;
      }
      distances[i] = nx * x + ny * y + nz * z + c;
    }

    const triangleCount = (index ? index.length : count) / 3;
    for (let t = 0; t < triangleCount; t++) {
      const start = 3 * t;
      const a = index ? index[start] : start;
      if (accept && !accept(t, a)) continue;
      const b = index ? index[start + 1] : start + 1;
      const e = index ? index[start + 2] : start + 2;
      const da = distances[a], db = distances[b], de = distances[e];
      if ((da > 0 && db > 0 && de > 0) ||
          (da < 0 && db < 0 && de < 0) ||
          (da === 0 && db === 0 && de === 0)) continue;

      vertices[0] = a;
      vertices[1] = b;
      vertices[2] = e;
      let crossings = 0;
      for (let edge = 0; edge < 3 && crossings < 2; edge++) {
        const i0 = vertices[edge], i1 = vertices[(edge + 1) % 3];
        const d0 = distances[i0], d1 = distances[i1];
        if ((d0 > 0) === (d1 > 0)) continue;
        const u = d0 / (d0 - d1);
        const point = crossings === 0 ? p : q;
        for (let axis = 0; axis < 3; axis++) {
          const v0 = world[3 * i0 + axis];
          point[axis] = v0 + (world[3 * i1 + axis] - v0) * u;
        }
        crossings++;
      }
      if (crossings !== 2) continue;
      const segment = clipSegment(p, q, others);
      if (segment) {
        for (let i = 0; i < 6; i++) out.push(segment[i]);
      }
    }
  }
  return new Float32Array(out);
}
