// Isometric scene of Helenaveen, rendered tile by tile by render/run.mjs.
// World units are meters: x east, y up, z south, origin at the center of the 3 x 3 km area.
import * as THREE from 'three';

THREE.ColorManagement.enabled = false; // colors are painted in sRGB and used as-is, like pixel art

const SUN_AZIMUTH = 250; // keep in sync with scripts/sun.py
const SUN_ELEVATION = 40;
const HALF = 1500;
const SLAB = 14; // depth of the diorama block under the ground
const CAMERA_ELEVATION = 30; // 2:1 pixel-art isometric
const TOP_MARGIN = 32;
const BACKGROUND = new THREE.Color(0x20242c);

const DATA = '/data/build';
const TYPES = { house: 0, barn: 1, shed: 2, greenhouse: 3, tank: 4, silo: 5, canopy: 6, church: 7, tower: 8, turret: 9, school: 10, mast: 11, cross: 12 };

const rgb = (r, g, b) => new THREE.Color(r / 255, g / 255, b / 255);
const hash = (x) => {
  const s = Math.sin(x * 12.9898) * 43758.5453;
  return s - Math.floor(s);
};

const WALLS_BARN = [
  [rgb(108, 122, 104), 3], [rgb(78, 96, 80), 2], [rgb(150, 146, 132), 2], [rgb(120, 70, 54), 2], [rgb(96, 102, 108), 2],
];
// Roof colors snap to this palette after a little contrast from the aerial sample.
const ROOFS = [
  rgb(176, 84, 58), rgb(140, 64, 50), rgb(108, 56, 46), rgb(66, 68, 74), rgb(88, 90, 96), rgb(120, 122, 124),
  rgb(150, 150, 146), rgb(184, 182, 176), rgb(120, 92, 70), rgb(98, 114, 98), rgb(214, 214, 206), rgb(44, 48, 56),
];

function pickWeighted(list, r) {
  const total = list.reduce((s, [, w]) => s + w, 0);
  let t = r * total;
  for (const [c, w] of list) if ((t -= w) <= 0) return c;
  return list[0][0];
}

function nearestRoof(c) {
  let best = ROOFS[0], bd = Infinity;
  for (const p of ROOFS) {
    const d = (p.r - c.r) ** 2 * 0.9 + (p.g - c.g) ** 2 * 1.2 + (p.b - c.b) ** 2;
    if (d < bd) { bd = d; best = p; }
  }
  return best;
}

// Facades by construction year (BAG): the eras of a Peel village.
const ERAS = [
  [1945, [[rgb(138, 68, 50), 4], [rgb(118, 58, 44), 3], [rgb(158, 90, 64), 2], [rgb(226, 220, 206), 1]], rgb(236, 234, 226)],
  [1970, [[rgb(160, 88, 62), 4], [rgb(176, 106, 74), 3], [rgb(140, 78, 58), 2], [rgb(200, 172, 132), 1]], rgb(232, 230, 222)],
  [1995, [[rgb(112, 72, 56), 3], [rgb(128, 84, 62), 3], [rgb(196, 170, 128), 2], [rgb(150, 80, 58), 2]], rgb(88, 62, 48)],
  [9999, [[rgb(150, 80, 60), 3], [rgb(112, 108, 104), 2], [rgb(226, 222, 212), 2], [rgb(84, 64, 52), 2], [rgb(176, 104, 74), 1]], rgb(58, 60, 64)],
];

function era(m) {
  return ERAS.find(([until]) => (m.year || 1985) < until);
}

function frameColor(m) {
  if (m.frame_fixed) return rgb(...m.frame_fixed);
  if (m.kind === 'school') return rgb(176, 40, 34);
  return era(m)[2];
}

function roofColor(m) {
  if (m.roof_fixed) return rgb(...m.roof_fixed);
  if (!m.roof_rgb) return ROOFS[4];
  const c = rgb(...m.roof_rgb);
  // Push saturation up a bit: the photo is hazy, pixel art is not.
  const hsl = {};
  c.getHSL(hsl);
  c.setHSL(hsl.h, Math.min(1, hsl.s * 1.5), hsl.l);
  return nearestRoof(c);
}

