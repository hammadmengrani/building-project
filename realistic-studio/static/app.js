import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TransformControls } from 'three/addons/controls/TransformControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
const $ = id => document.getElementById(id), clone = v => JSON.parse(JSON.stringify(v));
const state = {
  source: 'example',
  config: null,
  scene: null,
  edits: {},
  base: '/output/example',
  view: 'exterior',
  floor: 'all',
  mode: 'rendered',
  tool: 'select',
  selected: null,
  objects: [],
  busy: false,
  history: [],
  future: [],
  loadSerial: 0,
  dirty: false
};
const viewport = $('viewport');
let renderer;
try {
  renderer = new THREE.WebGLRenderer({
    antialias: true,
    preserveDrawingBuffer: true
  });
} catch (e) {
  $('empty').innerHTML = '<h2>WebGL is unavailable</h2><p>Enable hardware acceleration in your browser to use the studio.</p>';
  throw e;
}
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.6));
renderer.shadowMap.enabled = true;
renderer.shadowMap.autoUpdate = false;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1;
renderer.outputColorSpace = THREE.SRGBColorSpace;
viewport.prepend(renderer.domElement);
const world = new THREE.Scene();
world.background = new THREE.Color('#89949a');
const camera = new THREE.PerspectiveCamera(43, 1, .05, 500);
camera.position.set(22, 17, 22);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = .09;
controls.maxPolarAngle = Math.PI * .49;
controls.minDistance = 1;
controls.maxDistance = 130;
const ambient = new THREE.HemisphereLight(0xc9dcf0, 0x746653, 2.2);
world.add(ambient);
const sun = new THREE.DirectionalLight(0xffefd5, 4.0);
sun.position.set(- 8, 20, 10);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.bias = - .00015;
sun.shadow.normalBias = .04;
sun.shadow.camera.left = - 24;
sun.shadow.camera.right = 24;
sun.shadow.camera.top = 24;
sun.shadow.camera.bottom = - 24;
sun.shadow.camera.near = .1;
sun.shadow.camera.far = 90;
world.add(sun, sun.target);
const fill = new THREE.DirectionalLight(0xdce8ff, 1);
fill.position.set(12, 8, - 12);
world.add(fill);
// A local studio environment; no external HDR dependency or remote tracking.
const envScene = new THREE.Scene();
envScene.background = new THREE.Color(0xb9c9d7);
const groundEnv = new THREE.Mesh(new THREE.PlaneGeometry(100, 100), new THREE.MeshBasicMaterial({
  color: 0x68705e,
  side: THREE.DoubleSide
}));
groundEnv.rotation.x = - Math.PI / 2;
groundEnv.position.y = - 5;
envScene.add(groundEnv);
for (const[x, y, z, s] of[[- 7, 9, 6, 5], [8, 5, - 7, 3]]) {
  const panel = new THREE.Mesh(new THREE.PlaneGeometry(s, s), new THREE.MeshBasicMaterial({
    color: new THREE.Color(3, 2.8, 2.5),
    side: THREE.DoubleSide
  }));
  panel.position.set(x, y, z);
  panel.lookAt(0, 0, 0);
  envScene.add(panel);
}
const pmrem = new THREE.PMREMGenerator(renderer);
const envTarget = pmrem.fromScene(envScene, .06);
world.environment = envTarget.texture;
pmrem.dispose();
const ground = new THREE.Mesh(new THREE.PlaneGeometry(300, 300), new THREE.MeshStandardMaterial({
  color: '#707770',
  roughness: 1
}));
ground.rotation.x = - Math.PI / 2;
ground.position.y = - .23;
ground.receiveShadow = true;
world.add(ground);
const grid = new THREE.GridHelper(80, 80, 0xb2b7bb, 0x7d888d);
grid.position.y = - .21;
grid.material.opacity = .26;
grid.material.transparent = true;
grid.material.depthWrite = false;
world.add(grid);
const axes = new THREE.AxesHelper(3);
axes.position.set(0, .04, 0);
world.add(axes);
const selectionBox = new THREE.BoxHelper(new THREE.Object3D(), 0xe5bc77);
selectionBox.visible = false;
selectionBox.material.depthTest = false;
selectionBox.renderOrder = 10;
world.add(selectionBox);
const gizmo = new TransformControls(camera, renderer.domElement);
gizmo.setSize(.85);
world.add(gizmo.getHelper());
gizmo.setTranslationSnap(.1);
gizmo.setRotationSnap(THREE.MathUtils.degToRad(5));
gizmo.setScaleSnap(.05);
let model = null, edgeGroup = null, down = null, dragged = false, lastNoticeTimer;
const loader = new GLTFLoader(), ray = new THREE.Raycaster();
function notice(text, error = false, persist = false) {
  clearTimeout(lastNoticeTimer);
  $('notice').textContent = text;
  $('notice').classList.toggle('error', error);
  $('notice').hidden = false;
  if (! persist) lastNoticeTimer = setTimeout(() => $('notice').hidden = true, error ? 14000: 7000);
}
function dirty() {
  state.dirty = true;
  $('dirty').style.color = '#d9b67a';
}
function pushHistory() {
  state.history.push(clone(state.edits));
  if (state.history.length > 50) state.history.shift();
  state.future =[];
}
function refreshHistory() {
  applyAllEdits();
  fillInputs();
  updateSelectionBox();
  dirty();
}
function undo() {
  if (! state.history.length) return;
  state.future.push(clone(state.edits));
  state.edits = state.history.pop();
  refreshHistory();
}
function redo() {
  if (! state.future.length) return;
  state.history.push(clone(state.edits));
  state.edits = state.future.pop();
  refreshHistory();
}
function editable(o) {
  while (o && o !== model) {
    if (o.userData.entity) return o;
    o = o.parent;
  }
  return null;
}
function objectMeshes(object, fn) {
  object.traverse(o => {
    if (o.isMesh && ! o.userData.edge) fn(o);
  });
}
function setTint(object, color) {
  objectMeshes(object, o => {
    const mats = Array.isArray(o.material) ? o.material: [o.material];
    for (const m of mats) if (m.color) {
      m.color.set(color);
      m.map = null;
      m.needsUpdate = true;
    }
  });
}
function rememberOriginal(object) {
  object.userData.originalTransform = {
    position: object.position.toArray(),
    rotation: [object.rotation.x, object.rotation.y, object.rotation.z],
    scale: object.scale.toArray()
  };
  objectMeshes(object, o => {
    o.userData.originalMaterials =(Array.isArray(o.material) ? o.material: [o.material]).map(m => m.clone());
  });
}
function restoreMaterials(object) {
  objectMeshes(object, o => {
    if (o.userData.displayMaterials) {
      const display = Array.isArray(o.userData.displayMaterials) ? o.userData.displayMaterials: [o.userData.displayMaterials];
      display.forEach(m => m.dispose());
      delete o.userData.displayMaterials;
    }
    const old = Array.isArray(o.material) ? o.material: [o.material];
    old.forEach(m => m.dispose());
    const next = o.userData.originalMaterials.map(m => m.clone());
    o.material = next.length === 1 ? next[0]: next;
  });
}
function applyAllEdits() {
  for (const object of state.objects) {
    const base = object.userData.originalTransform,
    edit = state.edits[object.userData.entity] || {};
    object.position.fromArray(edit.position || base.position);
    object.rotation.set(...(edit.rotation || base.rotation));
    object.scale.fromArray(edit.scale || base.scale);
    restoreMaterials(object);
    if (edit.color) setTint(object, edit.color);
  }
  setShading(state.mode);
}
function captureSelected() {
  renderer.shadowMap.needsUpdate = true;
  const o = state.selected;
  if (! o) return;
  const prior = state.edits[o.userData.entity] || {};
  state.edits[o.userData.entity] = {
    ... prior,
    position: o.position.toArray(),
    rotation: [o.rotation.x, o.rotation.y, o.rotation.z],
    scale: o.scale.toArray()
  };
  dirty();
  fillInputs();
  updateSelectionBox();
}
function updateSelectionBox() {
  selectionBox.visible = ! ! state.selected;
  if (state.selected) {
    state.selected.updateWorldMatrix(true, true);
    selectionBox.setFromObject(state.selected);
  }
}
function setTool(tool) {
  state.tool = tool;
  document.querySelectorAll('[data-tool]').forEach(b => b.classList.toggle('active', b.dataset.tool === tool));
  if (tool === 'select') gizmo.detach();
  else if (state.selected) {
    gizmo.setMode(tool);
    gizmo.attach(state.selected);
  }
}
function select(object) {
  state.selected = object;
  gizmo.detach();
  $('object-name').textContent = object ? object.userData.displayName: 'Scene settings';
  $('object-type').textContent = object ? object.userData.category || 'Editable scene object': 'Select an object to inspect its transform.';
  $('selection-status').textContent = object ? object.userData.displayName: 'No object selected';
  $('color').disabled = ! object;
  if (object) {
    let m;
    objectMeshes(object, o => {
      if (! m) {
        const actual = o.userData.displayMaterials || o.material;
        m = Array.isArray(actual) ? actual[0]: actual;
      }
    });
    if (m?.color) $('color').value = '#' + m.color.getHexString();
    if (state.tool !== 'select') {
      gizmo.setMode(state.tool);
      gizmo.attach(object);
    }
  }
  fillInputs();
  updateSelectionBox();
  document.querySelectorAll('[data-entity]').forEach(b => b.classList.toggle('active', b.dataset.entity === object?.userData.entity));
}
function fillInputs() {
  for (const field of['position', 'rotation', 'scale']) for (let i = 0; i < 3; i ++) {
    const input = $(`${field}-${i}`);
    if (! input) continue;
    input.disabled = ! state.selected;
    const a = state.selected ?(field === 'rotation' ?[state.selected.rotation.x, state.selected.rotation.y, state.selected.rotation.z]: state.selected[field].toArray()): [0, 0, 0];
    input.value =(field === 'rotation' ? THREE.MathUtils.radToDeg(a[i]): a[i]).toFixed(2);
  }
}
for (const[field, label] of[['position', 'Location'], ['rotation', 'Rotation'], ['scale', 'Scale']]) {
  const row = document.createElement('div');
  row.className = 'transform-row';
  row.innerHTML = `<span>${label}</span>`;
  ['X', 'Y', 'Z'].forEach((axis, i) => {
    const label = document.createElement('label');
    label.innerHTML = `<span>${axis}</span><input type="number" id="${field}-${i}" step="${field==='rotation'?5:.1}" aria-label="${field} ${axis}" disabled>`;
    row.append(label);
    const control = label.querySelector('input');
    let commitTimer;
    const commit = e => {
      if (! state.selected) return;
      const v = Number(e.target.value);
      if (! Number.isFinite(v) || Math.abs(v) > 500 ||(field === 'scale' &&(v < .05 || v > 20))) {
        fillInputs();
        return;
      }
      const next = field === 'rotation' ? THREE.MathUtils.degToRad(v): v;
      if (Math.abs(state.selected[field][['x', 'y', 'z'][i]] - next) < .000001) {
        fillInputs();
        return;
      }
      pushHistory();
      state.selected[field][['x', 'y', 'z'][i]] = next;
      captureSelected();
    };
    control.addEventListener('change', commit);
    control.addEventListener('blur', commit);
    control.addEventListener('input', e => {
      clearTimeout(commitTimer);
      commitTimer = setTimeout(() => commit(e), 250);
    });
  });
  $('transforms').append(row);
}
gizmo.addEventListener('dragging-changed', e => {
  controls.enabled = ! e.value;
  dragged = true;
  if (e.value) pushHistory();
  else captureSelected();
});
gizmo.addEventListener('objectChange', () => {
  renderer.shadowMap.needsUpdate = true;
  fillInputs();
  updateSelectionBox();
});
renderer.domElement.addEventListener('pointerdown', e => {
  down = {
    x: e.clientX,
    y: e.clientY
  };
  dragged = false;
});
renderer.domElement.addEventListener('pointerup', e => {
  if (! model || ! down || dragged || e.button !== 0 || Math.hypot(e.clientX - down.x, e.clientY - down.y) > 5) return;
  const r = renderer.domElement.getBoundingClientRect();
  ray.setFromCamera(new THREE.Vector2((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1), camera);
  const hits = ray.intersectObject(model, true).filter(h => h.object.visible && ! h.object.userData.edge && editable(h.object)?.visible);
  select(hits.length ? editable(hits[0].object): null);
});
function drawOutliner() {
  const filter = $('search').value.toLowerCase();
  $('outliner').replaceChildren();
  for (const o of state.objects) {
    if (! o.visible || !(o.userData.displayName || o.name).toLowerCase().includes(filter)) continue;
    const b = document.createElement('button');
    b.dataset.entity = o.userData.entity;
    b.classList.toggle('active', state.selected === o);
    const icon = document.createElement('span');
    icon.textContent = o.userData.category === 'Furniture' ? '◈': '◇';
    b.append(icon, document.createTextNode(o.userData.displayName || o.name));
    b.title = o.userData.entity;
    b.onclick =() => select(o);
    $('outliner').append(b);
  }
  $('object-count').textContent = state.objects.length;
}
function disposeModel(root) {
  root.traverse(o => {
    if (o.isMesh || o.isLineSegments) {
      o.geometry?.dispose();
      const mats = Array.isArray(o.material) ? o.material: [o.material];
      mats.forEach(m => {
        if (! m) return;
        for (const value of Object.values(m)) if (value?.isTexture) value.dispose();
        m.dispose();
      });
      o.userData.originalMaterials?.forEach(m => m.dispose());
    }
  });
}
function rebuildEdges() {
  if (edgeGroup) {
    world.remove(edgeGroup);
    edgeGroup.traverse(o => {
      o.geometry?.dispose();
      o.material?.dispose();
    });
  }
  edgeGroup = new THREE.Group();
  if (model) model.traverse(o => {
    if (! o.isMesh) return;
    const edge = new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry, 28), new THREE.LineBasicMaterial({
      color: 0x232729,
      transparent: true,
      opacity: .45
    }));
    edge.matrixAutoUpdate = false;
    o.updateWorldMatrix(true, false);
    edge.matrix.copy(o.matrixWorld);
    edge.userData.entity = editable(o);
    edge.visible = editable(o)?.visible !== false;
    edgeGroup.add(edge);
  });
  world.add(edgeGroup);
  edgeGroup.visible = $('edges').checked;
}
async function loadModel({
  fit = true
}
= {}) {
  const serial = ++ state.loadSerial;
  $('status').textContent = 'Loading scene…';
  try {
    const gltf = await loader.loadAsync(`${state.base}/${state.view}.glb`);
    if (serial !== state.loadSerial) {
      disposeModel(gltf.scene);
      return;
    }
    select(null);
    if (model) {
      world.remove(model);
      disposeModel(model);
    }
    model = gltf.scene;
    world.add(model);
    state.objects =[];
    model.traverse(o => {
      if (o.isMesh) {
        o.castShadow = true;
        o.receiveShadow = true;
        o.material = Array.isArray(o.material) ? o.material.map(m => m.clone()): o.material.clone();
      }
      if (o.userData.entity) state.objects.push(o);
    });
    state.objects.forEach((o, i) => {
      const key = o.userData.source_key || o.userData.entity,
      category = o.userData.category || 'Object',
      id = key.split(':')[1],
      layout = o.userData.level ?(state.scene?.upper_floors ||[]).find(f => f.level === o.userData.level): state.scene,
      room = layout?.rooms.find(r => r.id === id),
      f = layout?.furniture.find(f => f.id === id);
      o.userData.displayName = room ? `${category} / ${room.name}`: f ? `${f.kind[0].toUpperCase()+f.kind.slice(1)} / ${f.id}`: category === 'Wall' ? `Wall segment / ${i+1}`: category === 'Facade' ? `Facade / ${room?.name||id}`: `${category} / ${id||'Ground'}`;
      rememberOriginal(o);
    });
    applyAllEdits();
    updateFloorSelector();
    applyFloorVisibility();
    rebuildEdges();
    drawOutliner();
    $('empty').hidden = true;
    if (fit) frameScene();
    $('status').textContent = 'Scene ready';
    $('scene-badge').textContent = (state.source === 'example' ? 'EXAMPLE' : state.source === 'groq' ? 'GROQ' : 'PROJECT') + ' / ' + (state.scene?.storeys || 1) + ' FLOORS';
    updateStats();
  } catch (e) {
    notice('Could not load 3D model: ' + e.message, true);
    $('status').textContent = 'Model loading failed';
  }
}
function updateFloorSelector() {
  const select = $('floor-view');
  select.replaceChildren();
  const all = document.createElement('option');
  all.value = 'all';
  all.textContent = 'All floors';
  select.append(all);
  for (let i = 0; i <(state.scene?.storeys || 1); i ++) {
    const option = document.createElement('option');
    option.value = String(i);
    option.textContent = i === 0 ? 'Ground floor': `Floor ${i+1}`;
    select.append(option);
  }
  if (![... select.options].some(o => o.value === state.floor)) state.floor = 'all';
  select.value = state.floor;
}
function applyFloorVisibility() {
  select(null);
  for (const o of state.objects) o.visible = state.floor === 'all' ||(o.userData.level || 0) === Number(state.floor);
  renderer.shadowMap.needsUpdate = true;
  drawOutliner();
}
$('floor-view').onchange = e => {
  state.floor = e.target.value;
  applyFloorVisibility();
  rebuildEdges();
  frameScene();
};
function updateStats() {
  let tris = 0;
  model?.traverse(o => {
    if (o.isMesh) tris +=(o.geometry.index?.count || o.geometry.attributes.position.count) / 3;
  });
  $('stats').textContent = `${state.objects.length} OBJECTS · ${Math.round(tris).toLocaleString()} TRIANGLES`;
}
function frameScene() {
  if (! model) return;
  const box = new THREE.Box3();
  for (const o of state.objects) if (o.visible) box.union(new THREE.Box3().setFromObject(o));
  if (box.isEmpty()) box.setFromObject(model);
  const center = box.getCenter(new THREE.Vector3()),
  size = box.getSize(new THREE.Vector3());
  center.y = Math.max(center.y, 1);
  controls.target.copy(center);
  const halfFov = Math.min(THREE.MathUtils.degToRad(camera.fov) / 2, Math.atan(Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * camera.aspect));
  const d = size.length() / 2 / Math.sin(halfFov) * 1.04;
  camera.position.copy(center).add(new THREE.Vector3(.70, .55, .85).normalize().multiplyScalar(d));
  controls.maxDistance = Math.max(130, d * 3);
  camera.far = Math.max(500, d * 10);
  camera.updateProjectionMatrix();
  controls.update();
  sun.target.position.copy(center);
  sun.position.copy(center).add(new THREE.Vector3(- 12, 20, 15));
  grid.position.x = center.x;
  grid.position.z = center.z;
}
function setShading(mode) {
  renderer.shadowMap.needsUpdate = true;
  state.mode = mode;
  document.querySelectorAll('[data-mode]').forEach(b => b.classList.toggle('active', b.dataset.mode === mode));
  if (model) model.traverse(o => {
    if (! o.isMesh) return;
    if (o.userData.displayMaterials) {
      const old = Array.isArray(o.material) ? o.material: [o.material];
      old.forEach(m => m.dispose());
      o.material = o.userData.displayMaterials;
      delete o.userData.displayMaterials;
    }
    if (mode === 'wireframe' || mode === 'solid') {
      o.userData.displayMaterials = o.material;
      const mat = new THREE.MeshStandardMaterial({
        color: mode === 'solid' ? 0xb0b7bd: 0xc4d0d6,
        roughness: .8,
        metalness: 0,
        wireframe: mode === 'wireframe',
        side: THREE.DoubleSide
      });
      o.material = mat;
    }
  });
  const rendered = mode === 'rendered';
  sun.intensity = rendered ? 4: 2.1;
  ambient.intensity = rendered ? 2.2: 2.8;
  sun.castShadow = rendered && $('shadows').checked;
  ground.material.color.set(rendered ? '#707770': '#303942');
  world.background.set(rendered ? '#89949a': '#303942');
  world.environmentIntensity = mode === 'material' ? 1.5: 1;
  renderer.toneMappingExposure = Number($('exposure').value);
}
async function api(path, payload) {
  const res = await fetch(path, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Studio-Token': state.config.token
    },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (! res.ok) throw new Error(data.message || 'Request failed');
  return data;
}
function setBusy(busy, button) {
  state.busy = busy;
  for (const id of['generate', 'demo', 'multi-demo', 'render', 'export-glb', 'export-blend', 'open']) $(id).disabled = busy;
  $('empty-demo').disabled = busy;
  document.querySelectorAll('button.busy').forEach(b => b.classList.remove('busy'));
  if (busy && button) button.classList.add('busy');
}
async function job(kind, payload, button) {
  if (state.busy) return null;
  setBusy(true, button);
  try {
    const created = await api('/api/' + kind, payload);
    let result;
    for (; ; ) {
      await new Promise(r => setTimeout(r, 1300));
      const response = await fetch('/api/jobs/' + created.id);
      result = await response.json();
      $('status').textContent = result.message || result.status;
      if (['complete', 'failed', 'needs_input'].includes(result.status)) break;
    }
    if (result.status !== 'complete') {
      $('status').textContent = result.status === 'needs_input' ? 'Design needs clarification': 'Generation failed';
      notice(result.message, true, true);
      return null;
    }
    return result;
  } catch (e) {
    notice(e.message, true, true);
    $('status').textContent = 'Action failed';
    return null;
  } finally {
    setBusy(false);
  }
}
function describeScene(packet) {
  const s = state.scene;
  if (! s) return;
  $('design-details').replaceChildren();
  for (const text of[`${s.width.toFixed(2)} × ${s.depth.toFixed(2)} m footprint`, `${s.storeys||1} floors · ${s.rooms.length+(s.upper_floors||[]).reduce((n,f)=>n+f.rooms.length,0)} rooms · ${s.site?.parking?.length||0} parking bays${s.site?.park?' · park':''}${s.site?.pool?' · swimming pool':''}`, ...(packet?.assumptions ||[]), ...(packet?.unsupported ||[]).map(t => 'Unsupported: ' + t)]) {
    const p = document.createElement('p');
    p.textContent = text;
    $('design-details').append(p);
  }
}
async function demo() {
  if (state.busy) return;
  try {
    state.scene = await(await fetch('/api/demo')).json();
    state.edits = {};
    state.history =[];
    state.future =[];
    state.source='example';
    state.base = '/output/example';
    state.view = 'exterior';
    document.querySelectorAll('[data-view]').forEach(b => b.classList.toggle('active', b.dataset.view === 'exterior'));
    describeScene();
    await loadModel();
    state.dirty = false;
    $('dirty').style.color = '#69736b';
  } catch (e) {
    notice(e.message, true);
  }
}
$('generate').onclick = async() => {
  const prompt = $('prompt').value.trim();
  if (! prompt) {
    notice('Describe the building first.', true);
    return;
  }
  if (! state.config.groq) {
    notice('GROQ_API_KEY is missing. Add it to the parent .env and restart the server.', true);
    return;
  }
  const result = await job('design', {
    prompt,
    previous: state.source === 'example' ? null : state.scene
  }, $('generate'));
  if (! result) return;
  state.source='groq';
  state.scene = result.scene;
  state.edits = {};
  state.history =[];
  state.future =[];
  state.base = '/output/' + result.id;
  describeScene(result.packet);
  await loadModel();
  dirty();
  notice(result.packet?.message || 'Your building is ready. Select an object to refine it.');
};
$('demo').onclick = demo;
$('empty-demo').onclick = demo;
$('views').onclick = e => {
  const b = e.target.closest('[data-view]');
  if (! b || ! state.scene || state.busy) return;
  state.view = b.dataset.view;
  state.floor = state.view === 'exterior' ? 'all': state.floor === 'all' ? '0': state.floor;
  document.querySelectorAll('[data-view]').forEach(x => x.classList.toggle('active', x === b));
  loadModel({
    fit: false
  });
};
$('shading').onclick = e => {
  const b = e.target.closest('[data-mode]');
  if (b) setShading(b.dataset.mode);
};
$('tools').addEventListener('click', e => {
  const b = e.target.closest('[data-tool]');
  if (b) setTool(b.dataset.tool);
});
$('search').oninput = drawOutliner;
$('fit').onclick = frameScene;
$('undo').onclick = undo;
$('redo').onclick = redo;
$('reset-object').onclick =() => {
  if (! state.selected) return;
  pushHistory();
  delete state.edits[state.selected.userData.entity];
  refreshHistory();
};
$('color').onchange = e => {
  if (! state.selected) return;
  pushHistory();
  const id = state.selected.userData.entity;
  state.edits[id] = {
    ...(state.edits[id] || {}),
    color: e.target.value
  };
  refreshHistory();
};
$('snap').onchange = e => {
  gizmo.setTranslationSnap(e.target.checked ? .1: null);
  gizmo.setRotationSnap(e.target.checked ? THREE.MathUtils.degToRad(5): null);
  gizmo.setScaleSnap(e.target.checked ? .05: null);
};
$('grid').onchange = e => {
  grid.visible = axes.visible = e.target.checked;
};
$('edges').onchange = rebuildEdges;
$('shadows').onchange =() => setShading(state.mode);
$('exposure').oninput = e => {
  renderer.toneMappingExposure = Number(e.target.value);
  $('exposure-value').textContent = Number(e.target.value).toFixed(2);
};
$('sun').oninput = e => {
  renderer.shadowMap.needsUpdate = true;
  const angle = Number(e.target.value) * Math.PI / 180;
  sun.position.set(controls.target.x + Math.cos(angle) * 20, 22, controls.target.z + Math.sin(angle) * 20);
  $('sun-value').textContent = e.target.value + '°';
};
document.querySelectorAll('[data-camera]').forEach(b => b.onclick =() => {
  if (! model) return;
  const c = controls.target.clone(),
  d = Math.max(state.scene.width, state.scene.depth) * 1.6;
  const positions = {
    top: [0, d, .001],
    front: [0, 2, d],
    right: [d, 2, 0],
    perspective: [d * .7, d * .5, d * .7]
  };
  camera.position.copy(c).add(new THREE.Vector3(... positions[b.dataset.camera]));
  controls.update();
});
function download(data, name, type) {
  const a = document.createElement('a'),
  url = URL.createObjectURL(new Blob([data], {
    type
  }));
  a.href = url;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}
