import sys,json,unittest
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pedestrian'))
from environment import Environment

class SharedEnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.env=Environment(ROOT,json.loads((ROOT/'pedestrian/scenario.json').read_text()))
    def test_replay_across_boundaries_and_full_duration(self):
        for name in ['poll','temp']:
            _,a=self.env.layers[name]; valid=np.isfinite(a[0])&np.isfinite(a[1])
            if name=='temp':valid &= self.env.invalid==0
            j,i=np.argwhere(valid)[0];cell=8192/a.shape[-1];p=[-4096+(i+.5)*cell,-4096+(j+.5)*cell]
            for t in [0,15,599.9]:
                for shift in [600,1200,46200]:self.assertAlmostEqual(self.env.sample(name,p,t),self.env.sample(name,p,t+shift),places=6)
            self.assertIsNone(self.env.sample(name,p,-1))
    def test_smooth_boundary(self):
        for name in ['poll','temp']:
            ts,a=self.env.layers[name]
            valid=np.all(np.isfinite(a),axis=0)
            if name=='temp':valid &= self.env.invalid==0
            j,i=np.argwhere(valid & (a[0]!=a[-1]))[0]
            cell=8192/a.shape[-1];p=[-4096+(i+.5)*cell,-4096+(j+.5)*cell]
            for boundary in [600,1200,46800]:
                self.assertAlmostEqual(self.env.sample(name,p,boundary-.001),self.env.sample(name,p,boundary),places=5)
            native=float(a[-2,j,i]) if name=='poll' else (float(a[-2,j,i])+float(a[-1,j,i]))/2
            self.assertAlmostEqual(self.env.sample(name,p,570),(native+float(a[0,j,i]))/2,places=5)

    def test_native_time_and_coordinate_sampling(self):
        e=self.env
        for name in ['poll','temp']:
            ts,a=e.layers[name];valid=np.isfinite(a[0])&np.isfinite(a[1])
            if name=='temp':valid &= e.invalid==0
            j,i=np.argwhere(valid & (a[0]!=a[1]))[0];cell=8192/a.shape[-1];point=[-4096+(i+.5)*cell,-4096+(j+.5)*cell]
            self.assertAlmostEqual(e.sample(name,point,ts[0]),float(a[0,j,i]))
            self.assertAlmostEqual(e.sample(name,point,(ts[0]+ts[1])/2),(float(a[0,j,i])+float(a[1,j,i]))/2)
            self.assertNotEqual(e.sample(name,point,ts[0]),e.sample(name,point,ts[1]))
    def test_masked_and_outside_are_missing(self):
        j,i=np.argwhere(self.env.invalid!=0)[0]
        self.assertTrue(np.isfinite(self.env.sample('temp',[-4096+(i+.5)*32,-4096+(j+.5)*32],100)))
        self.assertTrue(np.isfinite(self.env.layers['temp'][1]).all())
        self.assertTrue(np.isfinite(self.env.layers['poll'][1]).all())
        for target,source in self.env.pollution_fill[::max(1,len(self.env.pollution_fill)//100)]:
            a=self.env.layers['poll'][1].reshape(len(self.env.layers['poll'][0]),-1)
            np.testing.assert_array_equal(a[:,target],a[:,source])
        self.assertIsNone(self.env.sample('poll',[4096,0],100))

if __name__=='__main__':unittest.main()
