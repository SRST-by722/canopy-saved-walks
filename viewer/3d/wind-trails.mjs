/* co_demo_001 (CO for the London demo): short wind streaks with direction, after the Bristol viewer, from the u/v that the London
   scene already ships for its final wind snapshot (scene.json protocol_display.npy_transport['wind.npy']: 1 x 3 x 2048 x 2048,
   8-bit codes, value = offset + code * scale, code 255 = invalid; part 0 = u (east), part 1 = v (north); 4 m cells, row 0 = south,
   column 0 = west, the same frame as the fields and the lite proxy city). Building cells come from masks/wind_invalid_zyx.npy
   layer 0 (the mask the speed map uses at this height); no streak starts, stays or steps into them, and a tail is cut where it would cross one.
   The field is one moment (model t = 7500 s, the last of the 300 steps). The streaks are tracers that move along that fixed field:
   they show its direction and speed, not how the wind changed over time. Their motion is sped up for display. */
import * as THREE from 'three';

const RAMP = ['#2b83ba', '#29b6c6', '#7fd6a1', '#e6f08a', '#fdae61'].map(c => new THREE.Color(c));   // slow -> fast
const LIFE = 2.2;   // s on screen

async function gunzipBytes(url, expect) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`wind streaks: HTTP ${r.status} for ${url}`);
  const b = new Uint8Array(await new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
  if (expect && b.byteLength !== expect) throw new Error('wind streaks: unexpected size of ' + url);
  return b;
}

export function windTrailsAvailable(scene) {
  const t = scene?.protocol_display?.npy_transport?.['wind.npy'];
  return !!(t && t.meta?.shape?.length === 4 && t.meta.shape[1] >= 2 && t.parts?.length >= 2 && t.meta.quantization);
}

/**
 * scene, camera, controls: the viewer's; physicsURL: URL of the scene's physics/ folder; sceneJSON: scene.json;
 * x0, zs: world x of the west edge and world z of the south edge (main.js X0, ZS); y: drawing height; count: streaks; scale: m/s at the top of the colour ramp
 */