$('save').onclick =() => {
  if (! state.scene) {
    notice('Load or generate a design first.', true);
    return;
  }
  download(JSON.stringify({
    version: 1,
    scene: state.scene,
    edits: state.edits,
    prompt: $('prompt').value
  }, null, 2), 'form-project.json', 'application/json');
  state.dirty = false;
  $('dirty').style.color = '#69736b';
  notice('Project saved, including your object edits.');
};
$('open').onclick =() => $('file').click();
$('file').onchange = async e => {
  const file = e.target.files[0];
  if (! file) return;
  try {
    if (file.size > 2000000) throw new Error('Project file exceeds 2 MB.');
    const p = JSON.parse(await file.text());
    if (p.version !== 1 || ! p.scene) throw new Error('Unsupported project file.');
    const result = await job('build', {
      scene: p.scene,
      edits: p.edits || {}
    }, $('open'));
    if (result) {
      state.source='project';
      state.scene = result.scene;
      state.edits = result.edits;
      state.history =[];
      state.future =[];
      state.base = '/output/' + result.id;
      if (typeof p.prompt === 'string') $('prompt').value = p.prompt;
      describeScene();
      await loadModel();
      notice('Project restored.');
    }
  } catch (e) {
    notice(e.message, true);
  } finally {
    $('file').value = '';
  }
};
async function exportProject(extension) {
  if (! state.scene) {
    notice('Load or generate a design first.', true);
    return;
  }
  const result = await job('build', {
    scene: state.scene,
    edits: state.edits
  }, $(extension === 'glb' ? 'export-glb': 'export-blend'));
  if (result) {
    const a = document.createElement('a');
    a.href = `/output/${result.id}/${extension==='glb'?state.view+'.glb':'design.blend'}`;
    a.download = extension === 'glb' ? `residence-${state.view}.glb`: 'residence.blend';
    a.click();
    notice('Export includes current object edits.');
  }
}
$('export-glb').onclick =() => exportProject('glb');
$('export-blend').onclick =() => exportProject('blend');
$('screenshot').onclick =() => {
  gizmo.getHelper().visible = false;
  selectionBox.visible = false;
  renderer.render(world, camera);
  const a = document.createElement('a');
  a.href = renderer.domElement.toDataURL('image/png');
  a.download = 'form-viewport.png';
  a.click();
  gizmo.getHelper().visible = true;
  updateSelectionBox();
};
$('render').onclick = async() => {
  if (! state.scene) {
    notice('Load or generate a design first.', true);
    return;
  }
  notice('Rendering a 1200 × 900 image in Blender Cycles. This can take a few minutes.', false, true);
  const result = await job('render', {
    scene: state.scene,
    edits: state.edits,
    view: state.view,
    presentation: {
      floor: state.floor,
      camera: camera.position.toArray(),
      target: controls.target.toArray(),
      sun: sun.position.toArray(),
      exposure: Number($('exposure').value)
    }
  }, $('render'));
  if (result) {
    $('notice').hidden = true;
    $('render-image').src = result.render;
    $('download-render').href = result.render;
    $('render-dialog').showModal();
  }
};
$('close-dialog').onclick =() => $('render-dialog').close();
window.addEventListener('keydown', e => {
  if (['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName) || $('render-dialog').open) return;
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
    e.preventDefault();
    e.shiftKey ? redo(): undo();
    return;
  }
  if (e.key === 'Escape') {
    select(null);
    setTool('select');
  }
  const tools = {
    q: 'select',
    g: 'translate',
    r: 'rotate',
    s: 'scale'
  };
  if (tools[e.key.toLowerCase()]) {
    e.preventDefault();
    setTool(tools[e.key.toLowerCase()]);
  }
  if (e.key.toLowerCase() === 'f') frameScene();
});
window.addEventListener('beforeunload', e => {
  if (state.dirty) {
    e.preventDefault();
    e.returnValue = '';
  }
});
new ResizeObserver(() => {
  const w = viewport.clientWidth,
  h = viewport.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}).observe(viewport);
let lastFrame = 0;
renderer.setAnimationLoop(time => {
  if (time - lastFrame < 1000 / 30) return;
  lastFrame = time;
  controls.update();
  if (state.selected) updateSelectionBox();
  if (edgeGroup?.visible && model) {
    let i = 0;
    model.traverse(o => {
      if (o.isMesh && edgeGroup.children[i]) {
        o.updateWorldMatrix(true, false);
        edgeGroup.children[i].visible = editable(o)?.visible !== false;
        edgeGroup.children[i ++].matrix.copy(o.matrixWorld);
      }
    });
  }
  renderer.render(world, camera);
});
try {
  state.config = await(await fetch('/api/config')).json();
  $('connection').textContent = `${state.config.groq?'● Groq key loaded':'○ Groq key missing'} · ${state.config.blender?'Blender ready':'Blender missing'}`;
  await demo();
} catch (e) {
  notice('Local backend unavailable: ' + e.message, true, true);
}

$('multi-demo').onclick = async () => {
  if(state.busy) return;
  try {
    const response = await fetch('/api/examples/four-storey');
    if(!response.ok) throw new Error('Restart the updated server to load the multi-storey example.');
    const sample = await response.json();
    let base = sample.model_base;
    if(!base) {
      const result = await job('build', {scene: sample.scene, edits: {}}, $('multi-demo'));
      if(!result) return;
      base = '/output/' + result.id;
    }
    state.source = 'example';
    state.scene = sample.scene;
    state.edits = {};
    state.history = [];
    state.future = [];
    state.base = base;
    state.view = 'exterior';
    state.floor = 'all';
    document.querySelectorAll('[data-view]').forEach(button => button.classList.toggle('active',button.dataset.view==='exterior'));
    describeScene();
    await loadModel();
    state.dirty = false;
    notice('Four-floor example: stairs, lift, gym, 8 parking bays and park. No Groq call.');
  } catch(error) { notice(error.message, true); }
};
