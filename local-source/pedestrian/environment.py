"""Repeat native CANOPY fields on the journey clock; repeated scenario, not weather forecast."""
from pathlib import Path
import gzip, json
import numpy as np
from collections import deque

class Environment:
    def __init__(self, root, config):
        scene=Path(root)/'scenes/imperial_corridor_8km'
        manifest=json.loads((scene/'physics/manifest.json').read_bytes())['arrays']
        traffic=json.loads((scene/'context/traffic-am.json').read_bytes())
        self.config=config; self.layers={}
        transport=json.loads((scene/'scene.json').read_bytes())['protocol_display']['npy_transport']
        for name in ['poll','temp']:
            spec=manifest[name+'.npy']; times=np.asarray(spec['time_s'])
            src=transport[name+'.npy'];decoded=[]
            for part in src['parts']:
                raw=np.frombuffer(gzip.decompress((scene/'physics'/part['file']).read_bytes()),dtype=src['meta']['descr'])
                q=src['meta'].get('quantization')
                values=np.where(raw==255,np.nan,raw.astype('float32')*q['scale']+q['offset']) if q else raw
                decoded.append(values.reshape(spec['shape'][-2:]))
            frames=np.stack(decoded)
            if name=='poll':
                mask_src=transport['masks/poll_invalid.npy']['parts'][0]['file']
                mask=np.frombuffer(gzip.decompress((scene/'physics'/mask_src).read_bytes()),dtype='u1').reshape(frames.shape[1:])
                frames[:,mask!=0]=np.nan
            self.layers[name]=(times,frames)
        self.invalid=np.frombuffer(gzip.decompress((scene/'physics/chunks/masks/temp_invalid/0000.gz').read_bytes()),dtype='u1').reshape(256,256)
        fills={}
        for name in ['temp','poll']:
            frames=self.layers[name][1]
            missing=~np.all(np.isfinite(frames),axis=0)
            if name=='temp':missing|=self.invalid!=0
            if missing.all():raise ValueError('No valid '+name+' cells to extend')
            h,w=missing.shape
            donors=np.arange(h*w).reshape(h,w);seen=~missing.copy()
            queue=deque(map(tuple,np.argwhere(seen)))
            while queue:
                y,x=queue.popleft()
                for yy,xx in [(y-1,x),(y+1,x),(y,x-1),(y,x+1)]:
                    if 0<=yy<h and 0<=xx<w and not seen[yy,xx]:
                        seen[yy,xx]=True;donors[yy,xx]=donors[y,x];queue.append((yy,xx))
            targets=np.flatnonzero(missing)
            sources=donors.ravel()[targets]
            for frame in frames:frame.ravel()[targets]=frame.ravel()[sources]
            fills[name]=list(zip(targets.tolist(),sources.tolist()))
        self.temperature_fill=fills['temp']
        self.pollution_fill=fills['poll']
        self.solar={};solar_meta={}
        for day in ['20260621','20261221']:
            key='solar_'+day+'.npy';spec=manifest[key];src=transport[key]
            frames=np.stack([np.frombuffer(gzip.decompress((scene/'physics'/part['file']).read_bytes()),dtype='u1').reshape(spec['shape'][-2:]) for part in src['parts']])
            if np.any(frames==255):raise ValueError('Missing solar irradiance data')
            self.solar[day]=(np.asarray(spec['time_s']),frames,src['meta']['quantization']['scale'])
            solar_meta[day]=dict(times_s=spec['time_s'],shape=spec['shape'][-2:],transport=src)
        self.horizon=min((traffic['frames']-1)*traffic['dt'],*(ts[-1] for ts,_ in self.layers.values()))
        self.metadata=dict(solar=solar_meta,solar_clock_origin_s=31800,solar_default_day='20260621',solar_warming_c_per_800=config.get('solar_warming_c_per_800',6.),pollution_fill=self.pollution_fill,pollution_fill_method="nearest valid cell by grid distance; illustrative extrapolation",temperature_fill=self.temperature_fill,temperature_fill_method="nearest valid cell by grid distance; illustrative extrapolation",horizon_s=float(self.horizon),replay=True,replay_blend_s=60,traffic_period_s=traffic['frames']*traffic['dt'],traffic_t0_s=traffic['t0'],traffic_dt_s=traffic['dt'],
            alignment='Scenario t=0 aligns first SUMO frame (08:50) with field t=0; not a jointly observed event.',
            layers={name:dict(times_s=ts.tolist(),shape=list(a.shape[1:]),cell_m=8192/a.shape[-1],transport=transport[name+'.npy']) for name,(ts,a) in self.layers.items()})

    def sample(self,name,point,seconds):
        if not np.isfinite(seconds) or seconds<0:return None
        ts,a=self.layers[name]; size=a.shape[-1]
        # Repeat the original sequence; journey and physiological time never reset.
        seconds=ts[0]+seconds%(ts[-1]-ts[0])
        i,j=np.floor((np.asarray(point[:2])+4096)/(8192/size)).astype(int)
        if not (0<=i<size and 0<=j<size):return None
        hi=min(int(np.searchsorted(ts,seconds,side='right')),len(ts)-1);lo=max(0,hi-1)
        f=(seconds-ts[lo])/(ts[hi]-ts[lo]) if hi!=lo else 0
        v=float(a[lo,j,i]) if f==0 else float(a[hi,j,i]) if f==1 else float(a[lo,j,i])*(1-f)+float(a[hi,j,i])*f
        u=max(0.0,min(1.0,(seconds-(ts[-1]-60))/60))
        blend=u*u*(3-2*u)
        if blend>0:v=v*(1-blend)+float(a[0,j,i])*blend
        return v if np.isfinite(v) else None

    def pollution(self,point,seconds):
        tracer=self.sample('poll',point,seconds)
        if tracer is None or tracer<0:return None
        c=self.config
        return float(c['min']+(c['max']-c['min'])*np.clip(np.log1p(tracer/c['tracer_scale'])/np.log1p(c['tracer_reference']/c['tracer_scale']),0,1))

    def sunlight(self,point,seconds,day='20260621'):
        if not np.isfinite(seconds) or seconds<0:return None
        times,a,scale=self.solar[day];size=a.shape[-1]
        i,j=np.floor((np.asarray(point[:2])+4096)/(8192/size)).astype(int)
        if not (0<=i<size and 0<=j<size):return None
        clock=31800+seconds
        if clock<times[0] or clock>times[-1]:return 0.
        hi=min(int(np.searchsorted(times,clock,side='right')),len(times)-1);lo=max(0,hi-1)
        f=(clock-times[lo])/(times[hi]-times[lo]) if hi!=lo else 0.
        return (float(a[lo,j,i])*(1-f)+float(a[hi,j,i])*f)*scale

    def thermal(self,point,seconds,day='20260621'):
        air=self.sample('temp',point,seconds);solar=self.sunlight(point,seconds,day)
        return None if air is None or solar is None else air+self.config.get('solar_warming_c_per_800',6.)*min(1.5,max(0.,solar/800.))
