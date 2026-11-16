import json,sys,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'pedestrian'),str(ROOT/'pedestrian/health_planning')]
from environment import Environment
from test_corridor_breathing import BreathingTests

class SolarTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.env=Environment(ROOT,json.loads((ROOT/'pedestrian/scenario.json').read_bytes()))
 def test_native_sampling_clock_and_day(self):
  e=self.env;p=[4.,4.];i=j=512
  for day,(times,a,scale) in e.solar.items():
   k=int(np.searchsorted(times,43200));t=float(times[k]-31800)
   self.assertAlmostEqual(e.sunlight(p,t,day),float(a[k,j,i])*scale)
   self.assertAlmostEqual(e.sunlight(p,t+300,day),(float(a[k,j,i])+float(a[k+1,j,i]))*.5*scale)
   self.assertEqual(e.sunlight(p,46800,day),0.)
   self.assertIsNone(e.sunlight([4096,0],t,day))
   self.assertFalse(np.any(a==255))
   self.assertGreater(np.unique(a[k]).size,2)
  self.assertNotEqual(e.sunlight(p,11400,'20260621'),e.sunlight(p,11400,'20261221'))
  self.assertNotEqual(e.sunlight(p,11400),e.sunlight(p,12000))
 def test_proxy(self):
  e=self.env;p=[4.,4.];t=11400
  self.assertAlmostEqual(e.thermal(p,t),e.sample('temp',p,t)+6*min(1.5,e.sunlight(p,t)/800))

class SolarCostTests(BreathingTests):
 def test_solar_changes_route_cost_but_not_cvae_features(self):
  from types import SimpleNamespace
  p=np.array([1700.,-500.,0.,0.]);cost=self.cost()
  cost.pollution_sampler=lambda p,t:15.
  cost.temperature_sampler=lambda p,t:28.
  cost.thermal_sampler=lambda p,t:28.
  state0,parts0,_=cost.wait(p,cost.initial,0,300)
  edge=SimpleNamespace(points=[p]);branch0=cost.branching_density(edge,cost.initial,0)
  calls=[]
  cost.thermal_sampler=lambda p,t:(calls.append((tuple(p),t)) or 34.)
  state1,parts1,_=cost.wait(p,cost.initial,0,300)
  self.assertGreater(parts1[0],parts0[0])
  self.assertGreater(cost.branching_density(edge,cost.initial,0),branch0)
  np.testing.assert_array_equal(self.runtime.br(state0),self.runtime.br(state1))
  self.assertEqual(calls[0],(tuple(p),1.))
  self.assertEqual(calls[-2][1],299.)

if __name__=='__main__':unittest.main()
