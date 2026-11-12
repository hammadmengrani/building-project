import copy
import json
from pathlib import Path
import sys
import unittest
from pydantic import ValidationError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from intent import BriefResponse, RoomIntent
from planner import compile_brief
from server import checked_scene
ROOT=Path(__file__).resolve().parents[1]

class RoomIntentNormalizationTests(unittest.TestCase):
    def test_zero_circulation_placeholders_compile_to_real_hall(self):
        brief=json.loads((ROOT/'assets/luxury-villa-brief.json').read_text())
        hall=next(r for r in brief['rooms'] if r['kind']=='hall')
        hall.update(kind='circulation',target_area=0,minimum_area=0,minimum_width=0)
        before=copy.deepcopy(brief)
        response=BriefResponse.model_validate(dict(message='ready',ready=True,assumptions=[],unsupported=[],brief=brief))
        parsed=next(r for r in response.brief.rooms if r.id==hall['id'])
        self.assertEqual(parsed.kind,'hall')
        self.assertEqual(parsed.target_area,0)
        self.assertIsNone(parsed.minimum_area)
        self.assertIsNone(parsed.minimum_width)
        scene=checked_scene(compile_brief(response.brief))
        self.assertTrue(any(r.get('kind')=='hall' and min(r['width'],r['depth'])>=1.58 for r in scene['rooms']))
        self.assertEqual(brief,before)

    def test_zero_optional_minimum_is_absent_but_positive_constraints_survive(self):
        room=RoomIntent(id='bed',name='Bedroom',kind='bedroom',target_area=28.,minimum_area=0,minimum_width=0)
        self.assertIsNone(room.minimum_area)
        self.assertIsNone(room.minimum_width)
        room=RoomIntent(id='bed',name='Bedroom',kind='bedroom',target_area=28.,minimum_area=25.,minimum_width=4.)
        self.assertEqual((room.minimum_area,room.minimum_width),(25.,4.))

    def test_invalid_usable_room_sizes_are_not_hidden(self):
        for kind in ['bedroom','bathroom','living','gym','pool']:
            with self.subTest(kind=kind),self.assertRaises(ValidationError):
                RoomIntent(id='room',name='Room',kind=kind,target_area=0,minimum_area=0,minimum_width=0)
        for field,value in [('minimum_area',-1.),('minimum_width',.5),('minimum_width',False),('target_area',-1.)]:
            data=dict(id='room',name='Room',kind='bedroom',target_area=28.)
            data[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValidationError):RoomIntent(**data)

    def test_upper_floor_hall_has_same_semantics(self):
        brief=json.loads((ROOT/'assets/l-courtyard-brief.json').read_text())
        brief['storeys']=2
        upper=copy.deepcopy(brief['rooms'])
        for room in upper:
            if room['kind']=='hall':room.update(kind=' hallway ',target_area=0,minimum_width=0,minimum_area=0)
        brief['upper_floors']=[dict(levels=[1],rooms=upper)]
        response=BriefResponse.model_validate(dict(message='ready',ready=True,assumptions=[],unsupported=[],brief=brief))
        self.assertTrue(any(room.kind=='hall' and room.target_area==0 for room in response.brief.upper_floors[0].rooms))

if __name__=='__main__':unittest.main()
