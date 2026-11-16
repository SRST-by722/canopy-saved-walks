"""Conservative crossing admission against immutable saved SUMO trajectories.

The whole crossing corridor must be clear for travel plus packet clearance.
Swept bounding discs cover vehicle bodies and motion between saved 1 s frames.
No synthetic connection is made between the last and first replay frame.
This only checks retained vehicles, in XY; it is not real-world safety assurance.
"""
from pathlib import Path
from bisect import bisect_right
import hashlib,json,math,struct,sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent/'dependencies'))
import shapely

VERSION=2
SPATIAL_MARGIN_M=1.4  # 0.4 m walker radius plus 1 m separation
TEMPORAL_BUFFER_S=1

def intervals(mask):
    transitions=np.diff(np.r_[False,mask,False].astype('int8'))
    return tuple(zip(np.flatnonzero(transitions==1).tolist(),np.flatnonzero(transitions==-1).tolist()))

class ClearWindows:
    def __init__(self,blocked,period=600.):
        self.blocked=tuple((float(a),float(b)) for a,b in blocked)
        self.period=float(period);self.ends=tuple(b for _,b in self.blocked)
        if self.period<=0 or any(not (0<=a<b<=period) for a,b in self.blocked):raise ValueError('Invalid traffic intervals')
        if any(self.blocked[i][1]>self.blocked[i+1][0] for i in range(len(self.blocked)-1)):raise ValueError('Unsorted traffic intervals')

    def conflict_end(self,start,duration):
        """End of the first occupied interval intersecting [start,start+duration)."""
        if not self.blocked:return None
        end=start+duration;cycle=math.floor(start/self.period)
        for c in range(cycle,math.floor(end/self.period)+1):
            base=c*self.period;i=bisect_right(self.ends,start-base+1e-9)
            if i<len(self.blocked):
                a,b=self.blocked[i]
                if base+a<end-1e-9:return base+b
        return None

    def clear(self,start,duration):return self.conflict_end(start,duration) is None

class TrafficGapGate:
    exact_entry=True  # stationary entrance packet can wait directly to this exact release
    def __init__(self,signal,windows):
        self.signal=signal;self.traffic=windows
        self.id=signal.id;self.program=signal.program;self.margin_s=signal.margin_s
    @property
    def windows(self):return self.signal.windows
    def permitted(self,entry,crossing_s):
        return self.signal.permitted(entry,crossing_s) and self.traffic.clear(entry,crossing_s+self.margin_s)
    def next_entry(self,arrival,crossing_s,deadline):
        entry=self.signal.next_entry(arrival,crossing_s,deadline)
        if self.traffic.blocked and crossing_s+self.margin_s>=self.traffic.period:return None
        while entry is not None:
            end=self.traffic.conflict_end(entry,crossing_s+self.margin_s)
            if end is None:return entry
            entry=self.signal.next_entry(end,crossing_s,deadline)
        return None
    def wait_details(self,arrival,crossing_s,deadline,entry):
        signal_entry=self.signal.next_entry(arrival,crossing_s,deadline)
        extra=max(0.,entry-signal_entry)
        return dict(wait_reason='traffic_gap_and_lights' if extra>1e-7 else 'pedestrian_light',
                    signal_only_wait_s=max(0.,signal_entry-arrival),traffic_extra_wait_s=extra)

def mark_sweeps(tree,positions,next_positions,radii):
    segments=shapely.linestrings(np.stack([positions,next_positions],axis=1))
    # GEOS dwithin on a degenerate two-identical-point LineString is unreliable.
    # Stopped cars/buses remain solid obstacles, represented by a point + radius.
    stationary=np.all(positions==next_positions,axis=1)
    segments[stationary]=shapely.points(positions[stationary])
    hits=tree.query(segments,predicate='dwithin',distance=radii)
    return np.unique(hits[1]) if hits.size else np.array([],dtype=int)

