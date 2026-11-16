import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'pedestrian/health_planning'))
from corridor_scenario import pollution, ScenarioCosts
from walking_cost_search import Edge
import json

class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.config=json.loads((Path(__file__).resolve().parents[2]/'pedestrian/scenario.json').read_text())
    def test_bounds_period_and_time_variation(self):
        rng=np.random.default_rng(42);points=rng.uniform(-4096,4096,(1000,2));t=rng.uniform(0,86400,1000)
        values=pollution(points,t,self.config)
        self.assertTrue(np.all((values>=6)&(values<=40)))
        np.testing.assert_allclose(values,pollution(points,t+180,self.config),atol=1e-10)
        self.assertGreater(np.max(np.abs(values-pollution(points,t+45,self.config))),10)
    def test_waiting_exposure_and_moving_cost_use_same_field(self):
        c=ScenarioCosts(0,{('a','b'):(0.,25.)},self.config);c.wait_value=(0.,25.)
        point=np.array([1700.,-500.,0.,0.]);state,parts,exposure=c.wait(point,0,0,40)
        times=np.linspace(0,40,40001);expected=np.trapezoid(pollution(np.broadcast_to(point,(len(times),4)),times,self.config),times)
        self.assertAlmostEqual(exposure,expected,delta=.2)
        self.assertAlmostEqual(parts[0],40+.05*exposure)
        e=Edge('a','b',np.array([point,point+[40,0,0,0]]),np.array([0.,40.]),'flat')
        state,parts,exposure=c.edge(e,0,0)
        self.assertEqual(state,30.)
        self.assertAlmostEqual(parts[0],30+.05*exposure)

if __name__=='__main__':unittest.main()
