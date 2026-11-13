import { build } from 'esbuild';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { readFile, writeFile, rm, mkdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = path.join(root, 'dist');
await rm(out, { recursive: true, force: true });
const python = process.env.PYTHON || 'python3';
function run(args) {
  const child = spawnSync(python, args, { cwd: root, stdio: 'inherit' });
  if (child.error) throw child.error;
  if (child.status !== 0) throw new Error(`${python} ${args.join(' ')} failed (${child.status})`);
}
run(['scripts/export_glb.py', '--out', out]);
const manifestFile = path.join(out, 'model-manifest.json');
const manifest = JSON.parse(await readFile(manifestFile, 'utf8'));
const bundled = await build({
  entryPoints: [path.join(root, 'web/viewer.js')], bundle: true, minify: true,
  write: false, format: 'esm', target: ['es2022'], legalComments: 'eof',
});
const bytes = bundled.outputFiles[0].contents;
const digest = createHash('sha256').update(bytes).digest('hex');
const viewerPath = `assets/viewer-${digest.slice(0, 10)}.js`;
await writeFile(path.join(out, viewerPath), bytes);
manifest.viewer = { path: viewerPath, sha256: digest };
// Self-host both decoder files; the browser never contacts a model/CDN service.
const decoderNames = ['draco_wasm_wrapper.js', 'draco_decoder.wasm'];
const decoderBytes = await Promise.all(decoderNames.map(name => readFile(path.join(root, 'node_modules/three/examples/jsm/libs/draco/gltf', name))));
const decoderHash = createHash('sha256');
for (const bytes of decoderBytes) decoderHash.update(bytes);
const decoderFolder = `assets/draco-${decoderHash.digest('hex').slice(0, 10)}/`;
await mkdir(path.join(out, decoderFolder), { recursive: true });
manifest.draco = { base_path: decoderFolder, files: [] };
for (let i = 0; i < decoderNames.length; i++) {
  const filePath = `${decoderFolder}${decoderNames[i]}`;
  await writeFile(path.join(out, filePath), decoderBytes[i]);
  manifest.draco.files.push({ path: filePath, sha256: createHash('sha256').update(decoderBytes[i]).digest('hex') });
}
manifest.build_script_sha256 = createHash('sha256').update(await readFile(fileURLToPath(import.meta.url))).digest('hex');
manifest.package_lock_sha256 = createHash('sha256').update(await readFile(path.join(root, 'package-lock.json'))).digest('hex');
let html = await readFile(path.join(root, 'web/index.html'), 'utf8');
html = html.replaceAll('{{glb}}', manifest.glb.path).replaceAll('{{viewer}}', viewerPath).replaceAll('{{draco}}', decoderFolder);
if (/\{\{/.test(html)) throw new Error('Unresolved HTML template');
await writeFile(path.join(out, 'index.html'), html);
await writeFile(path.join(out, '.nojekyll'), '');
await writeFile(path.join(out, 'THIRD_PARTY_NOTICES.txt'), await readFile(path.join(root, 'THIRD_PARTY_NOTICES.txt')));
await writeFile(manifestFile, `${JSON.stringify(manifest, null, 2)}\n`);
run(['scripts/check_site.py', out]);
console.log(`Built interactive GLB site in ${out}`);
