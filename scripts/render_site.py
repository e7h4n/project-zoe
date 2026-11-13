"""Build the website directly from the Blender source, without editing the .blend.
Run using the pinned bpy Python package (headless, no Blender executable needed).
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import bpy
from mathutils import Vector
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output, samples):
    source = ROOT / 'model/project-zoe.blend'
    output.mkdir(parents=True, exist_ok=True)
    assets = output / 'assets'
    assets.mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    scene = bpy.context.scene
    assert scene.camera, 'The source scene needs a camera'
    for name in ('BrewDuo_C_shell_5mm', 'Triangular_pyramid_arm_flat_face_UP', 'weighed_base'):
        assert bpy.data.objects.get(name), f'Missing assembly object: {name}'
    white = bpy.data.materials.new('Render_only_white_clay')
    white.use_nodes = True
    shader = white.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.82, .81, .79, 1)
    shader.inputs['Metallic'].default_value = 0
    shader.inputs['Roughness'].default_value = .48
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and not obj.hide_render and obj.name != 'Studio_ground':
            obj.data.materials.clear()
            obj.data.materials.append(white)
    floor = bpy.data.objects['Studio_ground']
    shader = floor.data.materials[0].node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.69, .68, .65, 1)
    shader.inputs['Roughness'].default_value = .8
    scene.world.node_tree.nodes.get('Background').inputs['Strength'].default_value = .5
    for obj in bpy.data.objects:
        if obj.type == 'LIGHT' and obj.data.type == 'SPOT':
            obj.hide_render = True
    camera = scene.camera
    camera.location = (-420, 610, 430)
    camera.rotation_euler = (Vector((0, 72, 160)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = 435
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.seed = 0
    scene.cycles.use_animated_seed = False
    scene.render.resolution_percentage = 100
    scene.render.resolution_x = 1800
    scene.render.resolution_y = 1600
    scene.render.image_settings.file_format = 'PNG'
    rendered = output / 'model-render.png'
    scene.render.filepath = str(rendered)
    bpy.ops.render.render(write_still=True)
    with Image.open(rendered) as raw:
        portrait = raw.convert('RGB')
    desktop = Image.new('RGB', (2560, 1600))
    desktop.paste(portrait.crop((0, 0, 1, 1600)).resize((760, 1600)), (0, 0))
    desktop.paste(portrait, (760, 0))
    images = {}
    for label, image in [('white-stage', desktop), ('white-portrait', portrait.crop((350, 0, 1350, 1600)))]:
        temp = assets / f'{label}.webp'
        image.save(temp, quality=92, method=6)
        checksum = digest(temp)
        filename = f'{label}-{checksum[:10]}.webp'
        temp.replace(assets / filename)
        images[label] = {'path': f'assets/{filename}', 'sha256': checksum}
    template = (ROOT / 'web/index.html').read_text()
    for label, info in images.items():
        template = template.replace('{{' + label + '}}', info['path'])
    assert '{{white-' not in template, 'Unresolved asset template'
    (output / 'index.html').write_text(template)
    (output / '.nojekyll').touch()
    manifest = {
        'model': 'model/project-zoe.blend', 'model_sha256': digest(source),
        'render_script_sha256': digest(Path(__file__)), 'blender': bpy.app.version_string,
        'samples': samples, 'engine': 'Cycles CPU',
        'commit': os.environ.get('GITHUB_SHA'), 'images': images,
    }
    (output / 'render-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    rendered.unlink()  # The website only needs the two compressed, content-hashed images.
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT / 'dist')
    parser.add_argument('--samples', type=int, default=48)
    args = parser.parse_args()
    if not 1 <= args.samples <= 512:
        parser.error('--samples must be between 1 and 512')
    build(args.out.resolve(), args.samples)
