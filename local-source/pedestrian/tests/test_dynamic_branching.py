import sys,unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'health_planning'))
from corridor_breathing import BreathingCosts
from test_destination_wave import Costs,network
from zero_speed_history_wave import solve

class DynamicBranchTests(unittest.TestCase):
 def test_local_position_absolute_time_and_missing(self):
  c=BreathingCosts.__new__(BreathingCosts);c.neutral=False;c.departure=600;c.config={};c.runtime=SimpleNamespace(mean=[10,22]);c.density=lambda state,t:state
  calls=[]
  c.pollution_sampler=lambda p,t:(calls.append((list(p),t)) or t/100)
  c.temperature_sampler=lambda p,t:26+p[0]
  e=SimpleNamespace(points=np.array([[5.,2.],[50.,20.]]))
  self.assertAlmostEqual(c.branching_density(e,2,30),1+.05*6.3+.25+.5)
  self.assertEqual(calls[-1],([5.,2.],630))
  self.assertNotEqual(c.branching_density(e,2,30),c.branching_density(e,2,90))
  c.temperature_sampler=lambda p,t:None
  self.assertAlmostEqual(c.branching_density(e,2,30),1+.315+.5+3)
  c.neutral=True;self.assertEqual(c.branching_density(e,2,30),1)
 def test_wave_uses_arrival_density_not_static_guide(self):
  n,e,d=network([('s','a',4),('a','g',4)])
  c=Costs();calls=[]
  def density(edge,state,elapsed):
   calls.append((edge.u,elapsed,state));return 1+elapsed
  c.branching_density=density
  path,a=solve(n,e,'s','g',d,c,dt_s=.125)
  self.assertEqual(path,[('s','a'),('a','g')])
  self.assertIn(('a',3.,3.),calls)
  self.assertEqual(a['trace'][-1]['branch_density'],4)
  self.assertAlmostEqual(a['trace'][-1]['branch_impedance'],2*(4/3)/4)
  self.assertGreater(a['rejections']['dynamic_branch_evaluations'],0)

if __name__=='__main__':unittest.main()
