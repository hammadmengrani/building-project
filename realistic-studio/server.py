"""Local architectural studio. Keys and Blender processes stay on the server."""
import argparse
import copy
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from dotenv import load_dotenv
from schema import Scene
from geometry import validate
from one_shot import design
ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT.parent / '.env')
load_dotenv(ROOT / '.env', override=True)
OUTPUT = ROOT / 'output'
OUTPUT.mkdir(exist_ok=True)
JOBS = {}
LOCK = threading.Lock()
WORKER = threading.Semaphore(1)
TOKEN = secrets.token_urlsafe(32)

def checked_scene(data):
    scene = Scene.model_validate(data).model_dump()
    errors = validate(scene)
    if errors:
        raise ValueError("""Layout validation failed:
""" + """
""".join(errors))
    return scene

def checked_edits(data):
    if not isinstance(data, dict) or len(data) > 2000:
        raise ValueError('Invalid object edits')
    import math
    result = {}
    for key, edit in data.items():
        if not isinstance(key, str) or len(key) > 180 or (not isinstance(edit, dict)):
            raise ValueError('Invalid edit ID')
        item = {}
        for field in ('position', 'rotation', 'scale'):
            values = edit.get(field)
            if values is None:
                continue
            if not isinstance(values, list) or len(values) != 3 or any((type(v) not in (int, float) or not math.isfinite(v) for v in values)):
                raise ValueError('Invalid transform')
            if field == 'scale' and any((v < 0.05 or v > 20 for v in values)):
                raise ValueError('Scale must be .05–20')
            if field != 'scale' and any((abs(v) > 500 for v in values)):
                raise ValueError('Transform out of bounds')
            item[field] = values
        if 'color' in edit:
            if not isinstance(edit['color'], str) or not re.fullmatch('#[0-9a-fA-F]{6}', edit['color']):
                raise ValueError('Invalid material color')
            item['color'] = edit['color']
        result[key] = item
    return result

def job_update(job_id, **kwargs):
    with LOCK:
        JOBS[job_id].update(kwargs)

def run_job(job_id, kind, payload):
    folder = OUTPUT / job_id
    folder.mkdir()
    packet = None
    try:
        with WORKER:
            job_update(job_id, status='running', message='Groq is interpreting the room brief…' if kind == 'design' else 'Blender is preparing the scene…')
            if kind == 'design':
                prompt = payload.get('prompt', '').strip()
                if not prompt or len(prompt) > 10000:
                    raise ValueError('Enter a brief between 1 and 10,000 characters.')
                previous = payload.get('previous')
                if previous is not None:
                    # A failed layout may be explicitly submitted for repair.
                    previous = Scene.model_validate(previous).model_dump()
                reply = design(prompt, previous, bool(previous), os.getenv('GROQ_API_KEY'), os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b'))
                packet = reply.model_dump()
                (folder / 'response.json').write_text(json.dumps(packet, indent=2))
                if not reply.ready or reply.scene is None:
                    job_update(job_id, status='needs_input', message=reply.message, packet=packet)
                    return
                scene = checked_scene(packet['scene'])
            else:
                scene = checked_scene(payload.get('scene'))
                packet = None
            edits = checked_edits(payload.get('edits', {}))
            (folder / 'scene.json').write_text(json.dumps(scene, indent=2))
            (folder / 'edits.json').write_text(json.dumps(edits, indent=2))
            blender = shutil.which('blender')
            if not blender:
                raise ValueError('Blender is not installed or is not on PATH.')
            command = [blender, '--background', '--factory-startup', '--threads', '6', '--python-exit-code', '1', '--python', str(ROOT / 'scripts' / 'building.py'), '--', '--scene', str(folder / 'scene.json'), '--out', str(folder), '--edits', str(folder / 'edits.json')]
            if kind == 'render':
                command.extend(['--render', '--view', payload.get('view', 'exterior') if payload.get('view') in ('exterior', 'interior', 'cutaway') else 'exterior'])
                presentation = payload.get('presentation', {})
                if presentation:
                    import math
                    for field in ('camera', 'target', 'sun'):
                        values = presentation.get(field)
                        if not isinstance(values, list) or len(values) != 3 or any((type(v) not in (int, float) or not math.isfinite(v) or abs(v) > 1000 for v in values)):
                            raise ValueError('Invalid presentation camera or light')
                    exposure = presentation.get('exposure', 1)
                    if type(exposure) not in (float, int) or not 0.1 <= exposure <= 3:
                        raise ValueError('Invalid exposure')
                    (folder / 'presentation.json').write_text(json.dumps(presentation))
                    command.extend(['--presentation', str(folder / 'presentation.json')])
            job_update(job_id, message='Cycles rendering final image…' if kind == 'render' else 'Local layout validated. Building materials and three views…')
            with (folder / 'blender.log').open('w') as log:
                result = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1200 if kind == 'render' else max(240, scene.get('storeys',1)*120))
            if result.returncode:
                raise ValueError('Blender failed. See this job’s blender.log for details.')
            job_update(job_id, status='complete', message='Scene ready', scene=scene, edits=edits, packet=packet, model=f'/output/{job_id}/exterior.glb', render=f'/output/{job_id}/render.png' if kind == 'render' else None)
    except Exception as exc:
        # Provider errors may include request details; do not return SDK dumps or secrets.
        name = type(exc).__name__
        if name in ('RateLimitError', 'APIConnectionError', 'APIStatusError', 'AuthenticationError'):
            message = {'RateLimitError': 'Groq quota/rate limit reached. No automatic retry was sent.', 'APIConnectionError': 'Could not connect to Groq. No automatic retry was sent.', 'AuthenticationError': 'Groq API key was rejected. Check the parent .env.', 'APIStatusError': 'Groq request failed. Check model access and account status.'}[name]
        else:
            message = str(exc)[:5000]
        job_update(job_id, status='failed', message=message, packet=packet)

