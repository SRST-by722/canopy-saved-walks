"""Synthetic pollution and time-integrated pedestrian scenario costs."""
import numpy as np

def pollution(points,seconds,config):
    p=np.asarray(points);s=config
    return s['baseline']+s['spatial_amplitude']*(.5+.5*np.sin(p[...,0]/s['x_scale_m']+p[...,1]/s['y_scale_m']))+s['pulse_amplitude']*(.5+.5*np.sin(2*np.pi*np.asarray(seconds)/s['period_s']-p[...,0]/s['drift_scale_m']))

class ScenarioCosts:
    initial=0.
    reference_objective=1.
    def __init__(self,departure,values,config,neutral=False):
        self.departure,self.values,self.config,self.neutral=departure,values,config,neutral
    def integrate(self,points,seconds,duration,temperature):
        pm=pollution(points,seconds,self.config)
        rho=np.ones_like(pm) if self.neutral else 1.+.5*pm/10.+.25*(max(temperature-26.,18.-temperature,0.)/5)**2
        return np.array([float(np.mean(rho)*duration),0.,0.]),float(np.mean(pm)*duration)
    def edge(self,e,state,elapsed):
        duration=e.length/(4/3);n=max(1,int(np.ceil(duration/2)));t=(np.arange(n)+.5)*duration/n
        parts,exposure=self.integrate(e.at(t*(4/3)),self.departure+elapsed+t,duration,self.values[e.u,e.v][1])
        return state+duration,parts,exposure
    def wait(self,point,state,elapsed,duration):
        n=max(1,int(np.ceil(duration/2)));t=(np.arange(n)+.5)*duration/n
        parts,exposure=self.integrate(np.broadcast_to(point,(n,len(point))),self.departure+elapsed+t,duration,self.wait_value[1])
        return state+duration,parts,exposure