function wallColor(m) {
  if (m.wall_fixed) return rgb(...m.wall_fixed);
  if (m.kind === 'tank') return [rgb(74, 98, 82), rgb(150, 150, 140), rgb(64, 72, 80)][Math.floor(m.rand * 3)];
  if (m.kind === 'silo') return rgb(196, 198, 192);
  if (m.kind === 'barn' || m.kind === 'shed') return pickWeighted(WALLS_BARN, m.rand);
  return pickWeighted(era(m)[1], m.rand);
}

async function fetchF32(url) {
  return new Float32Array(await (await fetch(url)).arrayBuffer());
}

// ---------------------------------------------------------------------------------------------
// Buildings

const buildingVertex = `
attribute vec2 aUv;
attribute float aKind;
attribute float aType;
attribute float aAxis;
attribute vec3 aFrame;
varying vec3 vFrame;
varying vec2 vUv2;
varying float vKind;
varying float vType;
varying float vAxis;
varying vec3 vWorld;
varying vec3 vWorldNormal;
`;

const buildingFragment = `
varying vec2 vUv2;
varying float vKind;
varying float vType;
varying float vAxis;
varying vec3 vWorld;
varying vec3 vWorldNormal;
varying vec3 vFrame;

vec3 buildingPattern(vec3 base) {
  vec3 c = base;
  bool wall = vKind > 0.5 && vKind < 1.5;
  bool roof = vKind > 1.5;
  int type = int(vType + 0.5);
  if (wall) {
    if (type == 0) {
      // Houses: a grid of windows per storey, and a darker plinth.
      float fl = mod(vUv2.y, 2.8);
      float col = mod(vUv2.x + 0.4, 3.1);
      bool win = vUv2.y > 0.5 && fl > 0.85 && fl < 2.15 && col > 0.8 && col < 2.2;
      if (win) {
        c = vec3(0.21, 0.26, 0.33);
        if (fl > 1.95 || col < 0.98) c = vFrame;
      }
      if (vUv2.y < 0.35) c *= 0.72;
    } else if (type == 1 || type == 2) {
      // Barns and sheds: corrugated metal or brick with a concrete plinth.
      if (mod(vUv2.x, 1.2) < 0.3) c *= 0.88;
      if (vUv2.y < 0.9) c = mix(c, vec3(0.6, 0.6, 0.58), 0.6);
      float bay = mod(vUv2.x, 14.0);
      if (type == 1 && bay > 4.0 && bay < 8.0 && vUv2.y < 4.2 && vUv2.y > 0.2) c = vec3(0.36, 0.38, 0.4);
    } else if (type == 3) {
      // Greenhouse glass: pale with the crop showing through, white mullions.
      c = mix(vec3(0.74, 0.82, 0.84), vec3(0.42, 0.58, 0.42), 0.3);
      if (mod(vUv2.x, 2.0) < 0.28 || mod(vUv2.y, 1.7) < 0.22) c = vec3(0.9, 0.92, 0.92);
    } else if (type == 4) {
      if (mod(vUv2.y, 1.2) < 0.18) c *= 0.85;
    } else if (type == 5) {
      if (mod(vUv2.y, 1.6) < 0.2) c *= 0.82;
    } else if (type == 6) {
      // Canopy: mostly open, just posts.
      if (vUv2.y < 2.6 && mod(vUv2.x, 4.0) > 0.4) c = vec3(0.28, 0.27, 0.25);
    } else if (type == 7) {
      // Church: tall round-arched windows in bays, a darker plinth.
      float cx = mod(vUv2.x + 1.0, 4.2) - 2.1;
      float y = vUv2.y;
      bool arch = y > 6.0 && length(vec2(cx, y - 6.0)) < 0.75;
      if (abs(cx) < 0.75 && y > 2.2 && (y < 6.0 || arch)) {
        c = vec3(0.22, 0.25, 0.32);
        if (mod(y, 1.1) < 0.12 || abs(cx) < 0.06) c = vec3(0.55, 0.56, 0.58);
      }
      if (y < 0.6) c *= 0.78;
    } else if (type == 8) {
      // Church tower: louvred belfry, a clock face below it, a slit window, brick plinth.
      float u = vUv2.x, y = vUv2.y, top = vAxis;
      if (abs(u) < 0.8 && y > top - 3.8 && y < top - 0.9) {
        c = vec3(0.16, 0.16, 0.18);
        if (mod(y, 0.42) < 0.14) c = vec3(0.42, 0.36, 0.3);
      }
      float r = length(vec2(u, y - (top - 5.4)));
      if (r < 0.85) c = r < 0.1 ? vec3(0.15) : (r > 0.72 ? vec3(0.2, 0.2, 0.22) : vec3(0.93, 0.92, 0.86));
      if (abs(u) < 0.28 && y > 4.0 && y < 8.5) c = vec3(0.2, 0.22, 0.28);
      if (y < 0.6) c *= 0.78;
    } else if (type == 9) {
      // Roof turret: white, with arched openings near the top.
      if (abs(vUv2.x) < 0.22 && vUv2.y > vAxis - 1.9 && vUv2.y < vAxis - 0.4) c = vec3(0.18, 0.18, 0.2);
    } else if (type == 10) {
      // 1930s school: tall classroom windows with red frames.
      float col = mod(vUv2.x, 2.0);
      float y = vUv2.y;
      if (col > 0.45 && col < 1.55 && y > 0.9 && y < 3.7) {
        c = vec3(0.22, 0.25, 0.3);
        if (col < 0.58 || col > 1.42 || y < 1.02 || y > 3.58 || abs(y - 2.9) < 0.08) c = vFrame;
      }
      if (y < 0.5) c *= 0.8;
    } else if (type == 11) {
      // Lattice mast: steel cross-bracing.
      float a = fract((vUv2.x + vUv2.y) / 2.2), b = fract((vUv2.y - vUv2.x) / 2.2);
      c = (a < 0.16 || b < 0.16 || mod(vUv2.y, 2.2) < 0.25) ? vec3(0.78, 0.8, 0.82) : vec3(0.42, 0.44, 0.47);
    }
  } else if (roof) {
    if (type >= 8 && type != 10) {
      // Spires and caps: plain slate or metal.
    } else if (type == 3) {
      // Venlo greenhouse roof: rows of glass ridges, lit on one side.
      vec2 dir = vec2(cos(vAxis), sin(vAxis));
      float across = dot(vUv2, vec2(-dir.y, dir.x));
      float t = mod(across, 3.2);
      c = t < 1.6 ? vec3(0.88, 0.92, 0.93) : vec3(0.7, 0.79, 0.82);
      if (t < 0.22) c = vec3(0.56, 0.6, 0.62);
      float along = dot(vUv2, dir);
      if (mod(along, 5.0) < 0.2) c *= 0.93;
    } else if (vWorldNormal.y < 0.97) {
      // Pitched roof: courses of tiles along the contour.
      if (mod(vWorld.y, 0.55) < 0.16) c *= 0.86;
    } else {
      // Flat roof: gravel speckle.
      float n = fract(sin(dot(floor(vUv2 * 2.0), vec2(12.9898, 78.233))) * 43758.5453);
      c *= 0.95 + 0.08 * n;
    }
  }
  return c;
}
`;

