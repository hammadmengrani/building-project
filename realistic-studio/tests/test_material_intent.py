import copy
import json
from pathlib import Path
import sys
import unittest
from pydantic import ValidationError
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from intent import BriefResponse
from schema import MaterialPalette
from planner import compile_brief
from materials import resolve_materials
ROOT = Path(__file__).resolve().parents[1]

class ProviderMaterialTests(unittest.TestCase):
    def payload(self):
        return dict(message='Ready', ready=True, assumptions=[], unsupported=[], brief=json.loads((ROOT/'assets/l-courtyard-brief.json').read_text()))

    def test_reported_colors_in_finish_validate_and_compile_without_mutation(self):
        payload = self.payload()
        payload['brief']['materials'] = {'upholstery': {'finish':'cream'}, 'stone': {'finish':'pale'}, 'floor': {'finish':'pale'}}
        before = copy.deepcopy(payload)
        response = BriefResponse.model_validate(payload)
        self.assertIsNone(response.brief.materials.upholstery.finish)
        self.assertAlmostEqual(response.brief.materials.upholstery.color.r, 1.0)
        scene = compile_brief(response.brief.model_dump(mode='json'))
        specs = resolve_materials(scene, scene['rooms'][0])
        self.assertEqual(specs['upholstery']['finish'], 'linen')
        self.assertEqual(specs['upholstery']['color']['r'], 1.0)
        self.assertEqual(before, payload)

    def test_room_and_upper_floor_overrides_keep_explicit_rgb(self):
        payload = self.payload()
        rgb = dict(r=.2,g=.4,b=.6)
        payload['brief']['rooms'][0]['materials'] = {'upholstery': {'finish':'Cream Linen', 'color':rgb}}
        payload['brief']['storeys'] = 2
        payload['brief']['upper_floors'] = [{'levels':[1], 'rooms':copy.deepcopy(payload['brief']['rooms'])}]
        response = BriefResponse.model_validate(payload)
        for room in (response.brief.rooms[0], response.brief.upper_floors[0].rooms[0]):
            self.assertEqual(room.materials.upholstery.finish, 'linen')
            self.assertEqual(room.materials.upholstery.color.model_dump(), rgb)

    def test_terracotta_finish_and_color_aliases_compile(self):
        payload = self.payload()
        payload['brief']['materials'] = {'stone': {'finish':'terracotta'}}
        payload['brief']['rooms'][0]['materials'] = {'floor': {'finish':'terra-cotta', 'color':dict(r=.5,g=.3,b=.2)}}
        original = copy.deepcopy(payload)
        response = BriefResponse.model_validate(payload)
        scene = compile_brief(response.brief.model_dump(mode='json'))
        self.assertEqual(scene['materials']['stone']['finish'], 'terracotta')
        specs = resolve_materials(scene, scene['rooms'][0])
        self.assertGreater(specs['stone']['color']['r'], specs['stone']['color']['g'])
        room = next(r for r in response.brief.rooms if r.id == payload['brief']['rooms'][0]['id'])
        self.assertEqual(room.materials.floor.finish, 'terracotta')
        self.assertEqual(room.materials.floor.color.r, .5)
        self.assertEqual(payload, original)
        self.assertEqual(MaterialPalette.model_validate({'stone':{'finish':'terracotta'}}).stone.finish, 'terracotta')
        payload['brief']['materials']['stone']['finish'] = 'terracotta stone'
        stone = BriefResponse.model_validate(payload).brief.materials.stone
        self.assertEqual(stone.finish, 'stone')
        self.assertAlmostEqual(stone.color.r, 199/255)

    def test_named_color_compound_and_unknown_material(self):
        payload=self.payload()
        payload['brief']['materials']={'wood':{'finish':' WALNUT '},'stone':{'finish':'pale stone'},'upholstery':{'finish':'olive'}}
        brief=BriefResponse.model_validate(payload).brief
        self.assertEqual(brief.materials.wood.finish,'walnut')
        self.assertEqual(brief.materials.stone.finish,'stone')
        self.assertIsNotNone(brief.materials.upholstery.color)
        payload['brief']['materials']['wood']['finish']='unobtanium'
        with self.assertRaises(ValidationError):BriefResponse.model_validate(payload)
        with self.assertRaises(ValidationError):MaterialPalette.model_validate({'upholstery':{'finish':'cream'}})

if __name__=='__main__': unittest.main()
