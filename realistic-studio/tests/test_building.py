import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from planner import compile_brief, PlanningError, summarize_scene
from geometry import validate, owners
from server import checked_scene
ROOT = Path(__file__).resolve().parents[1]
BRIEF = json.loads((ROOT / 'assets/four-storey-brief.json').read_text())

class BuildingTests(unittest.TestCase):

    def test_four_floor_gym_parking_park_without_extra_ai(self):
        with patch('groq.Groq', side_effect=AssertionError('Local planning must not call Groq')):
            scene = checked_scene(compile_brief(BRIEF))
        self.assertEqual([], validate(scene))
        self.assertEqual(4, scene['storeys'])
        self.assertEqual([1, 2, 3], [f['level'] for f in scene['upper_floors']])
        self.assertEqual(8, len(scene['site']['parking']))
        self.assertAlmostEqual(120, scene['site']['park']['width'] * scene['site']['park']['depth'])
        gym = next((r for r in scene['rooms'] if r['kind'] == 'gym'))
        self.assertEqual({'treadmill', 'exercise_bike', 'weight_rack'}, {f['kind'] for f in scene['furniture'] if f['room_id'] == gym['id']})
        core = scene['vertical_core']
        for floor in [scene, *scene['upper_floors']]:
            stairs = next((r for r in floor['rooms'] if r['id'] == 'vertical_core'))
            self.assertEqual([core[k] for k in ('x', 'y', 'width', 'depth')], [stairs[k] for k in ('x', 'y', 'width', 'depth')])
        for floor in scene['upper_floors']:
            self.assertAlmostEqual(floor['level'] * scene['storey_height'], floor['elevation'])
            self.assertFalse(any((o['entrance'] for o in floor['openings'])))
            self.assertTrue(any(({r['id'] for r in owners(o, floor['rooms'])} == {'vertical_core', 'floor_lobby'} for o in floor['openings'] if o['kind'] == 'door')))

    def test_different_upper_floor_programs(self):
        brief = copy.deepcopy(BRIEF)
        brief['upper_floors'][0]['levels'] = [1, 2]
        brief['upper_floors'].append({'levels': [3], 'rooms': [dict(id='top_gym', name='Rooftop fitness room', kind='gym', target_area=60.0, zone='rear'), dict(id='top_office', name='Office', kind='office', target_area=20.0, zone='front')]})
        scene = compile_brief(brief)
        self.assertEqual([], validate(scene))
        self.assertTrue(any((r['kind'] == 'gym' for r in scene['upper_floors'][-1]['rooms'])))
        self.assertTrue(any((r['kind'] == 'bedroom' for r in scene['upper_floors'][0]['rooms'])))

    def test_invalid_plot_or_missing_aligned_core_rejected(self):
        brief = copy.deepcopy(BRIEF)
        brief['site'].update(width=20.0, depth=20.0)
        with self.assertRaisesRegex(PlanningError, 'do not fit'):
            compile_brief(brief)
        scene = compile_brief(BRIEF)
        scene['upper_floors'][0]['rooms'][-2]['x'] += 0.5
        self.assertTrue(any(('core' in e.lower() for e in validate(scene))))

    def test_eight_storeys_and_summary_includes_all_programs(self):
        brief = copy.deepcopy(BRIEF)
        brief['storeys'] = 8
        brief['upper_floors'][0]['levels'] = list(range(1, 8))
        scene = compile_brief(brief)
        self.assertEqual([], validate(scene))
        self.assertEqual(7, len(scene['upper_floors']))
        summary = summarize_scene(scene)
        self.assertEqual(8, summary['storeys'])
        self.assertEqual(1,len(summary['upper_floors']))
        self.assertEqual(list(range(1,8)),summary['upper_floors'][0]['levels'])
    def test_twenty_floors_with_pool_and_compact_summary(self):
        brief = copy.deepcopy(BRIEF)
        brief['storeys'] = 20
        brief['upper_floors'][0]['levels'] = list(range(1,20))
        brief['site'].update(pool_width=8.0, pool_depth=4.0)
        scene = checked_scene(compile_brief(brief))
        self.assertEqual([], validate(scene))
        self.assertEqual(19,len(scene['upper_floors']))
        self.assertEqual(8.0,scene['site']['pool']['width'])
        self.assertEqual(4.0,summarize_scene(scene)['site']['pool_depth'])
        broken = copy.deepcopy(scene)
        broken['site']['pool']['x'] = 0.0
        self.assertIn('Site feature overlaps the building.',validate(broken))

    def test_pool_requires_both_dimensions(self):
        brief = copy.deepcopy(BRIEF)
        brief['site']['pool_width'] = 8.0
        with self.assertRaisesRegex(PlanningError,'both width and depth'):
            compile_brief(brief)

if __name__ == '__main__':
    unittest.main()
