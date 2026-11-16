import sys,json,unittest,urllib.request,urllib.error
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'pedestrian'))
from environment import Environment
class SharedApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base='http://127.0.0.1:8811';cls.meta=json.load(urllib.request.urlopen(cls.base+'/api/pedestrian/meta'))
        cls.env=Environment(ROOT,json.loads((ROOT/'pedestrian/scenario.json').read_text()))
    def plan(self,start=0,minutes=None):
        a,b=self.meta['example'];body=dict(origin=a,goal=b,departure_s=start,max_minutes=(46800-start)/60 if minutes is None else minutes)
        return urllib.request.urlopen(urllib.request.Request(self.base+'/api/pedestrian/plan',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'}),timeout=180)
    def test_route_profiles_match_native_fields_at_actual_position_and_absolute_time(self):
        for start in [0,120,540,600,1200,45000]:
            result=json.load(self.plan(start));route=result['routes'][1]
            self.assertTrue(result['cvae_enabled']);self.assertLessEqual(start+route['duration_s'],46800)
            for s in route['profile']:
                t=s['seconds'];e=next((e for e in route['timeline'] if e['start']<=t<e['end']),route['timeline'][-1])
                p=e['points'][0]
                if e['kind']!='Waiting':
                    d=np.clip((t-e['start'])/(e['end']-e['start']),0,1)*e['distance'][-1]
                    p=[np.interp(d,e['distance'],np.array(e['points'])[:,j]) for j in range(2)]
                self.assertEqual(s['temperature'],self.env.sample('temp',p,start+t))
                self.assertEqual(s['pollution'],self.env.pollution(p,start+t))
            (ROOT/f'pedestrian/cache/shared-plan-{start}.json').write_text(json.dumps(result))
    def test_only_breathing_model_coverage_limits_journeys(self):
        for start,minutes in [(0,781),(120,779),(46800,1)]:
            with self.assertRaises(urllib.error.HTTPError) as c:self.plan(start,minutes)
            self.assertEqual(c.exception.code,400);self.assertIn('coverage',json.load(c.exception)['error'])
if __name__=='__main__':unittest.main()