async function makeBuildings() {
  const meta = await (await fetch(`${DATA}/buildings.json`)).json();
  const v = await fetchF32(`${DATA}/buildings.bin`);
  const n = v.length / 10;
  const pos = new Float32Array(n * 3), nor = new Float32Array(n * 3), uv = new Float32Array(n * 2);
  const kind = new Float32Array(n), type = new Float32Array(n), axis = new Float32Array(n), col = new Float32Array(n * 3);
  const frame = new Float32Array(n * 3);
  const walls = meta.map(wallColor), roofs = meta.map(roofColor), frames = meta.map(frameColor);
  for (let i = 0; i < n; i++) {
    const o = i * 10;
    pos.set([v[o], v[o + 1], v[o + 2]], i * 3);
    nor.set([v[o + 3], v[o + 4], v[o + 5]], i * 3);
    uv.set([v[o + 6], v[o + 7]], i * 2);
    kind[i] = v[o + 8];
    const b = v[o + 9], m = meta[b];
    type[i] = TYPES[m.kind] ?? 0;
    axis[i] = m.kind === 'greenhouse' ? m.axis : (m.param ?? m.axis);
    frame.set([frames[b].r, frames[b].g, frames[b].b], i * 3);
    const c = kind[i] === 2 ? roofs[b] : walls[b];
    col.set([c.r, c.g, c.b], i * 3);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  g.setAttribute('normal', new THREE.BufferAttribute(nor, 3));
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.setAttribute('aUv', new THREE.BufferAttribute(uv, 2));
  g.setAttribute('aKind', new THREE.BufferAttribute(kind, 1));
  g.setAttribute('aType', new THREE.BufferAttribute(type, 1));
  g.setAttribute('aAxis', new THREE.BufferAttribute(axis, 1));
  g.setAttribute('aFrame', new THREE.BufferAttribute(frame, 3));
  const mat = new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true, side: THREE.DoubleSide });
  mat.onBeforeCompile = (sh) => {
    sh.vertexShader = buildingVertex + sh.vertexShader.replace(
      '#include <begin_vertex>',
      `#include <begin_vertex>
       vUv2 = aUv; vKind = aKind; vType = aType; vAxis = aAxis; vFrame = aFrame;
       vWorld = position; vWorldNormal = normal;`,
    );
    sh.fragmentShader = buildingFragment + sh.fragmentShader.replace(
      '#include <color_fragment>',
      `#include <color_fragment>
       diffuseColor.rgb = buildingPattern(diffuseColor.rgb);`,
    );
  };
  return new THREE.Mesh(g, mat);
}

