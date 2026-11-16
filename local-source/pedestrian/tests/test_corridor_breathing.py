import sys,json,unittest
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pedestrian/health_planning'))
from state_cvae_routing import Runtime
from corridor_breathing import BreathingCosts

class BreathingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder=ROOT/'pedestrian/private/breathing_model'
        torch.set_num_threads(2)
        cls.runtime=Runtime(folder,42,16)
        cls.baseline=json.loads((folder/'personal_baseline.json').read_text())['bins']
        cls.config=json.loads((ROOT/'pedestrian/scenario.json').read_text())
    def cost(self,departure=0,config=None):
        cost=BreathingCosts(departure,{},config or self.config,self.runtime,self.baseline)
        cost.wait_value=(0.,25.)
        return cost
    def test_five_minute_updates_and_waiting_history(self):
        c=self.cost();p=np.array([1700.,-500.,0.,0.]);before=self.runtime.br(c.initial).copy()
        state,parts,_=c.wait(p,c.initial,0,299)
        np.testing.assert_array_equal(self.runtime.br(state),before)
        state,_,_=c.wait(p,state,299,1)
        self.assertEqual(state.updates,c.initial.updates+1)
        self.assertGreater(np.max(np.abs(self.runtime.br(state)-before)),1e-5)
        np.testing.assert_array_equal(self.runtime.br(c.initial),before)
        self.assertGreaterEqual(parts[2],0)
    def test_partition_invariance_and_environment_response(self):
        c=self.cost();p=np.array([1700.,-500.,0.,0.])
        whole,parts,_=c.wait(p,c.initial,0,600)
        state,a,_=c.wait(p,c.initial,0,240);split,b,_=c.wait(p,state,240,360)
        np.testing.assert_allclose(self.runtime.br(whole),self.runtime.br(split),atol=1e-6)
        np.testing.assert_allclose(parts,a+b,atol=1e-6)
        predictions=[]
        for value in [6.,40.]:
            cost=self.cost(config=dict(self.config,baseline=value,spatial_amplitude=0.,pulse_amplitude=0.))
            state,_,_=cost.wait(p,cost.initial,0,600);predictions.append(self.runtime.br(state))
        self.assertGreater(np.max(np.abs(predictions[0]-predictions[1])),1e-5)
    def test_departure_phase_crosses_boundary_at_correct_time(self):
        c=self.cost(240);c.trace=[c.prediction(c.initial,0)]
        state,_,_=c.wait(np.array([1700.,-500.,0.,0.]),c.initial,0,90)
        self.assertAlmostEqual(c.trace[1]['seconds'],60)
        self.assertEqual(state.updates,c.initial.updates+1)

if __name__=='__main__':unittest.main()
