import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from materials import resolve_materials
from planner import compile_brief,summarize_scene
from server import checked_scene
from procedural_materials import ensure_maps
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]


class MaterialTests(unittest.TestCase):
    def test_prompt_roles_and_room_overrides_survive_planning(self):
        brief=json.loads((ROOT/'assets/l-courtyard-brief.json').read_text())
        brief['materials']={'wood':{'finish':'walnut','color':{'r':0.2,'g':0.1,'b':0.04}},'upholstery':{'finish':'leather','color':{'r':0.1,'g':0.5,'b':0.6}}}
        bedroom=next(r for r in brief['rooms'] if r['kind']=='bedroom')
        bedroom['materials']={'upholstery':{'finish':'linen','color':{'r':0.8,'g':0.3,'b':0.2}},'floor':{'finish':'oak','repeat_m':1.8}}
        scene=checked_scene(compile_brief(brief))
        room=next(r for r in scene['rooms'] if r['id']==bedroom['id'])
        specs=resolve_materials(scene,room)
        self.assertEqual('walnut',specs['wood']['finish'])
        self.assertEqual('linen',specs['upholstery']['finish'])
        self.assertEqual(0.8,specs['upholstery']['color']['r'])
        self.assertEqual(1.8,specs['floor']['repeat_m'])
        self.assertEqual('walnut',summarize_scene(scene)['materials']['wood']['finish'])

    def test_styles_resolve_to_distinct_finishes_without_mutating_scene(self):
        scene=json.loads((ROOT/'assets/demo.json').read_text());before=copy.deepcopy(scene)
        room=scene['rooms'][0]
        outputs=[]
        for style in ('coastal','industrial','traditional'):
            outputs.append(resolve_materials(scene,{**room,'interior_style':style}))
        self.assertEqual('leather',outputs[1]['upholstery']['finish'])
        self.assertEqual('walnut',outputs[2]['wood']['finish'])
        self.assertNotEqual(outputs[0],outputs[1])
        self.assertEqual(before,scene)

    def test_generated_albedo_is_neutral_and_maps_are_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp:
            maps=ensure_maps(tmp,'marble',0.35,size=32)
            image=Image.open(maps['color'])
            self.assertEqual((32,32),image.size)
            pixels=image.tobytes()
            self.assertTrue(all(pixels[i]==pixels[i+1]==pixels[i+2] for i in range(0,len(pixels),3)))
            before={k:p.read_bytes() for k,p in maps.items()}
            self.assertEqual(before,{k:p.read_bytes() for k,p in ensure_maps(tmp,'marble',0.35,size=32).items()})
            self.assertNotEqual(before['color'],ensure_maps(tmp,'oak',0.35,size=32)['color'].read_bytes())

if __name__=='__main__':unittest.main()
