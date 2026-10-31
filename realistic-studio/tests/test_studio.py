import copy
import json
from pathlib import Path
import struct
import sys
import unittest
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server import ROOT, checked_scene, checked_edits
from geometry import validate
from one_shot import design
DEMO = json.loads((ROOT / 'assets/demo.json').read_text())

class LayoutTests(unittest.TestCase):

    def test_demo_has_real_connectivity_and_valid_furniture(self):
        scene = checked_scene(DEMO)
        self.assertEqual(7, len(scene['rooms']))
        self.assertEqual([], validate(scene))

    def test_overlap_and_unreachable_room_block_generation(self):
        bad = copy.deepcopy(DEMO)
        bad['rooms'][0]['x'] = 3.0
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            checked_scene(bad)
        bad = copy.deepcopy(DEMO)
        bad['openings'] = [o for o in bad['openings'] if o['id'] != 'd5']
        with self.assertRaisesRegex(ValueError, 'unreachable'):
            checked_scene(bad)

    def test_invalid_material_and_nonfinite_transforms_rejected(self):
        for edits in ({'a': {'position': [0, float('nan'), 0]}}, {'a': {'scale': [1, -1, 1]}}, {'a': {'color': 'javascript:alert(1)'}}):
            with self.assertRaises(ValueError):
                checked_edits(edits)
        self.assertEqual({'bed': {'position': [1, 2, 3], 'color': '#abcdef'}}, checked_edits({'bed': {'position': [1, 2, 3], 'color': '#abcdef'}}))

    def test_one_provider_request_returns_full_dynamic_scene(self):
        brief = json.loads((ROOT / 'assets/l-courtyard-brief.json').read_text())
        packet = {'message': 'Ready', 'ready': True, 'assumptions': [], 'unsupported': [], 'brief': brief}
        calls = []

        class Completions:

            def create(self, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(packet)), finish_reason='stop')])
        client = SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
        result = design('A furnished bungalow', client=client)
        self.assertEqual(1, len(calls))
        self.assertEqual(14, result.scene.width)
        self.assertEqual([], validate(result.scene.model_dump()))
        self.assertLessEqual(calls[0]['max_completion_tokens'], 5000)
        self.assertNotIn('openings', calls[0]['messages'][1]['content'])
        self.assertIn('A furnished bungalow', calls[0]['messages'][1]['content'])

    def test_provider_desk_alias_generates_scene_in_one_call(self):
        from unittest.mock import Mock
        brief = json.loads((ROOT / 'assets/four-storey-brief.json').read_text())
        office = next(r for r in brief['rooms'] if r['kind'] == 'office')
        office['furniture'] = ['desk', 'office chair']
        packet = dict(message='Ready', ready=True, assumptions=[], unsupported=[], brief=brief)
        create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(packet)), finish_reason='stop')]))
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        result = design('Four floors with an office desk', client=client)
        self.assertTrue(result.ready, result.message)
        self.assertEqual(1, create.call_count)
        self.assertEqual([], validate(result.scene.model_dump()))
        kinds = {f.kind for f in result.scene.furniture if f.room_id == office['id']}
        self.assertEqual({'table', 'chair'}, kinds)

    def test_provider_short_storey_height_is_fixed_in_one_call(self):
        from unittest.mock import Mock
        brief = json.loads((ROOT / 'assets/four-storey-brief.json').read_text())
        brief.update(ceiling_height=3.2, storey_height=3.2)
        packet = dict(message='Ready', ready=True, assumptions=[], unsupported=[], brief=brief)
        create = Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(
            message=SimpleNamespace(content=json.dumps(packet)), finish_reason='stop')]))
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        result = design('Four floors', client=client)
        self.assertTrue(result.ready, result.message)
        self.assertEqual(1, create.call_count)
        self.assertAlmostEqual(3.45, result.scene.storey_height)
        self.assertEqual([], validate(result.scene.model_dump()))
        for floor in result.scene.upper_floors:
            self.assertAlmostEqual(floor.level * 3.45, floor.elevation)

    def test_sufficient_or_unspecified_storey_height_is_preserved(self):
        from intent import DesignBrief
        brief = json.loads((ROOT / 'assets/four-storey-brief.json').read_text())
        for height in (None, 3.8):
            brief.update(ceiling_height=3.2, storey_height=height)
            self.assertEqual(height, DesignBrief.model_validate(brief).storey_height)

    def test_furniture_aliases_normalize_without_hiding_unknown_types(self):
        from intent import RoomIntent
        from pydantic import ValidationError
        room = dict(id='office', name='Office', kind='office', target_area=20.0)
        parsed = RoomIntent(**room, furniture=[' Desk ', 'Office-Chair', 'wash basin'])
        self.assertEqual(['table', 'chair', 'basin'], parsed.furniture)
        with self.assertRaises(ValidationError):
            RoomIntent(**room, furniture=['unsupported_magic_machine'])

    def test_truncated_provider_response_is_not_retried(self):
        calls = []

        class Completions:

            def create(self, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{}'), finish_reason='length')])
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            design('A bungalow', client=SimpleNamespace(chat=SimpleNamespace(completions=Completions())))
        self.assertEqual(1, len(calls))

class ExportTests(unittest.TestCase):

    @staticmethod
    def glb(mode):
        file = ROOT / 'output/example' / f'{mode}.glb'
        if not file.exists():
            raise unittest.SkipTest('Build example GLBs first')
        raw = file.read_bytes()
        assert struct.unpack_from('<4sII', raw) == (b'glTF', 2, len(raw))
        length = struct.unpack_from('<I', raw, 12)[0]
        return json.loads(raw[20:20 + length])

    def test_three_views_have_pbr_textures_and_stable_entity_ids(self):
        views = {mode: self.glb(mode) for mode in ('exterior', 'interior', 'cutaway')}
        for mode, g in views.items():
            ids = [n.get('extras', {}).get('entity') for n in g['nodes'] if n.get('extras', {}).get('entity')]
            self.assertEqual(len(ids), len(set(ids)))
            self.assertIn('furniture:bedA', ids)
            self.assertTrue(any(('normalTexture' in m for m in g['materials'])))
            self.assertGreater(len(g['images']), 5)
            self.assertEqual(mode == 'exterior', any((k.startswith('roof:') for k in ids)))

    def test_parenting_preserves_architectural_coordinates(self):
        g = self.glb('exterior')
        roots = {n.get('extras', {}).get('entity'): n for n in g['nodes']}
        bed = roots['furniture:bedA']
        for actual, expected in zip(bed['translation'], [1.6, 0.22, -6.7]):
            self.assertAlmostEqual(actual, expected, places=5)
        # Children must be local offsets, not the original global position again.
        for child in bed['children']:
            values = g['nodes'][child].get('translation', [0, 0, 0])
            self.assertLess(max((abs(v) for v in values)), 2)
        floor = roots['floor:living']
        self.assertEqual([2, 0, -2.5], floor['translation'])
if __name__ == '__main__':
    unittest.main()
