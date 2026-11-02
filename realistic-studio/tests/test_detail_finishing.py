import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from interior_details import add_finishing


class DetailFinishingTests(unittest.TestCase):
    def test_detailed_example_has_valid_access_and_wet_fixtures(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
        from server import checked_scene
        path=Path(__file__).resolve().parents[1]/'static/examples/detail-benchmark.json'
        scene=checked_scene(json.loads(path.read_text()))
        self.assertEqual(3,len(scene['rooms']))
        self.assertEqual({'bed','wardrobe','toilet','basin','shower'}, {f['kind'] for f in scene['furniture']})

    def test_skirting_clears_a_centered_door_and_curtain_tracks_match_window(self):
        room=dict(id='bed',x=0.,y=0.,width=6.,depth=5.,height=3.)
        scene=dict(rooms=[room],openings=[
            dict(kind='door',axis='x',x=1.,y=0.,width=.9,id='door'),
            dict(kind='window',axis='x',x=3.,y=5.,width=2.,height=1.5,bottom=.85,id='window')])
        boxes=[];panels=[]
        def box(name,size,pos,*args):boxes.append((name,size,pos))
        def curtain(name,w,h,center,*args):panels.append((w,h,center))
        add_finishing(scene,.22,lambda *a:None,box,lambda *a:None,lambda *a,**k:object(),object(),object(),'interior',curtain_builder=curtain)
        bottom=[(size,pos) for name,size,pos in boxes if name=='Painted skirting' and abs(pos[1]-.105)<.001]
        self.assertEqual(2,len(bottom))
        for size,pos in bottom:
            self.assertTrue(pos[0]+size[0]/2<=.55 or pos[0]-size[0]/2>=1.45)
        self.assertEqual(2,len(panels))
        for w,h,center in panels:
            self.assertGreaterEqual(center[0]-w/2,2.)
            self.assertLessEqual(center[0]+w/2,4.)
        tracks=[pos for name,size,pos in boxes if name=='Curtain track']
        self.assertEqual(3.,tracks[0][0])

if __name__=='__main__':unittest.main()
