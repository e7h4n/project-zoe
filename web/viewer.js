import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const host = document.querySelector('#model-viewer');
const canvas = document.querySelector('#model-canvas');
const status = document.querySelector('#viewer-status');
const resetButton = document.querySelector('#reset-view');
const viewButtons = [...document.querySelectorAll('[data-view]')];
const caption = document.querySelector('#view-caption');
const presets = {
  overall: { text: 'Silver anodized aluminum. A satin finish, considered from every angle.' },
  front: { eye: [0, 700, 58], target: [0, 85, 58], span: 205, text: 'Front elevation. A fixed, level dripper ring above the original continuous weighing surface.' },
  side: { eye: [-600, 85, 58], target: [0, 85, 58], span: 205, text: 'Side elevation. Manual fixed support; no automated head or adjustable arm.' },
  top: { eye: [0, 85, 700], target: [0, 85, 58], span: 205, text: 'From above. The manual ring and recessed carafe seat share center X0 / Y125.' },
  crown: { eye: [-90, 195, 210], target: [0, 115, 116], span: 90, text: 'Fixed manual ring. Nominal outer diameter 60 mm, inner diameter 48 mm.' },
  crownUnderside: { eye: [-90, 210, 45], target: [0, 115, 114], span: 90, text: 'Level ring underside. Nominal seat-to-ring clearance 109 mm; dripper outlet clearance unverified.' },
  upperBend: { eye: [-110, 120, 165], target: [0, 35, 113], span: 100, text: 'The fixed upper support replaces the historical automated crown and adjustable arm.' },
  surface: { eye: [-155, 315, 220], target: [0, 96, 13], span: 205, text: 'Original continuous weighing surface and Ø85 mm seat, recessed 0.5 mm.' },
  rear: { eye: [-125, 235, 145], target: [0, 12, 12], span: 90, text: 'Original rear base joint retained, with clearance around the upright root.' },
  edge: { eye: [-135, 270, 65], target: [-30, 150, 1], span: 65, text: 'Outer skirt extended downward to conceal the new inset ground plate. Nominal table gap 0.5 mm, not load-validated.' },
  underside: { eye: [-155, 315, -220], target: [0, 85, 0], span: 205, text: 'Three-layer serial concept: cover C, integrated floor/upright M, inset ground plate G. Sensors are not installed.' },
  rearUnderside: { eye: [-125, 180, -130], target: [0, 17, 0], span: 100, text: 'Shortened ground plate: 94.4 × 156.4 × 2 mm, R5.2. Rear straight-edge gap to the middle layer is nominally 0.8 mm; front and side gaps also 0.8 mm.' },
};
let renderer;
let controls;
let environment;
let frame;
let ready = false;

function fail(error) {
  ready = false;
  host.dataset.state = 'error';
  resetButton.disabled = true;
  viewButtons.forEach(button => { button.disabled = true; });
  status.hidden = false;
  status.replaceChildren(document.createTextNode('3D view unavailable. '));
  const link = document.createElement('a');
  link.href = host.dataset.model;
  link.download = 'project-zoe.glb';
  link.textContent = 'Download the GLB model';
  status.append(link);
  console.error('Project Zoe viewer:', error);
}

