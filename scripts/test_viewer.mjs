import { chromium } from '@playwright/test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dist = path.join(root, 'dist');
const types = { '.html': 'text/html', '.js': 'text/javascript', '.glb': 'model/gltf-binary', '.json': 'application/json', '.wasm': 'application/wasm' };
const server = createServer(async (req, res) => {
  try {
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const file = path.resolve(dist, `.${pathname === '/' ? '/index.html' : pathname}`);
    if (!file.startsWith(`${dist}${path.sep}`)) throw new Error('Invalid path');
    const bytes = await readFile(file);
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
    res.end(bytes);
  } catch { res.writeHead(404); res.end('Not found'); }
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const url = `http://127.0.0.1:${server.address().port}/`;
const browser = await chromium.launch({ executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || undefined, args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const errors = [];
const view = page => page.evaluate(() => window.projectZoe.getView());
const delta = (a, b) => Math.hypot(...a.map((n, i) => n - b[i]));
async function settle(page) {
  await page.evaluate(async () => {
    let previous = window.projectZoe.getView();
    let stable = 0;
    for (let i = 0; i < 300; i++) {
      await new Promise(requestAnimationFrame);
      const current = window.projectZoe.getView();
      const change = Math.max(...current.position.map((n, k) => Math.abs(n - previous.position[k])), ...current.target.map((n, k) => Math.abs(n - previous.target[k])));
      stable = change < 1e-6 && !current.transitioning ? stable + 1 : 0;
      if (stable >= 5) return;
      previous = current;
    }
    throw new Error('Orbit controls did not settle');
  });
}
async function open(context) {
  const page = await context.newPage();
  page.on('pageerror', error => errors.push(error.message));
  page.on('console', msg => { if (msg.type() === 'error') errors.push(msg.text()); });
  await page.goto(url);
  await page.waitForFunction(() => document.querySelector('#model-viewer').dataset.state === 'ready' && window.projectZoe);
  await settle(page);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  return page;
}
async function checkPresets(page, prefix) {
  const ids = ['overall', 'front', 'side', 'top', 'crown', 'crownUnderside', 'upperBend', 'surface', 'rear', 'edge', 'underside', 'rearUnderside'];
  assert.equal(await page.locator('button[data-view]').count(), ids.length);
  const positions = [];
  for (const id of ids) {
    const button = page.locator(`button[data-view="${id}"]`);
    await button.click();
    await settle(page);
    const current = await view(page);
    assert.equal(current.preset, id);
    assert.equal(await button.getAttribute('aria-pressed'), 'true');
    assert.equal(await page.locator('[data-view][aria-pressed="true"]').count(), 1);
    assert.equal(current.transitioning, false);
    assert(current.distance > .3 && current.distance < 24);
    assert([...current.position, ...current.target].every(Number.isFinite), 'Preset camera must be finite');
    for (const previous of positions) assert(delta(previous, current.position) > .01, 'Each preset must offer a distinct angle');
    positions.push(current.position);
    await page.screenshot({ path: path.join(root, `test-results/${prefix}-${id}.png`), fullPage: true });
  }
  await page.getByRole('button', { name: 'Reset view' }).click();
  await settle(page);
  assert.equal((await view(page)).preset, 'overall');
}
await mkdir(path.join(root, 'test-results'), { recursive: true });
try {
  const desktop = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await open(desktop);
  const initial = await view(page);
  assert.equal(initial.meshes, 3);
  assert.equal(initial.finish.name, 'Silver anodized aluminum');
  for (const material of initial.finish.materials) {
    assert.equal(material.metallic, 1, 'Export must retain metallic aluminum');
    assert(Math.abs(material.roughness - .32) < 1e-5, 'Aluminum must have the specified satin roughness');
  }
  assert(initial.dimensionsMeters[0] > .099 && initial.dimensionsMeters[0] < .101, 'GLB width must be 100mm in meter units');
  assert(initial.dimensionsMeters[1] > .1179 && initial.dimensionsMeters[1] < .1181, 'GLB height must be approx. 118mm after all undersides align at Z0.5');
  assert(initial.dimensionsMeters[2] > .169 && initial.dimensionsMeters[2] < .171, 'GLB depth must be 170mm');
  await page.screenshot({ path: path.join(root, 'test-results/desktop.png') });
  const rect = await page.locator('canvas').boundingBox();
  const x = rect.x + rect.width / 2, y = rect.y + rect.height / 2;
  await page.mouse.move(x, y);
  await page.mouse.down({ button: 'left' });
  await page.mouse.move(x + 110, y + 45, { steps: 12 });
  await page.mouse.up({ button: 'left' });
  await settle(page);
  const rotated = await view(page);
  assert(delta(initial.position, rotated.position) > .2, 'Left drag must rotate the camera');
  assert(delta(initial.target, rotated.target) < 1e-7, 'Rotation must not pan');
  await page.screenshot({ path: path.join(root, 'test-results/rotated.png') });
  await page.mouse.move(x, y);
  await page.mouse.down({ button: 'right' });
  await page.mouse.move(x + 80, y + 30, { steps: 12 });
  await page.mouse.up({ button: 'right' });
  await settle(page);
  const panned = await view(page);
  assert(delta(rotated.target, panned.target) > .03, 'Right drag must pan');
  assert(Math.abs(rotated.distance - panned.distance) < 1e-5, 'Pan must preserve zoom');
  await page.mouse.move(x, y);
  await page.mouse.wheel(0, -300);
  await settle(page);
  assert((await view(page)).distance < panned.distance, 'Wheel up must zoom in');
  await page.getByRole('button', { name: 'Reset view' }).click();
  await settle(page);
  let reset = await view(page);
  assert(delta(reset.position, initial.position) < 1e-5 && delta(reset.target, initial.target) < 1e-5, 'Reset must restore the initial view');
  await page.locator('canvas').focus();
  await page.keyboard.press('+');
  await settle(page);
  assert((await view(page)).distance < initial.distance, 'Keyboard + must zoom');
  await page.keyboard.press('r');
  await settle(page);
  reset = await view(page);
  assert(delta(reset.position, initial.position) < 1e-5, 'Keyboard R must reset');
  assert.equal(await page.locator('canvas').evaluate(c => c.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true }))), false);
  await checkPresets(page, 'desktop');
  // Fast switching must stop the previous camera transition and preserve the latest selection.
  await page.locator('[data-view="edge"]').click();
  await page.locator('[data-view="underside"]').click();
  await settle(page);
  assert.equal((await view(page)).preset, 'underside');
  await page.setViewportSize({ width: 1000, height: 760 });
  await settle(page);
  assert.equal((await view(page)).preset, 'underside', 'Resizing must preserve the selected detail');
  await desktop.close();

  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 });
  const touchPage = await open(mobile);
  const mobileInitial = await view(touchPage);
  await touchPage.screenshot({ path: path.join(root, 'test-results/mobile.png'), fullPage: true });
  const touchRect = await touchPage.locator('canvas').boundingBox();
  const tx = touchRect.x + touchRect.width / 2, ty = touchRect.y + touchRect.height / 2;
  const cdp = await mobile.newCDPSession(touchPage);
  const send = (type, points) => cdp.send('Input.dispatchTouchEvent', { type, touchPoints: points });
  await send('touchStart', [{ x: tx, y: ty, id: 1 }]);
  for (let i = 1; i <= 10; i++) await send('touchMove', [{ x: tx + i * 7, y: ty + i * 2, id: 1 }]);
  await send('touchEnd', []);
  await settle(touchPage);
  assert(delta((await view(touchPage)).position, mobileInitial.position) > .1, 'One finger must rotate');
  const beforePinch = await view(touchPage);
  await send('touchStart', [{ x: tx - 45, y: ty, id: 1 }, { x: tx + 45, y: ty, id: 2 }]);
  for (let i = 1; i <= 10; i++) await send('touchMove', [{ x: tx - 45 - i * 3, y: ty + i * 2, id: 1 }, { x: tx + 45 + i * 3, y: ty + i * 2, id: 2 }]);
  await send('touchEnd', []);
  await settle(touchPage);
  const pinched = await view(touchPage);
  assert(pinched.distance < beforePinch.distance, 'Two-finger pinch must zoom');
  assert(delta(pinched.target, beforePinch.target) > .01, 'Two-finger movement must pan');
  await checkPresets(touchPage, 'mobile');
  await touchPage.emulateMedia({ reducedMotion: 'reduce' });
  await touchPage.locator('[data-view="rear"]').click();
  assert.equal((await view(touchPage)).transitioning, false, 'Reduced motion must skip transitions');
  await touchPage.setViewportSize({ width: 320, height: 740 });
  await settle(touchPage);
  assert.equal(await touchPage.evaluate(() => document.documentElement.scrollWidth > innerWidth), false);
  await touchPage.screenshot({ path: path.join(root, 'test-results/mobile-narrow.png'), fullPage: true });
  await mobile.close();
  assert.deepEqual(errors, [], 'No browser errors expected');
  console.log('PASS: silver PBR finish, GLB units, mouse/keyboard/touch controls, all twelve desktop/mobile detail views, rapid switching, responsive resize and reduced motion.');
} finally {
  await browser.close();
  await new Promise(resolve => server.close(resolve));
}
