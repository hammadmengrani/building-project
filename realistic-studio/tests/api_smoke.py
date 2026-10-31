"""Build once via the running local API; check saved visual edits in exported GLB."""
import json
from pathlib import Path
import struct
import sys
import time
from urllib.request import Request, urlopen
BASE = 'http://127.0.0.1:8504'
ROOT = Path(__file__).resolve().parents[1]

def get(path):
    with urlopen(BASE + path, timeout=20) as r:
        return json.load(r)
config = get('/api/config')
scene = json.loads((ROOT / 'assets/demo.json').read_text())
edits = {'furniture:sofa1': {'position': [1.2, 0.22, -2.6], 'rotation': [0, 0.25, 0], 'scale': [1, 1, 1], 'color': '#387f68'}}
request = Request(BASE + '/api/build', data=json.dumps({'scene': scene, 'edits': edits}).encode(), headers={'Content-Type': 'application/json', 'X-Studio-Token': config['token']}, method='POST')
with urlopen(request, timeout=20) as r:
    job = json.load(r)
print('API build submitted:', job['id'], flush=True)
for _ in range(240):
    result = get('/api/jobs/' + job['id'])
    if result['status'] in ('failed', 'complete'):
        break
    time.sleep(1)
assert result['status'] == 'complete', result
file = ROOT / 'output' / job['id'] / 'exterior.glb'
raw = file.read_bytes()
n = struct.unpack_from('<I', raw, 12)[0]
g = json.loads(raw[20:20 + n])
node = next((n for n in g['nodes'] if n.get('extras', {}).get('entity') == 'furniture:sofa1'))
for a, b in zip(node['translation'], [1.2, 0.22, -2.6]):
    assert abs(a - b) < 1e-05, (node, a, b)
assert 'rotation' in node, node
colors = []
for child in node['children']:
    mesh = g['nodes'][child].get('mesh')
    if mesh is not None:
        for primitive in g['meshes'][mesh]['primitives']:
            material = g['materials'][primitive['material']]['pbrMetallicRoughness']
            assert 'baseColorTexture' not in material
            colors.append(material.get('baseColorFactor'))
assert colors and all((color == colors[0] for color in colors))
assert (file.parent / 'design.blend').stat().st_size > 1000000
print('API_SMOKE_OK: background job, GLB transforms, material override, packed Blender project')
(ROOT / 'output' / 'api-smoke-result.json').write_text(json.dumps({'job': job['id'], 'status': 'passed'}, indent=2))
