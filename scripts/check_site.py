"""Check local asset paths and trace every website image back to the .blend."""
import hashlib
import json
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Images(HTMLParser):
    def __init__(self):
        super().__init__()
        self.references = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('img', 'source'):
            for key in ('src', 'srcset'):
                if attrs.get(key):
                    self.references.extend(x.strip().split()[0] for x in attrs[key].split(','))


if __name__ == '__main__':
    output = Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'dist').resolve()
    html = (output / 'index.html').read_text()
    assert '{{white-' not in html
    parser = Images()
    parser.feed(html)
    manifest = json.loads((output / 'render-manifest.json').read_text())
    assert manifest['model_sha256'] == sha(ROOT / manifest['model'])
    assert manifest['render_script_sha256'] == sha(ROOT / 'scripts/render_site.py')
    paths = {item['path'] for item in manifest['images'].values()}
    assert set(parser.references) == paths, 'Website image sources must match rendered assets'
    for item in manifest['images'].values():
        path = (output / item['path']).resolve()
        assert path.is_relative_to(output) and path.is_file()
        assert sha(path) == item['sha256']
        assert item['sha256'][:10] in path.name
        assert path.stat().st_size > 1000
    print('PASS: all website images match the rendered assets and current Blender source.')
