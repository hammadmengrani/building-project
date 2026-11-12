import copy
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geometry import validate, owners, shape_signature, intersects
from planner import compile_brief, summarize_scene, PlanningError
from intent import DesignBrief
ROOT = Path(__file__).resolve().parents[1]
BRIEF = json.loads((ROOT / 'assets/l-courtyard-brief.json').read_text())

def contains(scene, x, y):
    return any((r['x'] <= x <= r['x'] + r['width'] and r['y'] <= y <= r['y'] + r['depth'] for r in scene['rooms']))

class PlannerTests(unittest.TestCase):

    def test_regression_actual_groq_failure_becomes_valid_without_provider(self):
        old = json.loads((ROOT / 'tests/fixtures/failed-groq-scene.json').read_text())
        errors = validate(old)
        self.assertTrue(any(('overlaps' in e for e in errors)))
        self.assertTrue(any(('unreachable' in e for e in errors)))
        with patch('groq.Groq', side_effect=AssertionError('No API call allowed')):
            scene = compile_brief(BRIEF)
        self.assertEqual([], validate(scene))
        self.assertEqual((14, 12), (scene['width'], scene['depth']))
        self.assertEqual(2, sum(('bedroom' in r['name'].lower() for r in scene['rooms'])))
        self.assertEqual(1, sum(('bathroom' in r['name'].lower() for r in scene['rooms'])))
        self.assertFalse(contains(scene, 13.9, 11.9))
        self.assertTrue(contains(scene, 0.1, 11.9))
        self.assertTrue(contains(scene, 13.9, 0.1))
        self.assertEqual(BRIEF['wall_color'], scene['wall_color'])
        self.assertEqual(10, len(scene['furniture']))

    def test_courtyard_side_reflects_shape_and_valid_openings(self):
        brief = copy.deepcopy(BRIEF)
        brief['courtyard_corner'] = 'rear-left'
        scene = compile_brief(brief)
        self.assertEqual([], validate(scene))
        self.assertFalse(contains(scene, 0.1, 11.9))
        self.assertTrue(contains(scene, 13.9, 11.9))
        self.assertTrue(all((len(owners(o, scene['rooms'])) == 1 for o in scene['openings'] if o['kind'] == 'window')))

    def test_dimensions_and_room_counts_drive_new_geometry(self):
        brief = copy.deepcopy(BRIEF)
        brief.update(width=16.0, depth=14.0)
        bedroom = copy.deepcopy(brief['rooms'][0])
        bedroom.update(id='bed3', name='Bedroom 3')
        brief['rooms'].append(bedroom)
        scene = compile_brief(brief)
        self.assertEqual([], validate(scene))
        self.assertEqual(3, sum(('bedroom' in r['name'].lower() for r in scene['rooms'])))
        self.assertNotEqual(shape_signature(scene), shape_signature(compile_brief(BRIEF)))

    def test_explicit_maximum_room_areas_are_honored(self):
        brief = copy.deepcopy(BRIEF)
        limits = {'bed1': 16.0, 'bed2': 16.0, 'bath': 6.0, 'living': 26.0, 'kitchen': 14.0}
        for room in brief['rooms']:
            if room['id'] in limits:
                room['maximum_area'] = limits[room['id']]
        scene = compile_brief(brief)
        self.assertEqual([], validate(scene))
        for room in scene['rooms']:
            if room['id'] in limits:
                area = room['width'] * room['depth']
                self.assertLessEqual(area, limits[room['id']] + 0.01, room['id'])

    def test_bounded_rooms_fit_compact_multistorey_footprint(self):
        brief = copy.deepcopy(BRIEF)
        brief.update(shape='rectangle', width=10.0, depth=12.0, storeys=2, upper_floors=[])
        brief['rooms'] = [
            dict(id='bed1', name='Bedroom 1', kind='bedroom', target_area=14.0, maximum_area=18.0, zone='rear'),
            dict(id='bed2', name='Bedroom 2', kind='bedroom', target_area=14.0, maximum_area=18.0, zone='rear'),
            dict(id='bath1', name='Shared Bathroom 1', kind='bathroom', target_area=4.5, maximum_area=6.0),
            dict(id='bath2', name='Shared Bathroom 2', kind='bathroom', target_area=4.5, maximum_area=6.0),
            dict(id='kitchen', name='Kitchen', kind='kitchen', target_area=10.0, maximum_area=15.0),
        ]
        scene = compile_brief(brief)
        self.assertEqual([], validate(scene))
        for layout in [scene, *scene['upper_floors']]:
            areas = {r['id']: r['width'] * r['depth'] for r in layout['rooms']}
            self.assertLessEqual(areas['bed1'], 18.01)
            self.assertLessEqual(areas['bed2'], 18.01)
            self.assertLessEqual(areas['bath1'], 6.01)
            self.assertLessEqual(areas['bath2'], 6.01)
            self.assertLessEqual(areas['kitchen'], 15.01)

    def test_rectangle_and_u_shape_connectivity(self):
        for shape in ('rectangle', 'U'):
            brief = copy.deepcopy(BRIEF)
            brief.update(shape=shape, width=16.0, depth=14.0)
            with self.subTest(shape=shape):
                scene = compile_brief(brief)
                self.assertEqual([], validate(scene))
                if shape == 'U':
                    self.assertFalse(contains(scene, 8, 13.9))
                    self.assertTrue(contains(scene, 0.1, 13.9))
                    self.assertTrue(contains(scene, 15.9, 13.9))

    def test_attached_bathroom_connects_only_through_bedroom(self):
        brief = copy.deepcopy(BRIEF)
        brief.update(shape='rectangle', width=14.0, depth=14.0)
        brief['rooms'][2]['attached_to'] = 'bed1'
        scene = compile_brief(brief)
        self.assertEqual([], validate(scene))
        pairs = [{r['id'] for r in owners(o, scene['rooms'])} for o in scene['openings'] if o['kind'] == 'door']
        self.assertIn({'bed1', 'bath'}, pairs)
        self.assertFalse(any(('bath' in pair and len(pair) == 2 and ('bed1' not in pair) for pair in pairs)))

    def test_palette_edit_preserves_every_coordinate_and_opening(self):
        scene = compile_brief(BRIEF)
        summary = summarize_scene(scene)
        brief = copy.deepcopy(BRIEF)
        brief['action'] = 'palette'
        brief['wall_color'] = {'r': 0.06, 'g': 0.14, 'b': 0.28}
        # A compiled plan can have extra circulation segments; include their stable IDs.
        existing = {r['id'] for r in brief['rooms']}
        for r in summary['rooms']:
            if r['id'] not in existing:
                brief['rooms'].append(dict(id=r['id'], name=r['name'], kind='hall', target_area=float(r['area'])))
        changed = compile_brief(brief, scene)
        self.assertEqual([], validate(changed))
        self.assertEqual(scene['openings'], changed['openings'])
        self.assertEqual(shape_signature(scene), shape_signature(changed))
        self.assertEqual(scene['furniture'], changed['furniture'])
        self.assertNotEqual(scene['wall_color'], changed['wall_color'])

    def test_impossible_brief_fails_without_dropping_rooms_or_retries(self):
        brief = copy.deepcopy(BRIEF)
        brief.update(width=5.0, depth=5.0)
        with patch('groq.Groq', side_effect=AssertionError('No API call allowed')):
            with self.assertRaisesRegex(PlanningError, 'No extra Groq request'):
                compile_brief(brief)

    def test_variants_change_geometry_and_are_reproducible(self):
        variants = []
        for variant in (0, 1, 7):
            brief = copy.deepcopy(BRIEF)
            brief['layout_variant'] = variant
            scene = compile_brief(brief)
            self.assertEqual([], validate(scene))
            self.assertEqual(scene, compile_brief(brief))
            variants.append(shape_signature(scene))
        self.assertGreater(len(set(variants)), 1)
if __name__ == '__main__':
    unittest.main()