class Handler(BaseHTTPRequestHandler):

    def send_json(self, data, status=200):
        raw = json.dumps(data).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/config':
            return self.send_json({'token': TOKEN, 'groq': bool(os.getenv('GROQ_API_KEY')), 'blender': bool(shutil.which('blender')), 'model': os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b')})
        if path.startswith('/api/jobs/'):
            with LOCK:
                job = copy.deepcopy(JOBS.get(path.rsplit('/', 1)[-1]))
            return self.send_json(job or {'message': 'Job not found'}, 200 if job else 404)
        if path == '/api/examples/four-storey':
            sample = checked_scene(json.loads((ROOT / 'assets' / 'four-storey-scene.json').read_text()))
            ready = all((OUTPUT / 'four-storey-check' / (mode + '.glb')).exists() for mode in ('exterior','interior','cutaway'))
            return self.send_json({'scene': sample, 'model_base': '/output/four-storey-check' if ready else None})
        if path == '/api/demo':
            return self.send_json(json.loads((ROOT / 'assets' / 'demo.json').read_text()))
        if path.startswith('/output/'):
            base = OUTPUT
            relative = path[len('/output/'):]
        else:
            base = ROOT / 'static'
            relative = path.lstrip('/') or 'index.html'
        file = (base / relative).resolve()
        if not file.is_relative_to(base.resolve()) or not file.is_file():
            return self.send_error(404)
        raw = file.read_bytes()
        self.send_response(200)
        content_type = {'.js': 'text/javascript', '.glb': 'model/gltf-binary'}.get(file.suffix) or mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(raw)))
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        if self.headers.get('X-Studio-Token') != TOKEN:
            return self.send_json({'message': 'Invalid local session'}, 403)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 2000000:
                raise ValueError('Request too large or empty')
            payload = json.loads(self.rfile.read(size))
            if not isinstance(payload, dict):
                raise ValueError('Expected JSON object')
            kind = {'/api/design': 'design', '/api/build': 'build', '/api/render': 'render'}.get(urlparse(self.path).path)
            if not kind:
                return self.send_error(404)
            if kind != 'design':
                checked_scene(payload.get('scene'))
            checked_edits(payload.get('edits', {}))
            with LOCK:
                if any((j['status'] in ('queued', 'running') for j in JOBS.values())):
                    return self.send_json({'message': 'A job is already running. Wait for it to finish.'}, 409)
                job_id = uuid.uuid4().hex
                JOBS[job_id] = {'id': job_id, 'kind': kind, 'status': 'queued', 'message': 'Queued', 'created': time.time()}
            threading.Thread(target=run_job, args=(job_id, kind, payload), daemon=True).start()
            self.send_json({'id': job_id}, 202)
        except (ValueError, TypeError, KeyError) as exc:
            self.send_json({'message': str(exc)[:5000]}, 400)
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8504)
    parser.add_argument('--host', default='127.0.0.1')
    args = parser.parse_args()
    if not all(((OUTPUT / 'example' / (mode + '.glb')).exists() for mode in ('exterior', 'interior', 'cutaway'))):
        blender = shutil.which('blender')
        if blender:
            print('Preparing example residence (no Groq request)…', flush=True)
            subprocess.run([blender, '--background', '--factory-startup', '--threads', '6', '--python-exit-code', '1', '--python', str(ROOT / 'scripts/building.py'), '--', '--scene', str(ROOT / 'assets/demo.json'), '--out', str(OUTPUT / 'example')], cwd=ROOT, check=True)
    print(f'Architect Studio: http://{args.host}:{args.port}', flush=True)
    ThreadingHTTPServer((args.host, args.port), Handler).serve_forever()
