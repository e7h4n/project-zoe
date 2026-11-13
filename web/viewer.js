import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';

const host = document.querySelector('#model-viewer');
const canvas = document.querySelector('#model-canvas');
const status = document.querySelector('#viewer-status');
const resetButton = document.querySelector('#reset-view');
let renderer;
let controls;
let environment;
let frame;
let ready = false;

function fail(error) {
  ready = false;
  host.dataset.state = 'error';
  resetButton.disabled = true;
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
  renderer.toneMappingExposure = 1.15;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, 1, .01, 100);
  const pmrem = new THREE.PMREMGenerator(renderer);
  const room = new RoomEnvironment();
  environment = pmrem.fromScene(room, .04);
  scene.environment = environment.texture;
  scene.environmentIntensity = .65;
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
  controls.minDistance = 1.2;
  controls.maxDistance = 24;
  controls.minPolarAngle = .01;
  controls.maxPolarAngle = Math.PI - .01;
  controls.mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN };
  controls.touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN };
  controls.listenToKeyEvents(canvas);
  const homeDirection = new THREE.Vector3(-4.2, 2.7, -5.38).normalize();
  let homeDistance = 8;

  function invalidate() {
    if (frame) return;
    frame = requestAnimationFrame(() => {
      frame = undefined;
      controls.update();
      renderer.render(scene, camera);
    });
  }
  controls.addEventListener('change', invalidate);
  function resetView() {
    // Drain damping deltas before restoring position/target, so reset is exact.
    controls.enableDamping = false;
    controls.reset();
    controls.target.set(0, 0, 0);
    camera.position.copy(homeDirection).multiplyScalar(homeDistance);
    camera.zoom = 1;
    camera.updateProjectionMatrix();
    controls.update();
    controls.saveState();
    controls.enableDamping = true;
    invalidate();
  }
  function resize() {
    const { width, height } = host.getBoundingClientRect();
    if (!width || !height) return;
    const oldHome = homeDistance;
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    renderer.setSize(width, height, false);
    // A 3-unit-high model, with room for its base at narrow aspect ratios.
    homeDistance = Math.max(3.55, 2.25 / camera.aspect) / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)));
    if (ready) camera.position.sub(controls.target).multiplyScalar(homeDistance / oldHome).add(controls.target);
    else camera.position.copy(homeDirection).multiplyScalar(homeDistance);
    controls.update();
    invalidate();
  }
  const observer = new ResizeObserver(resize);
  observer.observe(host);
  resize();
  resetButton.addEventListener('click', resetView);
  canvas.addEventListener('contextmenu', event => event.preventDefault());
  canvas.addEventListener('pointerdown', () => canvas.focus({ preventScroll: true }));
  canvas.addEventListener('keydown', event => {
    if (!ready) return;
    if (event.key.toLowerCase() === 'r' || event.key === 'Home') {
      event.preventDefault();
      resetView();
    } else if (['+', '=', '-', '_'].includes(event.key)) {
      event.preventDefault();
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
  const model = new THREE.Group();
  model.add(gltf.scene);
  model.scale.setScalar(3 / size.y);
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
  status.hidden = true;
  resetView();
  // Small public integration API, also useful for reproducible interaction QA.
  window.projectZoe = {
    resetView,
    getView: () => ({
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
