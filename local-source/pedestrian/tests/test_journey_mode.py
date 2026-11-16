import sys,unittest
from pathlib import Path
from dataclasses import replace
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'pedestrian'),str(ROOT/'pedestrian/health_planning')]
from corridor_breathing import BreathingCosts
from destination_wave import solve
from test_destination_wave import network,Costs
from traffic_gaps import ClearWindows,TrafficGapGate
from walk_signal_schedule import WalkGate,WalkProgram

class SpeedCosts(Costs):
 def edge(self,e,state,elapsed):
  duration=e.length/e.walking_speed
  return state+duration,np.array([duration,0.,0.]),duration

class JourneyModeTests(unittest.TestCase):
 def test_wave_uses_speed_for_travel_and_full_gap(self):
  nodes,original,density=network([('s','g',6.)])
  gate=TrafficGapGate(WalkGate('gap',WalkProgram(1,100,10,origin_s=-1)),ClearWindows([(5,15)]))
  for speed,expected_wait in [(4/3,15.),(2.5,0.)]:
   edges={k:replace(e,walking_speed=speed) for k,e in original.items()}
   path,a=solve(nodes,edges,'s','g',density,SpeedCosts(),gates={('s','g'):gate},duration_s=60)
   self.assertEqual(path,[('s','g')]);self.assertAlmostEqual(a['trace'][-1]['wait_s'],expected_wait)
   self.assertAlmostEqual(a['trace'][-1]['physical_s'],expected_wait+6/speed)
   self.assertAlmostEqual(a['carried_parts'][0],expected_wait+6/speed)
  self.assertEqual(original['s','g'].walking_speed,4/3)
 def test_breathing_transition_samples_the_speed_correct_position(self):
  _,edges,_=network([('s','g',20.)]);e=replace(edges['s','g'],walking_speed=2.5)
  c=BreathingCosts.__new__(BreathingCosts);c.values={('s','g'):(0.,22.)}
  c.transition=lambda state,elapsed,duration,temperature,at:(duration,at(2.))
  duration,point=c.edge(e,None,10.)
  self.assertEqual(duration,8.);self.assertEqual(point[0],5.)

if __name__=='__main__':unittest.main()
