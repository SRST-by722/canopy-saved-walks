"""State-augmented Bellman street search, a discrete HJB extension.

An edge advances physical time, environmental accumulators and recurrent state.
The learned state is updated only at fixed five-minute boundaries. Costs use the
last available prediction within each bin (explicit one-bin response lag).
"""
import copy,heapq,json
from dataclasses import dataclass
import numpy as np
import pandas as pd
import torch
from state_cvae_model import StateCVAE

@dataclass
class PhysState:
    hidden: object
    last: object
    elapsed: float
    accumulated: object
    phase: float
    updates: int

class Runtime:
    def __init__(self,out,seed=42,particles=16):
        self.out=out;self.particles=particles
        d=json.loads((out/'scaler.json').read_text());self.mean=np.array(d['mean']);self.scale=np.array(d['scale'])
        saved=torch.load(out/'state_cvae.pt',weights_only=True);self.model=StateCVAE();self.model.load_state_dict(saved['state_dict']);self.model.eval()
        self.eps=torch.tensor(np.random.default_rng(seed).normal(size=(400,particles,4)),dtype=torch.float32)
        self.start=pd.Timestamp('2022-05-08 23:00:00',tz='UTC')
        self.data=pd.read_csv(out/'inh010_Non-Winter_five_minutes.csv',index_col=0,parse_dates=True)
        self.columns=d['columns'][:8]
        past=self.data.loc[self.data.index<=self.start]
        # Feature fill is causal last observation, then training mean. Never targets.
        allx=self.data[self.columns].ffill().fillna(dict(zip(self.columns,self.mean[:8])))
        self.feature_data=allx
        ix=pd.date_range(self.start-pd.Timedelta(minutes=55),self.start,freq='5min')
        hist=past.reindex(ix);valid=hist[self.columns+['br_avg']].notna()
        filled=past[self.columns+['br_avg']].ffill().reindex(ix).fillna(dict(zip(self.columns+['br_avg'],self.mean)))
        norm=(filled.to_numpy()-self.mean)/self.scale
        with torch.no_grad():h,last=self.model.warm(torch.tensor(norm[None,:,:8],dtype=torch.float32).repeat(particles,1,1),torch.tensor(norm[None,:,8],dtype=torch.float32).repeat(particles,1))
        self.initial=PhysState(h,last,0.,np.zeros(8),0.,0)
        self.history_audit=dict(history_start=str(ix[0]),history_end=str(ix[-1]),missing_history_cells=int((~valid).sum().sum()),missing_BR_bins=int((~valid.br_avg).sum()),fallback='past-only forward-fill then training mean; no missingness features, provisional inference mismatch')
        self.states={0:self.initial};self.replay=[]
        state=self.initial
        for k in range(288):
            stamp=self.start+pd.Timedelta(minutes=5*(k+1));features=self.features(stamp)
            state=self.advance(state,features,300.)
            self.states[(k+1)*300]=state;self.replay.append(dict(timestamp=stamp.isoformat(),mean_br=float(self.br(state).mean()),sd_latent=float(self.br(state).std(ddof=1))))

    def features(self,stamp):
        stamp=pd.Timestamp(stamp)
        if stamp.tzinfo is None:stamp=stamp.tz_localize('UTC')
        index=self.feature_data.index.get_indexer([stamp],method='pad')[0]
        x=self.feature_data.iloc[max(index,0)].to_numpy(float).copy()
        hour=stamp.tz_convert('Europe/London').hour+stamp.minute/60
        x[6:]=[np.sin(hour*2*np.pi/24),np.cos(hour*2*np.pi/24)]
        return x

    def br(self,state):return state.last[:,0].numpy()*self.scale[8]+self.mean[8]

    def advance(self,state,features,duration):
        """Piecewise-constant covariates; partition invariant across street edges."""
        h,last=state.hidden,state.last;elapsed=state.elapsed;phase=state.phase;acc=state.accumulated.copy();updates=state.updates
        remaining=float(duration)
        while remaining>1e-8:
            take=min(remaining,300-phase);acc+=np.asarray(features)*take;phase+=take;elapsed+=take;remaining-=take
            if phase>=300-1e-7:
                xx=torch.tensor(((acc/300-self.mean[:8])/self.scale[:8])[None,:],dtype=torch.float32).repeat(self.particles,1)
                with torch.no_grad():_,_,(h,last),_=self.model.step(xx,(h,last),self.eps[updates])
                updates+=1;phase=0.;acc=np.zeros(8)
        return PhysState(h,last,elapsed,acc,phase,updates)

