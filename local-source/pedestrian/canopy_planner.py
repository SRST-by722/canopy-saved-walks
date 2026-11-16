"""CANOPY providers for the retained pedestrian wave/CVAE planner."""
from pathlib import Path
import gzip, hashlib, heapq, json
import numpy as np
import torch
from imperial_pedestrian import CorridorPlanner
from walking_cost_search import Edge
from walk_signal_schedule import WalkGate, WalkProgram
from state_cvae_routing import Runtime
from destination_wave import solve as destination_wave_solve
from environment import Environment
from traffic_gaps import RecordedTrafficGaps, TrafficGapGate

# Fixed scenario presets, not estimates of an individual's exercise capacity.
TRAVEL_MODES={'walk':dict(label='Walking',speed_m_s=4/3,speed_km_h=4.8),
              'run':dict(label='Running',speed_m_s=2.5,speed_km_h=9.)}

class CanopyPlanner(CorridorPlanner):
    solve_route=staticmethod(destination_wave_solve)
    def __init__(self, root):
        self.root=Path(root); self.folder=self.root/'pedestrian/generated'
        self.network=json.loads((self.folder/'network.json').read_bytes())
        self.nodes=self.network['nodes'];self.edges={};self.values={};self.gates={}
        self.scenario=json.loads((self.root/'pedestrian/scenario.json').read_bytes())
        model=self.root/'pedestrian/private/breathing_model'
        torch.set_num_threads(2)
        self.runtime=Runtime(model,42,16)
        self.baseline=json.loads((model/'personal_baseline.json').read_bytes())['bins']
        self.model_identity={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in model.iterdir() if p.is_file()}
        context=self.root/'scenes/imperial_corridor_8km/physics/chunks'
        self.temperature=np.frombuffer(gzip.decompress((context/'temp/0010.gz').read_bytes()),dtype='<f2').reshape(256,256)
        self.invalid=np.frombuffer(gzip.decompress((context/'masks/temp_invalid/0000.gz').read_bytes()),dtype='u1').reshape(256,256)
        self.environment=Environment(self.root,self.scenario)
        self.environment.horizon=max(self.runtime.states)-self.scenario['breathing_history_offset_s']
        self.environment.metadata['horizon_s']=self.environment.horizon
        self.display_temperatures={};self.missing_edges=0
        for row in self.network['edges']:
            points=np.asarray(row['points']);distance=np.asarray(row['distance'])
            marks=np.linspace(0,distance[-1],max(2,int(np.ceil(distance[-1]/2))+1))
            sampled=np.c_[np.interp(marks,distance,points[:,0]),np.interp(marks,distance,points[:,1])]
            samples=[self.sample_temperature(p) for p in sampled]
            valid=all(v is not None for v in samples)
            temp=float(np.mean(samples)) if valid else float(self.runtime.mean[1])
            if not valid:self.missing_edges+=1
            for u,v,pts,dist in [(row['u'],row['v'],points,distance),(row['v'],row['u'],points[::-1],distance[-1]-distance[::-1])]:
                self.edges[u,v]=Edge(u,v,np.c_[pts,np.zeros(len(pts))],dist,row['name'])
                self.values[u,v]=(0.,temp)
                self.display_temperatures[u,v]=temp if valid else None
        self.component={n:i for i,c in enumerate(self.network['components']) for n in c}
        self.wait_values={tuple(np.round(p[:2],4)):(0.,self.sample_temperature(p) if self.sample_temperature(p) is not None else float(self.runtime.mean[1])) for p in self.nodes.values()}
        for c in self.network['crossings']:
            for key in [tuple(c['edge']),tuple(c['edge'][::-1])]:self.gates[key]=WalkGate(c['id'],WalkProgram(**c['program']))
        choices=[c for c in self.network['crossings'] if c['both_pavement_approaches']]
        choices.sort(key=lambda c: np.linalg.norm(np.asarray(self.nodes[c['edge'][0]][:2])-[1776,-848]) + (10000 if len(self.network['components'][c['component']])<30 else 0))
        # Prefer a default walk with valid native temperature; this does not prune the routable graph.
        adj={n:[] for n in self.nodes}
        for (u,v),e in self.edges.items():
            if self.display_temperatures[u,v] is not None:adj[u].append((v,e.length))
        crossing=choices[0];origin=crossing['edge'][0];goal=crossing['edge'][1]
        for candidate in choices:
            start=candidate['edge'][0]
            if not adj[start]:continue
            queue=[(0.,start)];distances={start:0.};found=None
            while queue:
                d,n=heapq.heappop(queue)
                if d>distances[n]:continue
                if d>=180:found=n;break
                for v,length in adj[n]:
                    nd=d+length
                    if nd<distances.get(v,float('inf')):distances[v]=nd;heapq.heappush(queue,(nd,v))
            if found is not None:
                crossing=candidate;origin=start;goal=found;break
        self.examples=[dict(id='canopy_walk',label='Canopy mapped walk',edge=[origin,goal]),dict(id='canopy_crossing',label='Canopy crossing',edge=crossing['edge'])]
        self.traffic_gaps=RecordedTrafficGaps(self.root,self.network['crossings'])
        self.gates={key:TrafficGapGate(gate,self.traffic_gaps.by_id[gate.id]) for key,gate in self.gates.items()}

    def sample_temperature(self,point,seconds=0):
        return self.environment.sample('temp',point,seconds)

    def sample_pollution(self,point,seconds):
        return self.environment.pollution(point,seconds)

    def sample_thermal(self,point,seconds):
        return self.environment.thermal(point,seconds,getattr(self,'solar_day','20260621'))

    def metadata(self):
        return dict(scene_id='imperial_corridor_8km',nodes=self.nodes,roads=[r['points'] for r in self.network['edges']],
            node_components=self.component,road_components=[self.component[r['u']] for r in self.network['edges']],
            crossings=self.network['crossings'],summary=self.network['summary'],example=self.examples[0]['edge'],examples=self.examples,
            journey_horizon_s=self.environment.horizon,environment=self.environment.metadata,pollution_scenario=self.scenario,
            cvae_enabled=True,model_identity=self.model_identity,provenance=self.network['provenance'],traffic_gap_policy=self.traffic_gaps.metadata,travel_modes=TRAVEL_MODES,
            missing_temperature_edges=self.missing_edges,
            limits='CANOPY mapped paths; geometric connectivity, not surveyed access. Modelled pedestrian lights plus conservative gap checks against retained recorded cars; vehicles remain unchanged. Time-aligned native tracer and temperature at 8 m above ground; tracer-derived PM2.5 is uncalibrated. Missing temperature uses training-mean model input and unavailable temperature/health display.')

    def plan(self,request):
        mode=request.get('travel_mode','walk')
        if not isinstance(mode,str) or mode not in TRAVEL_MODES:raise ValueError('Choose walking or running before the journey')
        speed=TRAVEL_MODES[mode]['speed_m_s']
        self.solar_day=request.get('solar_day','20260621')
        if self.solar_day not in self.environment.solar:raise ValueError('Unsupported solar day')
        departure=float(request.get('departure_s',0));cap=float(request.get('max_minutes',self.environment.horizon/60))*60
        if not np.isfinite(departure+cap) or departure+cap>self.environment.horizon+1e-7:
            raise ValueError(f'Maximum journey duration exceeds breathing-model coverage: {max(0,self.environment.horizon-departure)/60:g} minutes remain. Environmental replay does not shorten this limit.')
        result=super().plan(dict(request,max_minutes=cap/60,walking_speed_m_s=speed))
        for route in result['routes']:
            route.update(travel_mode=mode,speed_m_s=speed)
            if mode=='run':
                for event in route['timeline']:
                    if event['kind']=='Walking':event['kind']='Running'
            # Export only reference summaries; raw participant observations remain private.
            offset=self.scenario['breathing_history_offset_s']+departure
            boundaries=[0.]+[float(t-offset) for t in np.arange((int(offset//1800)+1)*1800,offset+route['duration_s']+1e-7,1800)]
            route['breathing_reference']=[]
            for elapsed in boundaries:
                index=min(len(self.baseline)-1,int((offset+elapsed)//1800))
                b=self.baseline[index]
                route['breathing_reference'].append(dict(seconds=elapsed,lower=b['q10'],upper=b['q90'],scale=max(b['scale'],.1),mode=b['mode'],count=b['count']))
            # Re-sample the native field at the actual replay positions, retaining masked data as null.
            missing=0
            for sample in route['profile']:
                t=sample['seconds'];event=next((e for e in route['timeline'] if e['start']<=t<e['end']),route['timeline'][-1])
                if event['kind']=='Waiting':point=event['points'][0]
                else:
                    f=min(1,max(0,(t-event['start'])/(event['end']-event['start'])));target=f*event['distance'][-1]
                    point=[np.interp(target,event['distance'],np.array(event['points'])[:,j]) for j in range(2)]
                sample['temperature']=self.sample_temperature(point,result['departure_s']+t)
                sample['pollution']=self.sample_pollution(point,result['departure_s']+t)
                sample['sunlight']=self.environment.sunlight(point,result['departure_s']+t,self.solar_day)
                sample['thermal_proxy']=self.sample_thermal(point,result['departure_s']+t)
                sample['tracer']=self.environment.sample('poll',point,result['departure_s']+t)
                missing+=sample['temperature'] is None
            route['missing_temperature_samples']=missing
        result['environment_mode']=self.scenario['description']
        result['environment']=self.environment.metadata
        result['solar_day']=self.solar_day
        result['breathing_model']['limitations']=self.scenario['description']+' Recorded activity/humidity template; missing field input uses training mean plus routing penalty.'
        result['travel_mode']=mode;result['travel_speed']=TRAVEL_MODES[mode]
        result['breathing_model']['activity_mode']='recorded_template_not_running_calibrated'
        result['breathing_model']['limitations']+=' Journey mode changes physical speed and timing only; activity, steps and personal reference remain recorded templates. Running physiology is not calibrated.'
        for audit in result['wave_audit']:audit['health_coupling']=self.scenario['description']
        result['network_source']=self.network['provenance']
        result['signal_mode']='modelled_pedestrian_plus_recorded_vehicle_gaps'
        result['traffic_gap_policy']=self.traffic_gaps.metadata
        selected=result['routes'][1]
        ids={self.gates[tuple(k)].id for k in selected['edge_keys'] if tuple(k) in self.gates}
        result['traffic_gaps']=self.traffic_gaps.export(ids,speed)
        return result
