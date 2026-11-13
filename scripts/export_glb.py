"""Export only the product assembly as a white-clay GLB; never modify the .blend."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import bpy
from mathutils import Matrix

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_OBJECTS = ('BrewDuo_C_shell_5mm', 'Triangular_pyramid_arm_flat_face_UP', 'weighed_base')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output):
    source = ROOT / 'model/project-zoe.blend'
    assets = output / 'assets'
    assets.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.use_scripts_auto_execute = False
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    bpy.ops.object.select_all(action='DESELECT')
    white = bpy.data.materials.new('Project Zoe white clay')
    white.use_nodes = True
    shader = white.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (.82, .81, .79, 1)
    shader.inputs['Metallic'].default_value = 0
    shader.inputs['Roughness'].default_value = .48
    for name in PRODUCT_OBJECTS:
        obj = bpy.data.objects.get(name)
        assert obj and obj.type == 'MESH', f'Missing product mesh: {name}'
        obj.hide_set(False)
        obj.hide_viewport = False
        obj.select_set(True)
        obj.data.materials.clear()
        obj.data.materials.append(white)
        if name == 'weighed_base':
            # The CAD-imported STL has flat triangle normals. Smooth only the
            # display normals; preserve >30-degree creases and all vertices.
            for polygon in obj.data.polygons:
                polygon.use_smooth = True
            obj.data.set_sharp_from_angle(angle=math.radians(30))
        # Source coordinates are mm; glTF uses meters. Explicitly convert the
        # world transform and use a unit scale of 1 to avoid ambiguous units.
        obj.matrix_world = Matrix.Scale(.001, 4) @ obj.matrix_world
    bpy.context.scene.unit_settings.scale_length = 1
    path = assets / 'project-zoe.glb'
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format='GLB', use_selection=True,
        export_apply=True, export_materials='EXPORT', export_normals=True,
        export_yup=True, export_cameras=False, export_lights=False,
        export_animations=False, export_extras=False,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=6,
        export_draco_position_quantization=20,
        export_draco_normal_quantization=12,
    )
    checksum = sha(path)
    name = f'project-zoe-{checksum[:10]}.glb'
    path.replace(assets / name)
    manifest = {
        'model': 'model/project-zoe.blend', 'model_sha256': sha(source),
        'export_script_sha256': sha(Path(__file__)), 'blender': bpy.app.version_string,
        'commit': os.environ.get('GITHUB_SHA'),
        'glb': {'path': f'assets/{name}', 'sha256': checksum, 'units': 'meters',
                'up_axis': 'Y', 'compression': 'KHR_draco_mesh_compression',
                'position_quantization_bits': 20, 'objects': list(PRODUCT_OBJECTS)},
    }
    (output / 'model-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    build(args.out.resolve())
