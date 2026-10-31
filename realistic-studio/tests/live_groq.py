"""One explicit live provider smoke test. Never part of the offline suite."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import ROOT, OUTPUT, checked_scene
from one_shot import design
import os
prompt = 'Actual building footprint 8 by 6 metres. Single storey. Design exactly two rooms: a living room and one bedroom. One exterior entrance, a connecting door, external windows for both rooms. Include a bed and sofa. No kitchen or bathroom is requested in this small rendering test. Warm plaster, wooden accents. Use valid nonoverlapping geometry and keep furniture clear of door approaches.'
r = design(prompt, api_key=os.getenv('GROQ_API_KEY'), model_name=os.getenv('GROQ_MODEL', 'openai/gpt-oss-20b'))
folder = OUTPUT / 'groq-smoke'
folder.mkdir(exist_ok=True)
(folder / 'response.json').write_text(r.model_dump_json(indent=2))
if not r.ready:
    raise ValueError(r.message)
s = checked_scene(r.scene.model_dump())
(folder / 'scene.json').write_text(json.dumps(s, indent=2))
print('LIVE_GROQ_VALID:', len(s['rooms']), 'rooms,', len(s['openings']), 'openings,', len(s['furniture']), 'furniture items')