// ---------------------------------------------------------------------------------------------
// Trees

const LEAVES = [rgb(78, 124, 50), rgb(92, 138, 56), rgb(66, 112, 48), rgb(106, 146, 60), rgb(84, 116, 44), rgb(72, 130, 64)];
const NEEDLES = [rgb(44, 84, 54), rgb(52, 92, 58), rgb(38, 74, 50)];

function lumpySphere(seed) {
  const g = new THREE.IcosahedronGeometry(1, 1);
  const p = g.attributes.position;
  const seen = new Map();
  for (let i = 0; i < p.count; i++) {
    const key = `${p.getX(i).toFixed(3)},${p.getY(i).toFixed(3)},${p.getZ(i).toFixed(3)}`;
    if (!seen.has(key)) seen.set(key, 0.82 + 0.3 * hash(seen.size * 7.1 + seed * 31.7));
    const k = seen.get(key);
    p.setXYZ(i, p.getX(i) * k, p.getY(i) * k, p.getZ(i) * k);
  }
  g.computeVertexNormals();
  return g;
}

async function makeTrees() {
  const t = await fetchF32(`${DATA}/trees.bin`);
  const n = t.length / 10;
  const group = new THREE.Group();
  const variants = [0, 1, 2].map(lumpySphere);
  const leafMat = new THREE.MeshLambertMaterial({ flatShading: true });
  const needleMat = new THREE.MeshLambertMaterial({ flatShading: true });
  const trunkMat = new THREE.MeshLambertMaterial({ color: rgb(92, 72, 54) });
  const counts = [0, 0, 0];
  let conifers = 0;
  for (let i = 0; i < n; i++) {
    if (t[i * 10 + 5] > 0.5) conifers++;
    else counts[Math.floor(t[i * 10 + 9] * 3) % 3]++;
  }
  const crowns = variants.map((g, k) => new THREE.InstancedMesh(g, leafMat, counts[k]));
  const cones = new THREE.InstancedMesh(new THREE.ConeGeometry(1, 1, 7), needleMat, conifers);
  const trunks = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), trunkMat, n);
  const fill = [0, 0, 0];
  let ci = 0;
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), s = new THREE.Vector3(), p = new THREE.Vector3();
  const up = new THREE.Vector3(0, 1, 0);
  for (let i = 0; i < n; i++) {
    const [x, z, h, r, base, kind, , , , seed] = t.subarray(i * 10, i * 10 + 10);
    q.setFromAxisAngle(up, seed * Math.PI * 2);
    const trunkW = Math.min(0.7, 0.3 + h * 0.02);
    const trunkH = Math.max(1, Math.min(base, h - 2 * Math.max(1, (h - base) / 2, Math.min(r * 0.9, h * 0.42))) + 0.8);
    m.compose(p.set(x, trunkH / 2, z), q, s.set(trunkW, trunkH, trunkW));
    trunks.setMatrixAt(i, m);
    if (kind > 0.5) {
      const bottom = base * 0.5;
      m.compose(p.set(x, (bottom + h) / 2, z), q, s.set(r * 0.9, h - bottom, r * 0.9));
      cones.setMatrixAt(ci, m);
      cones.setColorAt(ci++, NEEDLES[Math.floor(seed * 97) % NEEDLES.length]);
    } else {
      const k = Math.floor(seed * 3) % 3;
      // Full, round crowns: seen from above, a tree is mostly crown.
      const half = Math.max(1, (h - base) / 2, Math.min(r * 0.9, h * 0.42));
      m.compose(p.set(x, h - half, z), q, s.set(r * 1.12, half, r * 1.12));
      crowns[k].setMatrixAt(fill[k], m);
      const c = LEAVES[Math.floor(seed * 1013) % LEAVES.length].clone();
      c.multiplyScalar(0.92 + 0.16 * hash(seed * 77));
      crowns[k].setColorAt(fill[k]++, c);
    }
  }
  for (const mesh of [...crowns, cones, trunks]) {
    mesh.frustumCulled = false;
    group.add(mesh);
  }
  return group;
}

