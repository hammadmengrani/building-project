import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from planner import compile_brief, summarize_scene
from server import checked_scene
from geometry import validate
from services import plumbing_plan
from construction import construction_plan
from intent import DesignBrief
ROOT=Path(__file__).resolve().parents[1]
BRIEF=json.loads((ROOT/'assets/l-courtyard-brief.json').read_text())


class VariantAndServicesTests(unittest.TestCase):
    def test_style_and_room_override_survive_compilation_and_summary(self):
        brief=copy.deepcopy(BRIEF)
        brief['interior_style']='traditional'
        bedroom=next(r for r in brief['rooms'] if r['kind']=='bedroom')
        bedroom['interior_style']='coastal'
        scene=checked_scene(compile_brief(brief))
        self.assertEqual([],validate(scene))
        self.assertEqual('traditional',scene['interior_style'])
        self.assertEqual('coastal',next(r for r in scene['rooms'] if r['id']==bedroom['id'])['interior_style'])
        self.assertEqual('traditional',summarize_scene(scene)['interior_style'])
        self.assertTrue(all('design_variant' in f for f in scene['furniture']))

    def test_furniture_scale_changes_dimensions_with_valid_access(self):
        base=compile_brief(BRIEF)
        brief=copy.deepcopy(BRIEF)
        for r in brief['rooms']:r['furniture_scale']=0.85
        changed=checked_scene(compile_brief(brief))
        a=next(f for f in base['furniture'] if f['kind']=='bed')
        b=next(f for f in changed['furniture'] if f['kind']=='bed')
        self.assertAlmostEqual(a['width']*0.85,b['width'])
        self.assertEqual([],validate(changed))

    def test_plumbing_fixture_coverage_and_connected_risers(self):
        scene=compile_brief(BRIEF)
        plan=plumbing_plan(scene)
        wet={f['id']:f for f in scene['furniture'] if f['kind'] in ('toilet','shower','basin','kitchen')}
        self.assertEqual(set(wet),{f['id'] for f in plan['fixtures']})
        for key,f in wet.items():
            circuits={r['circuit'] for r in plan['routes'] if r['id'].startswith(key+':')}
            self.assertEqual({'cold','drain'} if f['kind']=='toilet' else {'cold','hot','drain'},circuits)
        for route in plan['routes']:
            offset={'cold':0,'hot':0.12,'drain':0.24}[route['circuit']]
            self.assertAlmostEqual(plan['riser'][0]+offset,route['points'][0][0])
            for a,b in zip(route['points'],route['points'][1:]):
                self.assertLessEqual(sum(abs(x-y)>1e-6 for x,y in zip(a,b)),1)

    def test_construction_quantities_are_traceable_and_courtyard_stays_open(self):
        scene=compile_brief(BRIEF)
        plan=construction_plan(scene)
        self.assertTrue(plan['columns'])
        self.assertIsNone(plan['quantities']['cement_bags'])
        self.assertIn('not engineer reviewed',plan['status'])
        members=[*plan['columns'],*plan['beams'],*plan['slabs']]
        self.assertAlmostEqual(round(sum(m['width']*m['depth']*m['height'] for m in members),3),plan['quantities']['concrete_per_floor_m3'])
        for column in plan['columns']:
            self.assertTrue(any(r['x']-.001<=column['x']<=r['x']+r['width']+.001 and r['y']-.001<=column['y']<=r['y']+r['depth']+.001 for r in scene['rooms']))

    def test_attached_bathroom_alias_resolves_only_unique_bedroom(self):
        brief=copy.deepcopy(BRIEF)
        bed=next(r for r in brief['rooms'] if r['kind']=='bedroom')
        bath=next(r for r in brief['rooms'] if r['kind']=='bathroom')
        bed['id']='bedroom_1'
        bath['attached_to']='bed1'
        parsed=DesignBrief.model_validate(brief)
        self.assertEqual('bedroom_1',next(r for r in parsed.rooms if r.id==bath['id']).attached_to)

if __name__=='__main__':unittest.main()
