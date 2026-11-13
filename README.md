# Project Zoe

**The ultimate elegant coffee brewing tool.**

An open-source pour-over stand concept. A circular crown, a dripper support, and a slender base. Explore the real 3D assembly as a clean white model.

[Interactive website](https://e7h4n.github.io/project-zoe/) · [Blender source](model/project-zoe.blend)

![Project Zoe white model](docs/preview.png)

## 3D controls

| Input | Action |
| --- | --- |
| Left mouse drag | Orbit / rotate |
| Right mouse drag | Pan |
| Mouse wheel / middle drag | Zoom |
| One-finger drag | Rotate |
| Two-finger drag / pinch | Pan / zoom |
| Arrow keys (viewer focused) | Pan |
| `+` / `−` (viewer focused) | Zoom |
| `R`, `Home`, or **Reset view** | Restore the initial view |

The viewer uses Three.js and OrbitControls. Context menus are suppressed **only inside the 3D canvas**. It renders on demand, with damping while moving; it does not auto-rotate. Keyboard focus is visible, and the model can be downloaded if WebGL is unavailable.

## Blender → GLB → website CI

Every relevant push to `main`:

1. Opens the actual `model/project-zoe.blend` in headless **Blender 5.0.1**, with automatic script execution disabled.
2. Exports only the three product meshes, applying modifiers and a white-clay material in memory. Cameras, studio lights, floor and accessory proxies are excluded.
3. Converts millimeters to glTF's meter units, uses Y-up, and applies **Draco compression**. Base display normals are smoothed while preserving >30° creases; vertices and original CAD geometry are unchanged. High-precision 20-bit position quantization keeps the small recess transition visually intact.
4. Bundles the viewer and self-hosted Draco decoder, producing content-hashed assets. No CDN, account, project secret or external texture is needed at runtime.
5. Validates the GLB structure, product objects, local assets and source/output hashes.
6. Runs real Chromium tests for dimensions, left-drag rotation, right-drag pan, wheel zoom, reset, keyboard, mobile layout and touch rotate/pan/pinch.
7. Deploys to **GitHub Pages** at <https://e7h4n.github.io/project-zoe/>.

`model-manifest.json` on the live site records the Blender-source hash, export/build scripts, dependency lockfile, commit and exported asset hashes. The full Blender source remains unchanged by export.

Pull requests build and upload an `interactive-website-and-qa` Actions artifact, including the GLB and browser screenshots, but **do not deploy**. Manual builds are available from the Actions tab. Actions are pinned to commit SHAs. Build/test has read-only repository access; deployment has only the additional Pages/OIDC permissions it needs. Failed browser tests block deployment.

The website now loads an actual GLB, not a pre-rendered image. The `.blend` remains the editable source of truth. `docs/preview.png` is a static documentation illustration. The original <https://project-zoe.okou.app> page is a separate historical snapshot, not the automatic CI target.

## Source files

| Path | Contents |
| --- | --- |
| `model/project-zoe.blend` | Complete exterior assembly, original aluminum materials, camera and studio lights. Blender 5.0.1. |
| `cad/base.step` | Engineering solid of the recessed weighing base **only**, not the complete assembly. |
| `cad/base-before-recess.step` | Rounded base before the circular recess. |
| `scripts/build_base.py` | Parametric CadQuery construction of the recessed base. |
| `scripts/export_glb.py` | Headless Blender → compressed GLB export. |
| `scripts/build_site.mjs` | Export, bundle and assemble the static website. |
| `scripts/check_site.py` | GLB, asset and provenance validation. |
| `scripts/test_viewer.mjs` | Real browser mouse, keyboard, touch and responsive tests. |
| `web/` | Responsive page and interactive Three.js viewer. |
| `docs/` | Static previews, section detail and geometric checks. |

The Blender scene uses millimeters. There are no external textures or supplier CAD dependencies. Hidden accessory proxies and unrelated scene objects have been removed from the published model.

## Build locally

Use Python 3.11 and Node.js 22 on Linux. `bpy` is the large headless Blender Python module; no GPU or Blender executable is required to export.

```sh
python3.11 -m venv .venv
. .venv/bin/activate
pip install -r requirements-export.txt
npm ci
npm run build
python -m http.server 8080 --directory dist
```

Open <http://localhost:8080>. Ubuntu may also need `libegl1 libgl1 libxkbcommon0 libxi6 libxrender1`; the workflow installs these explicitly.

To run the browser checks:

```sh
npx playwright install --with-deps chromium
npm test
```

Software WebGL is enabled for headless CI. Tests write desktop, mobile and rotated screenshots to `test-results/`. To test with an existing Chromium executable, set `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`.

### Edit the model

Open `model/project-zoe.blend` in Blender 5.0.1 or newer, edit, save and commit. Preserve the three product object names: `BrewDuo_C_shell_5mm`, `Triangular_pyramid_arm_flat_face_UP`, and `weighed_base`. The next CI build exports the changed geometry and updates the interactive website. The source keeps its aluminum finish; white materials are applied during export only. Camera framing, lighting and controls are in `web/viewer.js`.

## Base geometry

- Overall base: **100 × 170 × 5 mm**; R8 plan corners, nominal R0.35 exposed perimeter edges.
- Circular flat seat: **Ø85 mm**, centered at **X0 / Y125**, coaxial with the dripper support.
- Recess: **0.5 mm** deep; remaining floor thickness **4.5 mm**.
- S transition: two tangent, oppositely curved **R0.25** quarter circles, tangent to both planes. Radial blend width **0.5 mm**, outer transition diameter **Ø86 mm**.
- Rear mating/connection edges are deliberately excluded from exterior edge rounding.

The seat diameter is a user-specified nominal bottom diameter for a HARIO 360 mL server, **not** an independently verified manufacturer dimension. No extra radial fit allowance has been added. HARIO is a third-party trademark; this project is not affiliated with or endorsed by HARIO.

![Radial S-transition section](docs/section.png)

Rebuild the base separately (CadQuery is not needed for website export):

```sh
pip install cadquery==2.8.0
python scripts/build_base.py
```

This updates the base STEP/STL only; it does **not** silently modify the Blender assembly. Replace `weighed_base` in Blender with the resulting STL, preserve material/normals setup, and save before committing to update website geometry.

## Status and safety

**Design concept, not manufacturing-ready hardware.** Weighing internals, electronics, mounting, tolerances, deflection under load, food-contact suitability, thermal behavior, fabrication and physical edge safety have not been engineered or certified. Numeric checks validate the stated exterior geometry, not those functional properties. Use caution with hot water and fragile glassware.

## License

[MIT](LICENSE) for the authored code, model, CAD and artwork. Provided as-is, without warranty. Third-party trademarks are not licensed. Three.js and the Draco decoder retain their respective MIT and Apache-2.0 licenses; see [third-party notices](THIRD_PARTY_NOTICES.txt), also included in the built site.