// ---------------------------------------------------------------------------------------------
// Ground and diorama block

async function makeGround(renderer) {
  const group = new THREE.Group();
  const loader = new THREE.TextureLoader();
  const n = 6, size = 500;
  const jobs = [];
  for (let ix = 0; ix < n; ix++) {
    for (let iy = 0; iy < n; iy++) {
      jobs.push(
        loader.loadAsync(`${DATA}/ground/${ix}_${iy}.png`).then((tex) => {
          tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
          tex.generateMipmaps = true;
          tex.minFilter = THREE.LinearMipmapLinearFilter;
          tex.magFilter = THREE.LinearFilter;
          tex.wrapS = tex.wrapT = THREE.ClampToEdgeWrapping;
          const plane = new THREE.Mesh(new THREE.PlaneGeometry(size, size), new THREE.MeshBasicMaterial({ map: tex }));
          plane.rotation.x = -Math.PI / 2;
          plane.position.set(-HALF + size / 2 + ix * size, 0, HALF - size / 2 - iy * size);
          group.add(plane);
        }),
      );
    }
  }
  await Promise.all(jobs);
  return group;
}

function makeSlab() {
  // Peat over sand: the soil Helenaveen was dug out of.
  const c = document.createElement('canvas');
  c.width = 4;
  c.height = 280;
  const ctx = c.getContext('2d');
  const layers = [
    [0, 6, '#4b3a26'], [6, 10, '#2e2218'], [10, 60, '#3a2a1c'], [60, 64, '#2a1f16'], [64, 110, '#45321f'],
    [110, 116, '#2c2117'], [116, 150, '#56402a'], [150, 158, '#7a6a4a'], [158, 280, '#b39c6c'],
  ];
  for (const [a, b, col] of layers) {
    ctx.fillStyle = col;
    ctx.fillRect(0, a, 4, b - a);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.magFilter = THREE.NearestFilter;
  tex.minFilter = THREE.NearestFilter;
  const side = new THREE.MeshLambertMaterial({ map: tex });
  const top = new THREE.MeshBasicMaterial({ color: 0x3a2a1c });
  const box = new THREE.Mesh(new THREE.BoxGeometry(HALF * 2, SLAB, HALF * 2), [side, side, top, top, side, side]);
  box.position.y = -SLAB / 2 - 0.02;
  return box;
}

// ---------------------------------------------------------------------------------------------
// Camera, lights and the outline pass

const deg = Math.PI / 180;

function makeCamera(scale) {
  const el = CAMERA_ELEVATION * deg;
  const u = HALF * Math.SQRT2;
  const vGround = u * Math.sin(el);
  const width = Math.round(2 * u * scale);
  const top = vGround + TOP_MARGIN;
  const bottom = -vGround - SLAB * Math.cos(el) - 6;
  const height = Math.round((top - bottom) * scale);
  const cam = new THREE.OrthographicCamera(-width / scale / 2, width / scale / 2, top, top - height / scale, 10, 9000);
  const fwd = new THREE.Vector3(Math.cos(el) / Math.SQRT2, -Math.sin(el), -Math.cos(el) / Math.SQRT2);
  cam.position.copy(fwd.multiplyScalar(-4000));
  cam.up.set(0, 1, 0);
  cam.lookAt(0, 0, 0);
  return { cam, width, height };
}

function makeLights(scene) {
  const az = SUN_AZIMUTH * deg, el = SUN_ELEVATION * deg;
  // Toward the sun, in world axes: east = +x, north = -z.
  const dir = new THREE.Vector3(Math.sin(az) * Math.cos(el), Math.sin(el), -Math.cos(az) * Math.cos(el));
  const sun = new THREE.DirectionalLight(0xfff4e0, 0.95 * Math.PI);
  sun.position.copy(dir.multiplyScalar(1000));
  scene.add(sun);
  scene.add(new THREE.HemisphereLight(0xc8d8f0, 0x6a6450, 0.62 * Math.PI));
}

const outlineShader = {
  uniforms: { tColor: { value: null }, tDepth: { value: null }, texel: { value: new THREE.Vector2() }, range: { value: 1 }, bg: { value: BACKGROUND } },
  vertexShader: `varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }`,
  fragmentShader: `
    uniform sampler2D tColor; uniform sampler2D tDepth; uniform vec2 texel; uniform float range; uniform vec3 bg;
    varying vec2 vUv;
    float depthAt(vec2 uv) { return texture2D(tDepth, uv).x * range; }
    void main() {
      vec4 c = texture2D(tColor, vUv);
      float d = depthAt(vUv);
      float gap = 0.0;
      gap = max(gap, depthAt(vUv + vec2(texel.x, 0.0)) - d);
      gap = max(gap, depthAt(vUv - vec2(texel.x, 0.0)) - d);
      gap = max(gap, depthAt(vUv + vec2(0.0, texel.y)) - d);
      gap = max(gap, depthAt(vUv - vec2(0.0, texel.y)) - d);
      // A big step in depth means this pixel is the near side of a silhouette: ink it.
      if (gap > 2.2) c.rgb *= 0.58;
      gl_FragColor = vec4(c.rgb, 1.0);
    }`,
};

// ---------------------------------------------------------------------------------------------

async function main() {
  const params = new URLSearchParams(location.search);
  const scale = parseFloat(params.get('scale') || '3');
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true });
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  renderer.setPixelRatio(1);
  document.body.appendChild(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = BACKGROUND;
  makeLights(scene);
  const [ground, buildings, trees] = await Promise.all([makeGround(renderer), makeBuildings(), makeTrees()]);
  scene.add(ground, buildings, trees, makeSlab());

  const { cam, width, height } = makeCamera(scale);
  let target = null;
  const post = new THREE.ShaderMaterial(outlineShader);
  const quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), post);
  const postScene = new THREE.Scene();
  postScene.add(quad);
  const postCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

  function ensureTarget(w, h) {
    if (target && target.width === w && target.height === h) return;
    target?.dispose();
    target = new THREE.WebGLRenderTarget(w, h, { depthBuffer: true });
    target.depthTexture = new THREE.DepthTexture(w, h, THREE.FloatType);
    target.texture.minFilter = target.texture.magFilter = THREE.NearestFilter;
  }

  window.renderTile = (x, y, w, h) => {
    renderer.setSize(w, h, false);
    ensureTarget(w, h);
    cam.setViewOffset(width, height, x, y, w, h);
    cam.updateProjectionMatrix();
    renderer.setRenderTarget(target);
    renderer.render(scene, cam);
    post.uniforms.tColor.value = target.texture;
    post.uniforms.tDepth.value = target.depthTexture;
    post.uniforms.texel.value.set(1 / w, 1 / h);
    post.uniforms.range.value = cam.far - cam.near;
    renderer.setRenderTarget(null);
    renderer.render(postScene, postCam);
    return renderer.domElement.toDataURL('image/png');
  };
  window.sceneInfo = { width, height, scale };
  window.ready = true;
}

main().catch((e) => {
  window.loadError = String(e.stack || e);
  console.error(e);
});
