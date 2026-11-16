"""Real saved trajectories: independently recheck footprints for planned crossings."""
import sys,json,unittest,urllib.request,math,struct
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'pedestrian'),str(ROOT/'pedestrian/health_planning')]
from traffic_gaps import shapely

class TrafficApiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.base='http://127.0.0.1:8811';cls.meta=json.load(urllib.request.urlopen(cls.base+'/api/pedestrian/meta'))
  cls.crossings={c['id']:c for c in cls.meta['crossings']}
  folder=ROOT/'scenes/imperial_corridor_8km/context';meta=json.loads((folder/'traffic-am.json').read_bytes());raw=(folder/'traffic-am.bin').read_bytes()
  cls.frames=[];offset=0
  for _ in range(meta['frames']):
   count=struct.unpack_from('<I',raw,offset)[0];offset+=4
   rows=[struct.unpack_from('<Ifff',raw,offset+i*16) for i in range(count)];offset+=count*16
   cls.frames.append({v[0]:np.array(v[1:3]) for v in rows})
  cls.radii=[math.hypot(5.75,1.25) if v['type']=='bus' else math.hypot(2.25,.925) for v in meta['vehicles']]
 def plan(self,id,start,reverse=False,travel_mode='walk'):
  ends=self.crossings[id]['edge'];a,b=ends[::-1] if reverse else ends
  body=dict(origin=a,goal=b,departure_s=start,max_minutes=20,travel_mode=travel_mode)
  req=urllib.request.Request(self.base+'/api/pedestrian/plan',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
  return json.load(urllib.request.urlopen(req,timeout=180))
 def check_crossings(self,result):
  for route in result['routes']:
   for event in route['timeline']:
    if event['kind']!='Crossing':continue
    line=shapely.LineString(np.array(event['points'])[:,:2]);start=result['departure_s']+event['start'];end=result['departure_s']+event['end']+2
    # Recompute distance against every relevant vehicle, without the cached
    # occupancy table or spatial index used by the planner.
    for absolute in range(math.floor(start)-2,math.ceil(end)+2):
     if absolute+2<=start+1e-9 or absolute-1>=end-1e-9:continue
     k=absolute%600;current=self.frames[k];following=self.frames[k+1] if k<599 else current
     for vehicle,point in current.items():
      nxt=following.get(vehicle,point)
      sweep=shapely.Point(point) if np.array_equal(point,nxt) else shapely.LineString([point,nxt])
      self.assertGreater(shapely.distance(line,sweep),self.radii[vehicle]+1.4-1e-7,
                         f'Unsafe crossing {event["signal_id"]}, frame {k}, vehicle {vehicle}')
 def test_real_crossing_wait_and_cvae_at_replay_boundary(self):
  result=self.plan('canopy-walk-4264',590);route=result['routes'][1]
  self.assertEqual(route['wait_s'],88.);self.assertEqual(route['traffic_wait_s'],58.)
  self.assertEqual(route['timeline'][0]['wait_reason'],'traffic_gap_and_lights')
  self.assertEqual(route['breathing_profile'][1]['seconds'],10.) # CVAE update while held
  self.assertGreater(route['timeline'][0]['cost_end'],route['timeline'][0]['cost_start'])
  self.assertGreater(route['profile'][-1]['wait'],0)
  self.assertEqual(result['wave_audit'][1]['terminal_delay_added_s'],0.)
  self.assertEqual(result['wave_audit'][1]['trace'][-1]['physical_s'],route['duration_s'])
  self.check_crossings(result)
 def test_reverse_crossing_and_different_departure(self):
  result=self.plan('canopy-walk-4267',120,True)
  self.assertGreater(result['routes'][1]['traffic_wait_s'],0)
  self.check_crossings(result)
 def test_running_crossing_uses_running_duration_and_remains_clear(self):
  result=self.plan('canopy-walk-4264',590,travel_mode='run');route=result['routes'][1]
  self.assertEqual(result['travel_speed']['speed_m_s'],2.5)
  self.assertEqual(route['travel_mode'],'run')
  for event in route['timeline']:
   if event['kind']=='Crossing':
    expected=event['distance'][-1]/2.5
    self.assertAlmostEqual(event['end']-event['start'],expected)
    self.assertAlmostEqual(result['traffic_gaps'][event['signal_id']]['crossing_s'],expected)
  self.check_crossings(result)

if __name__=='__main__':unittest.main()