async function init() {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, powerPreference: 'low-power' });
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.05;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, .01, 100);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  environment = pmrem.fromScene(room, .04);
  scene.environment = environment.texture;
  scene.environmentIntensity = 1.05;
  room.dispose();
  pmrem.dispose();

  scene.add(new THREE.HemisphereLight(0xffffff, 0xbabbb7, 1.3));
  const key = new THREE.DirectionalLight(0xffffff, 2.8);
  key.position.set(-3, 7, -4);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.left = key.shadow.camera.bottom = -4;
  key.shadow.camera.right = key.shadow.camera.top = 4;
  key.shadow.camera.near = .1;
  key.shadow.camera.far = 20;
  key.shadow.bias = -.0002;
  key.shadow.normalBias = .015;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xffffff, 1.1);
  fill.position.set(4, 3, 2);
  scene.add(fill);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(12, 12), new THREE.ShadowMaterial({ opacity: .12 }));
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -1.505;
  floor.receiveShadow = true;
  scene.add(floor);

  controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true;
  controls.dampingFactor = .09;
  controls.rotateSpeed = .7;
  controls.panSpeed = .8;
  controls.zoomSpeed = .8;
  controls.screenSpacePanning = true;
  controls.minDistance = .3;
  controls.maxDistance = 24;
  controls.minPolarAngle = .01;
  controls.maxPolarAngle = Math.PI - .01;
  controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
  controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
  controls.listenToKeyEvents(canvas);
  const homeDirection = new THREE.Vector3(-4.2, 2.7, -5.38).normalize();
  let homeDistance = 8;
  let activeView = 'overall';
  let transition;
  let toDisplay;
  let displayScale;
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

  function invalidate() {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = undefined;
      if (transition) {
        const t = Math.min(1, (performance.now() - transition.started) / 550);
        const eased = t * t * (3 - 2 * t);
        camera.position.lerpVectors(transition.fromPosition, transition.position, eased);
        controls.target.lerpVectors(transition.fromTarget, transition.target, eased);
        if (t === 1) { transition = undefined; controls.enableDamping = true; }
      }
      controls.update();
      renderer.render(scene, camera);
      if (transition) invalidate();
    });
  }
  controls.addEventListener('change', invalidate);
  function selectView(id, animate = true) {
    const preset = presets[id];
    if (!preset || !ready) return;
    transition = undefined;
    controls.enableDamping = false;
    controls.update(); // Drain previous damping before capturing the transition.
    const target = id === 'overall' ? new THREE.Vector3() : toDisplay(preset.target);
    let position;
    if (id === 'overall') position = homeDirection.clone().multiplyScalar(homeDistance);
    else {
      const direction = toDisplay(preset.eye).sub(target).normalize();
      const distance = preset.span * .001 * displayScale * Math.max(1, 1 / camera.aspect)
        / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
      position = target.clone().addScaledVector(direction, distance);
    }
    activeView = id;
    host.dataset.view = id;
    floor.visible = !['underside', 'rearUnderside', 'crownUnderside'].includes(id);
    viewButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.view === id)));
    caption.textContent = preset.text;
    camera.zoom = 1;
    camera.updateProjectionMatrix();
    if (animate && !reducedMotion.matches) {
      transition = { started: performance.now(), fromPosition: camera.position.clone(),
        fromTarget: controls.target.clone(), position, target };
    } else {
      camera.position.copy(position);
      controls.target.copy(target);
      controls.update();
      controls.enableDamping = true;
    }
    invalidate();
  }
  function resetView() { selectView('overall'); }
  controls.addEventListener('start', () => {
    transition = undefined;
    controls.enableDamping = true;
    activeView = null;
    host.dataset.view = 'custom';
    viewButtons.forEach(button => button.setAttribute('aria-pressed', 'false'));
    caption.textContent = 'Free view. Rotate, pan or zoom to explore; choose a detail to return to it.';
    // No ground-plane occlusion when freely inspecting the underside.
    floor.visible = false;
  });
  function resize() {
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    const oldHome = homeDistance;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    // A model normalized to a 3-unit maximum extent, with framing margin.
    homeDistance = Math.max(4.1, 2.65 / camera.aspect) / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    if (ready && activeView) selectView(activeView, false);
    else if (ready) camera.position.sub(controls.target).multiplyScalar(homeDistance / oldHome).add(controls.target);
    else camera.position.copy(homeDirection).multiplyScalar(homeDistance);
    controls.update();
    invalidate();
  }
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  resize();
  resetButton.addEventListener('click', resetView);
  viewButtons.forEach(button => button.addEventListener('click', () => selectView(button.dataset.view)));
  canvas.addEventListener('contextmenu', event => event.preventDefault());
  canvas.addEventListener('pointerdown', () => canvas.focus({ preventScroll: true }));
  canvas.addEventListener('keydown', event => {
    if (!ready) return;
    if (event.key.toLowerCase() === 'r' || event.key === 'Home') {
      event.preventDefault();
      resetView();
    } else if (['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown'].includes(event.key)) {
      transition = undefined;
      controls.enableDamping = true;
      activeView = null;
      host.dataset.view = 'custom';
      viewButtons.forEach(button => button.setAttribute('aria-pressed', 'false'));
      caption.textContent = 'Free view. Choose a detail to return to it.';
    } else if (['+', '=', '-', '_'].includes(event.key)) {
      event.preventDefault();
      transition = undefined;
      controls.enableDamping = true;
      activeView = null;
      host.dataset.view = 'custom';
      viewButtons.forEach(button => button.setAttribute('aria-pressed', 'false'));
      caption.textContent = 'Free view. Choose a detail to return to it.';
      const distance = camera.position.distanceTo(controls.target);
      const desired = THREE.MathUtils.clamp(distance * (['+', '='].includes(event.key) ? .88 : 1.14), controls.minDistance, controls.maxDistance);
      camera.position.sub(controls.target).multiplyScalar(desired / distance).add(controls.target);
      controls.update();
      invalidate();
    }
  });
  canvas.addEventListener('webglcontextlost', event => {
    event.preventDefault();
    fail(new Error('WebGL context lost; reload the page to restore the viewer.'));
  });

  const draco = new DRACOLoader();
  draco.setDecoderPath(new URL(host.dataset.draco, document.baseURI).href);
  draco.setDecoderConfig({ type: 'wasm' });
  draco.setWorkerLimit(2);
  const loader = new GLTFLoader().setDRACOLoader(draco);
  let gltf;
  try { gltf = await loader.loadAsync(host.dataset.model); }
  finally { draco.dispose(); }
  const bounds = new THREE.Box3().setFromObject(gltf.scene);
  const size = bounds.getSize(new THREE.Vector3());
  const center = bounds.getCenter(new THREE.Vector3());
  if (!Number.isFinite(size.y) || size.y <= 0) throw new Error('The GLB has invalid bounds');
  // Normalize display only: the downloadable GLB retains true meter units.
  gltf.scene.position.sub(center);
  displayScale = 3 / Math.max(size.x, size.y, size.z);
  floor.position.y = -size.y * displayScale / 2 - .005;
  toDisplay = ([x, y, z]) => new THREE.Vector3(x * .001, z * .001, -y * .001).sub(center).multiplyScalar(displayScale);
  const model = new THREE.Group();
  model.add(gltf.scene);
  model.scale.setScalar(displayScale);
  model.traverse(obj => {
    if (obj.isMesh) {
      // A restrained base-contact shadow avoids distracting projected arm silhouettes.
      obj.castShadow = obj.name === 'weighed_base';
      obj.receiveShadow = false;
    }
  });
  scene.add(model);
  ready = true;
  host.dataset.state = 'ready';
  host.dataset.meshes = String(gltf.scene.getObjectsByProperty('isMesh', true).length);
  resetButton.disabled = false;
  viewButtons.forEach(button => { button.disabled = false; });
  status.hidden = true;
  selectView('overall', false);
  // Small public integration API, also useful for reproducible interaction QA.
  window.projectZoe = {
    resetView,
    selectView,
    getView: () => ({
      preset: activeView, transitioning: Boolean(transition),
      finish: { name: 'Silver anodized aluminum',
        materials: [...new Set(gltf.scene.getObjectsByProperty('isMesh', true).flatMap(obj => Array.isArray(obj.material) ? obj.material : [obj.material]))]
          .map(material => ({ metallic: material.metalness, roughness: material.roughness })) },
      position: camera.position.toArray(), target: controls.target.toArray(),
      distance: camera.position.distanceTo(controls.target), dimensionsMeters: size.toArray(),
      meshes: Number(host.dataset.meshes),
    }),
  };
  window.addEventListener('pagehide', () => {
    observer.disconnect();
    controls.dispose();
    environment.dispose();
    renderer.dispose();
    if (frame) cancelAnimationFrame(frame);
  }, { once: true });
}

init().catch(fail);
