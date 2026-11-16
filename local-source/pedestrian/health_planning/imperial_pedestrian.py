"""Corridor adapter for the retained wave and pedestrian gate implementation.

Uses a labelled synthetic PM2.5 scenario and retained temperature snapshots.

"""

import json, math, time
from dataclasses import replace

from pathlib import Path

import numpy as np

from walking_cost_search import Edge

from zero_speed_history_wave import solve

from walk_signal_schedule import WalkProgram, WalkGate

from corridor_scenario import pollution
from corridor_breathing import BreathingCosts
from state_cvae_routing import Runtime
import torch, hashlib

RUN='pedestrian_reconstruction_20261103_v1'

class CorridorPlanner:

    def __init__(self,root):

        self.root=Path(root);self.folder=self.root/'project/imperial_corridor_8km/runs'/RUN

        self.network=json.loads((self.folder/'network.json').read_text())

        self.nodes=self.network['nodes'];self.edges={};self.values={};self.gates={}

        for r in self.network['edges']:

            pts=np.c_[r['points'],np.zeros((len(r['points']),2))];ds=np.array(r['distance'])

            for u,v,p,d in [(r['u'],r['v'],pts,ds),(r['v'],r['u'],pts[::-1],ds[-1]-ds[::-1])]:

                self.edges[u,v]=Edge(u,v,p,d,r['name']);self.values[u,v]=(r['tracer'],r['temperature'])

        self.component={n:i for i,c in enumerate(self.network['components']) for n in c}

        for c in self.network['crossings']:

            for k in [tuple(c['edge']),tuple(c['edge'][::-1])]:self.gates[k]=WalkGate(c['id'],WalkProgram(**c['program']))

        # Temperature waiting samples use the retained native grid at the endpoint.

        import gzip

        source=self.root/'project/imperial_corridor_8km/input/published_20261103'

        transport=json.loads((source/'transport.json').read_text())

        def load(name):

            meta=transport[name]['meta']

            return np.frombuffer(gzip.decompress((source/(name.replace('/','_')+'.gz')).read_bytes()),dtype=meta['descr']).reshape(meta['shape'][-2:])

        temp=load('temp.npy');xy=np.array(list(self.nodes.values()))[:,:2]

        ij=np.floor((xy+4096)/(8192/temp.shape[0])).astype(int).clip(0,temp.shape[0]-1)

        self.wait_values={tuple(np.round(p[:2],4)):(0.,float(temp[j,i])) for p,(i,j) in zip(self.nodes.values(),ij)}

        self.scenario=json.loads((self.root/'project/imperial_corridor_8km/configs/pedestrian_demo.json').read_text())
        model_dir=self.root/'project/imperial_corridor_8km/input/breathing_model'
        torch.set_num_threads(2)
        self.runtime=Runtime(model_dir,42,16)
        self.baseline=json.loads((model_dir/'personal_baseline.json').read_text())['bins']
        self.model_identity={name:hashlib.sha256((model_dir/name).read_bytes()).hexdigest() for name in ['state_cvae.pt','scaler.json','inh010_Non-Winter_five_minutes.csv','personal_baseline.json']}


    def metadata(self):

        degree={n:0 for n in self.nodes}

        for u,v in self.edges:degree[u]+=1

        examples=[c for c in self.network['crossings'] if c.get('both_pavement_approaches')]

        examples.sort(key=lambda c:(c['component'],abs(c['points'][0][0]-1776)+abs(c['points'][0][1]+848)))

        choices=[dict(id=c['id'],label=f'Crossing example {i+1}',edge=c['edge']) for i,c in enumerate(examples[:20])]

        longer=self.folder/'longer-route.json'

        if longer.exists():

            request=json.loads(longer.read_text())['request']

            choices.append(dict(id='longer_walk',label='Longer pavement walk',edge=[request['origin'],request['goal']]))

        return dict(journey_horizon_s=max(self.runtime.states)-self.scenario['breathing_history_offset_s'],scene_id='imperial_corridor_8km',nodes=self.nodes,crossings=self.network['crossings'],summary=self.network['summary'],example=examples[0]['edge'],examples=choices,roads=[r['points'] for r in self.network['edges']],cvae_enabled=True,breathing_model=dict(participant='INH010',update_interval_s=300,history_offset_s=self.scenario['breathing_history_offset_s'],inputs_sha256=self.model_identity),pollution_scenario=self.scenario,limits=self.scenario['description'])

    def plan(self,request):

        o=request.get('origin');g=request.get('goal');departure=float(request.get('departure_s',0));cap=float(request.get('max_minutes',30))*60

        if o not in self.nodes or g not in self.nodes or o==g:raise ValueError('Choose two different pedestrian nodes')

        if self.component[o]!=self.component[g]:raise ValueError('These endpoints are in disconnected pavement components. Unsupported gaps have not been bridged.')

        if not math.isfinite(departure) or departure<0 or not math.isfinite(cap) or cap<60:raise ValueError('Choose a finite start time of zero or later and a maximum journey duration of at least 1 minute')

        if departure+cap+self.scenario['breathing_history_offset_s']>max(self.runtime.states):raise ValueError(f'Maximum journey duration exceeds breathing-model coverage at this start time: {max(0, (max(self.runtime.states)-self.scenario["breathing_history_offset_s"]-departure)/60):.1f} minutes remain')

        ns={n:p for n,p in self.nodes.items() if self.component[n]==self.component[o]}

        speed=float(request.get('walking_speed_m_s',4/3))
        if not math.isfinite(speed) or speed<=0:raise ValueError('Positive finite travel speed required')
        # Request-local copies: switching modes never modifies the stored network.
        es={k:replace(e,walking_speed=speed) for k,e in self.edges.items() if k[0] in ns}

        routes=[];audits=[];begun=time.perf_counter()

        for neutral in [True,False]:

            cost=BreathingCosts(departure,self.values,self.scenario,self.runtime,self.baseline,neutral)
            cost.thermal_sampler=getattr(self,'sample_thermal',None)
            cost.temperature_sampler=getattr(self,'sample_temperature',None)
            cost.pollution_sampler=getattr(self,'sample_pollution',None)

            cost.wait=lambda point,state,elapsed,duration,c=cost:self._wait(c,point,state,elapsed,duration)

            # Departure guide for candidate shortlisting only; wave junctions use
            # cost.branching_density at each retained history arrival.
            if cost.thermal_sampler is not None:
                # The solar-aware guide uses departure conditions; dynamic junctions
                # still re-evaluate each candidate at its own arrival time.
                density={k:cost.branching_density(e,cost.initial,0) for k,e in es.items()}
            else:
                initial_burden=cost.density(cost.initial,0)
                density={k:(1. if neutral else 1.+.05*float((self.sample_pollution(e.points[len(e.points)//2],departure) if hasattr(self,'sample_pollution') else pollution(e.points[len(e.points)//2],departure,self.scenario)) or 40.)+.25*(max(self.values[k][1]-26.,18.-self.values[k][1],0.)/5)**2+.25*initial_burden+(self.scenario.get('missing_temperature_penalty',3.) if getattr(self,'display_temperatures',{}).get(k,0) is None else 0.)) for k,e in es.items()}

            route_solver=getattr(self,'solve_route',solve)
            path,a=route_solver(ns,es,o,g,density,cost,gates=self.gates,dt_s=.125,duration_s=cap,max_records=12000,per_node=8,per_band=2,max_wave_time=32000)

            a['health_coupling']='Position/time sampled environment and CVAE history in propagation and junction impedance';a['carrier']='History-resolved characteristic wave channels'

            if not path:
                if a['failure']=='journey_duration':raise ValueError('No walking route including pedestrian-light waits fits the maximum journey duration. Increase the duration or choose a nearer destination.')
                raise ValueError('The route search could not validate a complete walking route: '+str(a['failure']))

            elapsed=0.;timeline=[];parts=np.zeros(3);exposure=0.;state=cost.initial
            cost.trace=[cost.prediction(state,0.)]

            for key in path:

                e=es[key];travel=e.length/e.walking_speed

                if key in self.gates:

                    entry=self.gates[key].next_entry(departure+elapsed,travel,departure+cap)

                    wait=entry-departure-elapsed

                    if wait>1e-8:

                        state,v,x=cost.wait(e.points[0],state,elapsed,wait);parts+=v;exposure+=x

                        details=self.gates[key].wait_details(departure+elapsed,travel,departure+cap,entry) if hasattr(self.gates[key],'wait_details') else dict(wait_reason='pedestrian_light',signal_only_wait_s=wait,traffic_extra_wait_s=0.)
                        timeline.append(dict(kind='Waiting',start=elapsed,end=elapsed+wait,points=[e.points[0,:3].tolist()],signal_id=self.gates[key].id,cost_start=float((parts-v)@[1,.25,.25]),cost_end=float(parts@[1,.25,.25]),temperature=cost.wait_value[1],**details));elapsed+=wait

                    assert self.gates[key].permitted(departure+elapsed,travel)

                state,v,x=cost.edge(e,state,elapsed);parts+=v;exposure+=x

                timeline.append(dict(kind='Crossing' if key in self.gates else 'Walking',signal_id=self.gates[key].id if key in self.gates else None,start=elapsed,end=elapsed+travel,points=e.points[:,:3].tolist(),distance=e.distance.tolist(),cost_start=float((parts-v)@[1,.25,.25]),cost_end=float(parts@[1,.25,.25]),temperature=self.values[key][1]));elapsed+=travel

            np.testing.assert_allclose(parts,a['carried_parts'],atol=1e-7)

            assert elapsed<=cap+1e-7

            cost.trace.append(cost.prediction(state,elapsed))
            profile=[];distance=0.;waiting=0.

            for event in timeline:

                duration=event['end']-event['start']

                for local in np.linspace(0,duration,max(2,int(np.ceil(duration/2))+1)):

                    fraction=local/duration;stamp=event['start']+local

                    if event['kind']=='Waiting':point=np.asarray(event['points'][0]);dist=distance;waited=waiting+local

                    else:

                        target=fraction*event['distance'][-1]

                        point=np.array([np.interp(target,event['distance'],np.asarray(event['points'])[:,j]) for j in range(2)])

                        dist=distance+target;waited=waiting

                    profile.append(dict(seconds=stamp,pollution=float(pollution(point,departure+stamp,self.scenario)),temperature=event['temperature'],distance=dist,wait=waited,health_cost=event['cost_start']+fraction*(event['cost_end']-event['cost_start'])))

                if event['kind']=='Waiting':waiting+=duration

                else:distance+=event['distance'][-1]

            routes.append(dict(traffic_wait_s=sum(e.get('traffic_extra_wait_s',0.) for e in timeline),breathing_profile=cost.trace,components=dict(environment_seconds=float(parts[0]),breathing_seconds=float(.25*parts[2])),profile=profile,label='Time reference + lights' if neutral else 'Environmental + CVAE wave + lights',edge_keys=path,timeline=timeline,duration_s=elapsed,wait_s=sum(e['end']-e['start'] for e in timeline if e['kind']=='Waiting'),score=float(parts@[1,.25,.25]),pollution_integral_ug_s_m3=exposure,points=[p for k in path for p in es[k].points[:,:3].tolist()]))

            audits.append(a)

        return dict(routes=routes,departure_s=departure,seconds=time.perf_counter()-begun,signal_mode='modelled_pedestrian',wave_audit=audits,vehicle_agents=False,cvae_enabled=True,breathing_model=dict(participant='INH010',update_interval_s=300,history_offset_s=self.scenario['breathing_history_offset_s'],inputs_sha256=self.model_identity,history_audit=self.runtime.history_audit,limitations='Synthetic pollution and frozen temperature; remaining covariates use recorded template. Research scenario, not validated physiology.'),pollution_scenario=self.scenario,environment_mode='synthetic PM2.5 with retained frozen temperature',planner_version=self.scenario['id'])

    def _wait(self,cost,point,state,elapsed,duration):

        cost.wait_value=self.wait_values[tuple(np.round(point[:2],4))]

        return BreathingCosts.wait(cost,point,state,elapsed,duration)