class RecordedTrafficGaps:
    def __init__(self,root,crossings):
        root=Path(root);folder=root/'scenes/imperial_corridor_8km/context'
        raw=(folder/'traffic-am.bin').read_bytes();meta_raw=(folder/'traffic-am.json').read_bytes();meta=json.loads(meta_raw)
        if meta['dt']!=1:raise ValueError('Traffic gap sampler requires the retained 1 second frames')
        self.period=meta['frames']*meta['dt'];self.crossings=crossings
        geometry=json.dumps([(c['id'],c['points']) for c in crossings],separators=(',',':')).encode()
        key=hashlib.sha256(raw+meta_raw+geometry+str((VERSION,SPATIAL_MARGIN_M,TEMPORAL_BUFFER_S)).encode()).hexdigest()
        cache=root/'pedestrian/cache/traffic-gap-occupancy.npz';blocked=None
        if cache.exists():
            try:
                with np.load(cache,allow_pickle=False) as data:
                    if str(data['key'])==key:blocked=data['blocked']
            except (OSError,ValueError,KeyError):pass
        if blocked is None:
            blocked=self.build(raw,meta,crossings)
            cache.parent.mkdir(parents=True,exist_ok=True)
            temp=cache.with_suffix('.tmp')
            with temp.open('wb') as stream:np.savez_compressed(stream,key=key,blocked=blocked)
            temp.replace(cache)
        if blocked.shape!=(len(crossings),meta['frames']):raise ValueError('Traffic occupancy shape mismatch')
        self.by_id={c['id']:ClearWindows(intervals(blocked[i]),self.period) for i,c in enumerate(crossings)}
        self.metadata=dict(mode='recorded_vehicle_gaps_plus_modelled_pedestrian_lights',period_s=self.period,
            traffic_sha256=hashlib.sha256(raw).hexdigest(),cache_key=key,spatial_margin_m=SPATIAL_MARGIN_M,
            temporal_buffer_s=TEMPORAL_BUFFER_S,clearance_s=2.,vehicle_shapes='Swept bounding discs: car 4.5 x 1.85 m; bus 11.5 x 2.5 m; same generic body sizes as viewer',
            crossings_with_recorded_conflicts=int(np.any(blocked,axis=1).sum()),crossings_checked=len(crossings),
            limitations='Retained simulated vehicle subset only; conservative XY footprints, no grade separation. Future saved motion is known. Lights do not control cars. Not real-world safety validation.')

    @staticmethod
    def build(raw,meta,crossings):
        frames=[];offset=0;dtype=np.dtype([('id','<u4'),('x','<f4'),('y','<f4'),('heading','<f4')])
        for _ in range(meta['frames']):
            count=struct.unpack_from('<I',raw,offset)[0];offset+=4
            frames.append(np.frombuffer(raw,dtype=dtype,count=count,offset=offset));offset+=count*16
        if offset!=len(raw):raise ValueError('Unexpected traffic bytes')
        tree=shapely.STRtree([shapely.LineString(np.asarray(c['points'])[:,:2]) for c in crossings])
        radii=np.array([math.hypot(11.5/2,2.5/2) if v['type']=='bus' else math.hypot(4.5/2,1.85/2) for v in meta['vehicles']])+SPATIAL_MARGIN_M
        mask=np.zeros((len(crossings),meta['frames']),dtype=bool)
        for k,frame in enumerate(frames):
            points=np.c_[frame['x'],frame['y']];following=points.copy()
            if k+1<len(frames):
                nxt=frames[k+1];lookup={int(v):i for i,v in enumerate(nxt['id'])}
                for i,vehicle in enumerate(frame['id']):
                    j=lookup.get(int(vehicle))
                    if j is not None:following[i]=[nxt['x'][j],nxt['y'][j]]
            # The last frame holds until replay resets. Never sweep a teleport across the map.
            hits=mark_sweeps(tree,points,following,radii[frame['id']]);mask[hits,k]=True
        original=mask.copy()
        for shift in range(1,TEMPORAL_BUFFER_S+1):mask|=np.roll(original,shift,axis=1)|np.roll(original,-shift,axis=1)
        return mask

    def export(self,ids,speed=4/3):
        lengths={c['id']:c['length_m'] for c in self.crossings}
        return {key:dict(period_s=self.period,blocked_intervals_s=self.by_id[key].blocked,
                        crossing_s=lengths[key]/speed,clearance_s=2.) for key in sorted(ids)}
