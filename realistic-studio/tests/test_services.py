import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from services import electrical_plan
ROOT=Path(__file__).resolve().parents[1]


class ElectricalConceptTests(unittest.TestCase):
    def test_every_non_stair_room_has_switch_and_light_without_wet_sockets(self):
        scene=json.loads((ROOT/'assets/four-storey-scene.json').read_text())
        for layout in [scene,*scene['upper_floors']]:
            plan=electrical_plan(layout)
            self.assertIn('not engineer reviewed',plan['status'])
            devices={d['id']:d for d in plan['devices']}
            for room in layout['rooms']:
                if room.get('kind')=='stairs': continue
                self.assertIn(room['id']+':switch',devices)
                self.assertIn(room['id']+':light',devices)
                if room.get('kind') in ('bathroom','kitchen','hall'):
                    self.assertNotIn(room['id']+':socket',devices)
            for route in plan['routes']:
                self.assertEqual(devices['distribution_board']['point'],route['points'][0]) if route['id'].endswith((':lighting',':power')) else None
                for a,b in zip(route['points'],route['points'][1:]):
                    self.assertLessEqual(sum(abs(x-y)>1e-6 for x,y in zip(a,b)),1)

    def test_legacy_rooms_with_no_kind_do_not_get_wet_area_sockets(self):
        scene=json.loads((ROOT/'assets/demo.json').read_text())
        devices={d['id'] for d in electrical_plan(scene)['devices']}
        for item in scene['furniture']:
            if item['kind'] in ('toilet','shower','kitchen'):
                self.assertNotIn(item['room_id']+':socket',devices)

    def test_switches_stay_in_room_and_output_deterministic(self):
        scene=json.loads((ROOT/'assets/demo.json').read_text())
        self.assertEqual(electrical_plan(scene),electrical_plan(scene))
        plan=electrical_plan(scene)
        for room in scene['rooms']:
            points=[d['point'] for d in plan['devices'] if d['id'].startswith(room['id']+':')]
            for x,y,z in points:
                self.assertTrue(room['x']<=x<=room['x']+room['width'])
                self.assertTrue(room['y']<=y<=room['y']+room['depth'])
                self.assertTrue(0<z<room['height'])

if __name__=='__main__': unittest.main()
