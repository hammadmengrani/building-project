import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from planner import compile_brief, summarize_scene, PlanningError
from server import checked_scene
from geometry import validate
from facade_geometry import add_villa_facade, solid_intervals
ROOT=Path(__file__).resolve().parents[1]

class VillaArchitectureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief=json.loads((ROOT/'assets/luxury-villa-brief.json').read_text())
        cls.scene=checked_scene(compile_brief(cls.brief))

    def test_hard_minimums_and_courtyard_survive_full_validation(self):
        self.assertEqual([],validate(self.scene))
        intents={r['id']:r for r in self.brief['rooms']}
        for room in self.scene['rooms']:
            intent=intents.get(room['id'],{})
            w,d=room['width']-.18,room['depth']-.18
            self.assertGreaterEqual(min(w,d)+.001,intent.get('minimum_width',0))
            self.assertGreaterEqual(w*d+.01,intent.get('minimum_area',0))
        x,y=self.scene['width']-.5,self.scene['depth']-.5
        self.assertFalse(any(r['x']<x<r['x']+r['width'] and r['y']<y<r['y']+r['depth'] for r in self.scene['rooms']))
        self.assertEqual(self.scene['architecture'],summarize_scene(self.scene)['architecture'])

    def test_impossible_minimum_is_not_silently_shrunk(self):
        brief=copy.deepcopy(self.brief)
        for r in brief['rooms']:
            if r['kind']=='bedroom':r['minimum_width']=14.
        with self.assertRaisesRegex(PlanningError,'minimum usable'):
            compile_brief(brief)

    def test_glazing_is_prompt_controlled_and_valid(self):
        brief=copy.deepcopy(self.brief)
        brief['architecture'].update(window_ratio=.3,window_height=1.2,window_sill=1.)
        alternate=checked_scene(compile_brief(brief))
        large={w['id']:w for w in self.scene['openings'] if w['kind']=='window'}
        differences=[w for w in alternate['openings'] if w['id'] in large and w['height']!=large[w['id']]['height']]
        self.assertTrue(differences)
        self.assertEqual([],validate(alternate))

    def parts(self,style):
        scene=copy.deepcopy(self.scene);scene['architecture']['entrance_style']=style
        parts=[]
        add_villa_facade(scene,.22,0,'exterior',lambda *a:None,
                         lambda name,size,pos,*a,**k:parts.append((name,size,pos)),
                         lambda *a,**k:None,lambda x:None,lambda *a:{'stone':{},'wood':{}})
        return parts

    def test_entrance_choices_generate_different_geometry(self):
        portal=self.parts('portal');pergola=self.parts('pergola');canopy=self.parts('canopy')
        self.assertTrue(any(n=='Villa portal pier' for n,*_ in portal))
        self.assertFalse(any(n=='Villa portal pier' for n,*_ in canopy))
        self.assertTrue(any(n=='Villa entrance open rafter' for n,*_ in pergola))
        self.assertFalse(any(n=='Villa broad entrance canopy' for n,*_ in pergola))
        self.assertNotEqual(portal,pergola)
        self.assertTrue(all(min(size)>0 for parts in (portal,pergola,canopy) for _,size,_ in parts))

    def test_cladding_gaps_preserve_real_door_and_window_spans(self):
        openings=[dict(axis='x',x=3.,y=0.,width=1.2),dict(axis='x',x=6.,y=0.,width=2.)]
        gaps=solid_intervals(0,10,openings,'x',0)
        self.assertTrue(gaps)
        for a,b in gaps:
            for opening in openings:
                self.assertTrue(b<=opening['x']-opening['width']/2-.18+1e-6 or a>=opening['x']+opening['width']/2+.18-1e-6)

if __name__=='__main__':unittest.main()