class RouteCosts:
    def __init__(self,runtime,field,departure,source_hour,scale,reference_objective,reference_duration,baseline):
        self.runtime=runtime;self.field=field;self.departure=departure;self.source_hour=source_hour;self.scale=scale
        self.reference_objective=reference_objective;self.reference_duration=reference_duration;self.baseline=baseline
        self.offset=int((pd.Timestamp(f'2022-05-09 {source_hour:02d}:00',tz='UTC')-runtime.start).total_seconds())
        self.initial=runtime.states[self.offset]

    def breathing_density(self,state,elapsed):
        slot=min(len(self.baseline)-1,int((self.offset+elapsed)//1800));b=self.baseline[slot];br=self.runtime.br(state)
        outside=np.maximum(np.maximum(b['q10']-br,br-b['q90']),0)/b['scale']
        # Additive pointwise latent spread penalty, distinct from paired full-route SD.
        return float(outside.mean()+.5*outside.std(ddof=1))

    def edge(self,edge,state,elapsed):
        total=edge.length/(4/3);bounds=np.unique(np.r_[0.,np.arange(np.floor(elapsed/25)+1,np.ceil((elapsed+total)/25))*25-elapsed,total])
        bounds=bounds[(bounds>=0)&(bounds<=total)];mid=(bounds[:-1]+bounds[1:])/2;dt=np.diff(bounds)
        points=edge.at(mid*(4/3));seconds=self.departure+elapsed+mid
        pm=self.field.sample(points,seconds)[0];temp=self.field.temperature(points,seconds)
        env=float(np.sum(dt*(1+.5*pm/self.scale))/self.reference_objective)
        thermal=float(np.sum(dt*((np.maximum(18-temp,0)/5)**2+(np.maximum(temp-26,0)/5)**2))/self.reference_duration)
        breathing=0.;nextstate=state
        for j,duration in enumerate(dt):
            left=float(duration)
            stamp=self.runtime.start+pd.Timedelta(seconds=self.offset+elapsed+mid[j])
            x=self.runtime.features(stamp);x[0]=pm[j];x[1]=temp[j]
            while left>1e-8:
                take=min(left,300-nextstate.phase)
                breathing+=take*self.breathing_density(nextstate,nextstate.elapsed-self.offset)/self.reference_duration
                nextstate=self.runtime.advance(nextstate,x,take);left-=take
        return nextstate,np.array([env,thermal,breathing]),float(np.sum(dt*pm)/60)

    def path(self,path,edges):
        state=self.initial;elapsed=0.;parts=np.zeros(3);exposure=0
        for key in path:
            state,c,e=self.edge(edges[key],state,elapsed);parts+=c;exposure+=e;elapsed+=edges[key].length/(4/3)
        return parts,exposure,state

def bellman_search(graph,edges,origin,goal,costs,lower_distance,max_distance,max_exposure,breathing=True,cap=3,budget=1800):
    """Forward labels realize Bellman transitions in (node,t,h,accumulator).

    Retained states are never merged. Per-node/time-bin cap and expansion budget
    make this an approximate search, not an exact continuous HJB solution.
    """
    labels=[dict(node=origin,path=[],length=0.,parts=np.zeros(3),exposure=0.,state=costs.initial,value=0.)]
    frontier=[(lower_distance[origin]/(4/3)/costs.reference_objective,0)];groups={(origin,0):[0]};active={0};goals=[];audit=[];expanded=0;pruned=0
    while frontier and expanded<budget:
        _,i=heapq.heappop(frontier)
        if i not in active:continue
        a=labels[i];expanded+=1
        if a['node']==goal:goals.append(i);continue
        seen={k[0] for k in a['path']}|{a['node']}
        for key in graph.get(a['node'],[]):
            if key[1] in seen:continue
            length=a['length']+edges[key].length
            if length+lower_distance.get(key[1],np.inf)>max_distance+1e-8:continue
            state,part,exposure=costs.edge(edges[key],a['state'],a['length']/(4/3));exposure+=a['exposure']
            if exposure>max_exposure+1e-8:continue
            parts=a['parts']+part;value=float(parts[0]+.25*parts[1]+(.25*parts[2] if breathing else 0))
            j=len(labels);labels.append(dict(node=key[1],path=a['path']+[key],length=length,parts=parts,exposure=exposure,state=state,value=value))
            groupkey=(key[1],int(length/(4/3)/60));group=groups.setdefault(groupkey,[]);group.append(j);group.sort(key=lambda q:(labels[q]['value'],q));drop=group[cap:];del group[cap:]
            for q in drop:active.discard(q)
            pruned+=len(drop)
            if j in group:
                active.add(j);heuristic=lower_distance[key[1]]/(4/3)/costs.reference_objective
                heapq.heappush(frontier,(value+heuristic,j))
            audit.append(dict(label=j,parent=i,node=key[1],elapsed_s=length/(4/3),parts=parts.tolist(),value=value,exposure=exposure,state_norm=float(state.hidden.norm()),mean_br=float(costs.runtime.br(state).mean()),phase=state.phase,updates=state.updates,retained=j in group))
    goals=list(set(goals)|{i for i,a in enumerate(labels) if a['node']==goal})
    result=min((labels[i] for i in goals),key=lambda a:a['value']) if goals else None
    if result is not None:result={**result,'terminal_paths':[labels[i]['path'] for i in goals]}
    return result,dict(expanded=expanded,generated=len(labels),goal_labels=len(goals),history_pruned=pruned,remaining_frontier=len(frontier),stop='budget' if expanded>=budget else 'exhausted',full_network_nodes=len(graph)),audit
