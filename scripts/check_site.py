"""Validate the built GLB, local website links and source/output provenance."""
import hashlib
import json
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = set()

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        for key in ('src', 'href', 'data-model'):
            if attrs.get(key) and not attrs[key].startswith('data:'):
                self.references.add(attrs[key])


if __name__ == '__main__':
    output = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'dist').resolve()
    html = (output / 'index.html').read_text()
    assert '{{' not in html
    parser = References()
    parser.feed(html)
    manifest = json.loads((output / 'model-manifest.json').read_text())
    assert manifest['model_sha256'] == sha(ROOT / manifest['model'])
    assert manifest['export_script_sha256'] == sha(ROOT / 'scripts/export_glb.py')
    assert manifest['build_script_sha256'] == sha(ROOT / 'scripts/build_site.mjs')
    assert manifest['package_lock_sha256'] == sha(ROOT / 'package-lock.json')
    paths = {manifest[k]['path'] for k in ('glb', 'viewer')}
    assert parser.references == paths, f'Unexpected website asset references: {parser.references}'
    for kind in ('glb', 'viewer'):
        item = manifest[kind]
        path = (output / item['path']).resolve()
        assert path.is_relative_to(output) and path.is_file()
        assert sha(path) == item['sha256']
        assert item['sha256'][:10] in path.name
        assert path.stat().st_size > 1000
    for item in manifest['draco']['files']:
        path = (output / item['path']).resolve()
        assert path.is_relative_to(output) and path.is_file()
        assert sha(path) == item['sha256']
    assert manifest['draco']['base_path'] in html
    content = (output / manifest['glb']['path']).read_bytes()
    magic, version, total = struct.unpack_from('<4sII', content)
    assert magic == b'glTF' and version == 2 and total == len(content)
    chunk_size, chunk_type = struct.unpack_from('<I4s', content, 12)
    assert chunk_type == b'JSON'
    gltf = json.loads(content[20:20+chunk_size])
    assert len(gltf['meshes']) == 3, 'Export must contain exactly the three product meshes'
    assert len(gltf['nodes']) == 3, 'Do not export studio/accessory objects'
    assert {n['name'] for n in gltf['nodes']} == set(manifest['glb']['objects'])
    assert 'KHR_draco_mesh_compression' in gltf.get('extensionsRequired', [])
    assert not any(gltf.get(key) for key in ('cameras', 'animations', 'images', 'textures'))
    assert not any(buffer.get('uri') for buffer in gltf['buffers']), 'GLB must be self-contained'
    assert manifest['finish']['name'] == 'Silver anodized aluminum'
    for material in gltf['materials']:
        pbr = material['pbrMetallicRoughness']
        assert pbr.get('metallicFactor', 1) == 1
        assert abs(pbr['roughnessFactor'] - .32) < 1e-5
        assert all(abs(a-b) < 1e-5 for a, b in zip(pbr['baseColorFactor'], [.62, .65, .69, 1]))
    for mesh in gltf['meshes']:
        for primitive in mesh['primitives']:
            assert primitive['attributes'].get('POSITION') is not None
            assert primitive['attributes'].get('NORMAL') is not None
    print(f'PASS: self-contained GLB ({len(content):,} bytes), 3 meshes, local JS, source and asset hashes verified.')