export function createWindTrails({ scene, camera, controls, physicsURL, sceneJSON, x0, zs, y = 7, count = 4000, scale = 1.0, t = 7500, onStatus = () => {} }) {
  const T = sceneJSON.protocol_display.npy_transport['wind.npy'], M = sceneJSON.protocol_display.npy_transport['masks/wind_invalid_zyx.npy'];
  const [, , H, W] = T.meta.shape, plane = H * W, q = T.meta.quantization, CELL = (sceneJSON.grid.cols * sceneJSON.grid.cell_m) / W;   // 4 m: 2048 columns over 8,192 m
  const S = { u: null, v: null, solid: null, loading: null, on: false, n: 0, steps: 0, t };
  let N = count, P = new Float32Array(2 * N), age = new Float32Array(N);
  let geo = null, mesh = null;
  function build(n) {
    N = n; P = new Float32Array(2 * N); age = new Float32Array(N);
    if (mesh) { scene.remove(mesh); geo.dispose(); }
    geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(N * 12), 3));
    geo.setAttribute('color', new THREE.BufferAttribute(new Float32Array(N * 16), 4));
    const idx = new Uint32Array(N * 6);
    for (let i = 0; i < N; i++) { const a = 4 * i, o = 6 * i; idx[o] = a; idx[o + 1] = a + 1; idx[o + 2] = a + 2; idx[o + 3] = a + 1; idx[o + 4] = a + 3; idx[o + 5] = a + 2; }
    geo.setIndex(new THREE.BufferAttribute(idx, 1));
    mesh = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ vertexColors: true, transparent: true, depthWrite: false, side: THREE.DoubleSide }));
    mesh.name = 'wind-streaks-t7500'; mesh.frustumCulled = false; mesh.renderOrder = 5; mesh.visible = S.on;
    scene.add(mesh);
    if (S.u) for (let i = 0; i < N; i++) spawn(i, true);
  }
  build(N);
  async function load() {
    if (S.u) return;
    if (!S.loading) S.loading = (async () => {
      onStatus('Loading wind directions (t = ' + S.t + ' s)…');
      const base = new URL(physicsURL, location.href);
      const [u, v, m] = await Promise.all([gunzipBytes(new URL(T.parts[0].file, base), plane), gunzipBytes(new URL(T.parts[1].file, base), plane),
        M ? gunzipBytes(new URL(M.parts[0].file, base), plane) : Promise.resolve(null)]);
      if (T.parts[0].offset !== 0 || T.parts[1].offset !== plane) throw new Error('wind streaks: unexpected channel layout');
      S.u = u; S.v = v; S.solid = m;
      for (let i = 0; i < N; i++) spawn(i, true);
      onStatus('');
    })().catch(e => { S.loading = null; onStatus('Wind streaks unavailable: ' + e.message); throw e; });
    return S.loading;
  }
  const val = (A, k) => (A[k] === 255 ? NaN : q.offset + A[k] * q.scale);
  // u, v (m/s, east / north) at world-plan position (x east, n north), bilinear on cell centres; null in or next to building cells
  function windAt(x, n) {
    if (!S.u) return null;
    const fx = (x - x0) / CELL - 0.5, fy = (n + zs) / CELL - 0.5;   // world z = -north; row 0 = south edge at north = -zs
    if (fx < 0 || fy < 0 || fx >= W - 1 || fy >= H - 1) return null;
    const i = fx | 0, j = fy | 0, a = fx - i, b = fy - j, k = j * W + i;
    const sd = S.solid;
    if (sd && (sd[k] || sd[k + 1] || sd[k + W] || sd[k + W + 1])) return null;
    const bl = A => (val(A, k) * (1 - a) + val(A, k + 1) * a) * (1 - b) + (val(A, k + W) * (1 - a) + val(A, k + W + 1) * a) * b;
    const u = bl(S.u), v = bl(S.v);
    return Number.isFinite(u) && Number.isFinite(v) ? [u, v] : null;
  }
  // true when the 4 m cell holding (x east, n north) is inside the grid and not a building cell
  function clear(x, n) {
    const c = Math.floor((x - x0) / CELL), r = Math.floor((n + zs) / CELL);
    return c >= 0 && r >= 0 && c < W && r < H && !(S.solid && S.solid[r * W + c]);
  }
  function region() { const t = controls.target, d = camera.position.distanceTo(t); return { cx: t.x, cn: -t.z, r: Math.min(4300, Math.max(150, d * 1.1)), d }; }
  function spawn(i, any) {
    const R = region();
    P[2 * i] = R.cx + (Math.random() * 2 - 1) * R.r; P[2 * i + 1] = R.cn + (Math.random() * 2 - 1) * R.r;
    age[i] = any ? Math.random() * LIFE : 0;
  }
  function update(dt) {
    if (!S.on || !S.u) return false;
    dt = Math.min(0.1, Math.max(0, dt)); S.steps++;
    const R = region(), accel = R.r / (8 * scale), L = 0.6 * accel, w = Math.max(R.r, R.d * 0.8) / 700;
    const pos = geo.attributes.position.array, col = geo.attributes.color.array;
    for (let i = 0; i < N; i++) {
      let x = P[2 * i], n = P[2 * i + 1]; const uv = windAt(x, n); age[i] += dt;
      const q12 = 12 * i, q16 = 16 * i;
      if (!uv || age[i] > LIFE || Math.abs(x - R.cx) > R.r * 1.2 || Math.abs(n - R.cn) > R.r * 1.2 || Math.hypot(uv[0], uv[1]) < 0.02) {
        spawn(i, false); pos.fill(0, q12, q12 + 12); col.fill(0, q16, q16 + 16); continue;
      }
      x += uv[0] * dt * accel; n += uv[1] * dt * accel;
      if (!clear(x, n)) { spawn(i, false); pos.fill(0, q12, q12 + 12); col.fill(0, q16, q16 + 16); continue; }   // the step would enter a building cell or leave the grid
      P[2 * i] = x; P[2 * i + 1] = n;
      // the tail is cut where it would cross a building cell (checked every metre back from the head, at most 240 checks)
      const sp = Math.hypot(uv[0], uv[1]); let Lc = L;
      { const len = sp * L, ns = Math.min(240, Math.ceil(len / (CELL / 4))); for (let k = 1; k <= ns; k++) { const f = k / ns; if (!clear(x - uv[0] * L * f, n - uv[1] * L * f)) { Lc = L * (k - 1) / ns; break; } } }
      const tx = x - uv[0] * Lc, tn = n - uv[1] * Lc, ex = -uv[1] / sp * w, en = uv[0] / sp * w;
      // head left / right, tail left / right (narrower); world z = -north
      pos[q12] = x + ex; pos[q12 + 1] = y; pos[q12 + 2] = -(n + en); pos[q12 + 3] = x - ex; pos[q12 + 4] = y; pos[q12 + 5] = -(n - en);
      pos[q12 + 6] = tx + ex * 0.35; pos[q12 + 7] = y; pos[q12 + 8] = -(tn + en * 0.35); pos[q12 + 9] = tx - ex * 0.35; pos[q12 + 10] = y; pos[q12 + 11] = -(tn - en * 0.35);
      const rt = Math.min(0.999, sp / scale) * (RAMP.length - 1), ri = rt | 0, f = rt - ri, A = RAMP[ri], B = RAMP[ri + 1];
      const r = A.r + (B.r - A.r) * f, g = A.g + (B.g - A.g) * f, bb = A.b + (B.b - A.b) * f;
      const fade = Math.min(1, age[i] * 3) * Math.min(1, (LIFE - age[i]) * 3), ah = 0.95 * fade, at = 0.12 * fade;
      for (let k = 0; k < 4; k++) { const o = q16 + 4 * k; col[o] = r; col[o + 1] = g; col[o + 2] = bb; col[o + 3] = k < 2 ? ah : at; }
    }
    geo.attributes.position.needsUpdate = true; geo.attributes.color.needsUpdate = true;
    return true;
  }
  return {
    S, windAt, update, load, clear, cell: CELL,
    heads: () => P.slice(0, 2 * N),   // [east, north] pairs, for tests
    get count() { return N; },
    setCount(n) { if (n !== N) build(n); },
    async setActive(on) { S.on = !!on; if (mesh) mesh.visible = S.on; if (on) await load(); },
    setOpacity(v) { if (mesh) mesh.material.opacity = Math.max(0, Math.min(1, v)); },
    /** where the heads are: fraction in building cells (should be 0) and the mean motion (m/s east, north) of the streaks drawn */
    audit() {
      if (!S.u) return null; let solid = 0, drawn = 0, ue = 0, vn = 0;
      for (let i = 0; i < N; i++) {
        const x = P[2 * i], n = P[2 * i + 1], c = Math.floor((x - x0) / CELL), rr = Math.floor((n + zs) / CELL);
        if (c < 0 || rr < 0 || c >= W || rr >= H) continue; const k = rr * W + c, uv = windAt(x, n); if (!uv) continue;
        drawn++; if (S.solid?.[k]) solid++; ue += uv[0]; vn += uv[1];
      }
      return { drawn, heads_in_building_cells: solid, mean_u_east: drawn ? ue / drawn : null, mean_v_north: drawn ? vn / drawn : null, steps: S.steps, on: S.on };
    },
  };
}
