"""Destination-guided bounded waves with fully simulated feasible incumbents.

Graph searches propose a timed feasible route and a frozen-environment route.
Every accepted candidate then propagates the original wave/CVAE history and
pedestrian gate fields. A bounded wave search refines their destination corridor.
This is an approximation, not globally optimal health routing on the full map.
"""
from collections import defaultdict
import heapq,math,time
import numpy as np
from zero_speed_history_wave import solve as wave_solve

def durations(edges):
    return {k:e.length/getattr(e,'walking_speed',4/3) for k,e in edges.items()}

def distances(weights,source,reverse=False):
    adjacent=defaultdict(list)
    for (u,v),w in weights.items():adjacent[v if reverse else u].append((u if reverse else v,w))
    queue=[(0.,source)];dist={source:0.};parents={}
    while queue:
        d,u=heapq.heappop(queue)
        if d!=dist[u]:continue
        for v,w in adjacent[u]:
            nd=d+w
            if nd<dist.get(v,math.inf):
                dist[v]=nd;parents[v]=u;heapq.heappush(queue,(nd,v))
    return dist,parents

def reconstruct(parents,origin,goal):
    if goal!=origin and goal not in parents:return None
    path=[];v=goal
    while v!=origin:
        u=parents[v];path.append((u,v));v=u
    return list(reversed(path))

def timed_path(edges,origin,goal,gates,departure,deadline):
    """FIFO earliest arrival, including actual signal windows and waiting."""
    travel=durations(edges);adjacent=defaultdict(list)
    for k in edges:adjacent[k[0]].append(k)
    queue=[(0.,origin)];arrivals={origin:0.};parents={}
    while queue:
        t,u=heapq.heappop(queue)
        if t!=arrivals[u]:continue
        if u==goal:return reconstruct(parents,origin,goal),t
        for k in adjacent[u]:
            start=departure+t
            if k in gates:start=gates[k].next_entry(start,travel[k],departure+deadline)
            if start is None:continue
            end=start-departure+travel[k]
            if end>deadline+1e-8:continue
            v=k[1]
            if end<arrivals.get(v,math.inf):
                arrivals[v]=end;parents[v]=u;heapq.heappush(queue,(end,v))
    return None,None

def feasible(path,travel,gates,departure,deadline):
    t=0.
    for k in path:
        start=departure+t
        if k in gates:start=gates[k].next_entry(start,travel[k],departure+deadline)
        if start is None:return False
        t=start-departure+travel[k]
        if t>deadline+1e-8:return False
    return True

def solve(nodes,edges,origin,goal,density,cost,*,gates=None,dt_s=.125,duration_s=1800.,max_records=12000,per_node=8,per_band=2,**unused):
    begun=time.perf_counter();gates=gates or {};travel=durations(edges)
    fastest,earliest=timed_path(edges,origin,goal,gates,cost.departure,duration_s)
    if not fastest:
        return None,dict(failure='journey_duration',records=0,graph_optimiser=True,
                         search_strategy='destination_guided_wave',search_complete=False)
    weights={k:travel[k]*density[k] for k in edges}
    forward,parents=distances(weights,origin);backward,_=distances(weights,goal,True)
    remaining,_=distances(travel,goal,True)
    candidates=[fastest]
    guided=reconstruct(parents,origin,goal)
    if not cost.neutral and guided and guided!=fastest and feasible(guided,travel,gates,cost.departure,duration_s):candidates.append(guided)
    options=dict(gates=gates,dt_s=dt_s,duration_s=duration_s,per_node=per_node,per_band=per_band)
    validated=[];attempts=[]
    for path in candidates:
        # Include reverse channels for the original junction impedance, while
        # the no-revisit rule prevents a chain from reflecting backwards.
        keys=set(path)|{(v,u) for u,v in path if (v,u) in edges}
        subset={k:edges[k] for k in keys};points={n:nodes[n] for k in keys for n in k}
        found,audit=wave_solve(points,subset,origin,goal,density,cost,**options,
                              max_records=max(len(path)+1,max_records),max_wave_time=math.inf)
        attempts.append(dict(kind='candidate',records=audit['records'],failure=audit['failure']))
        if found:validated.append((float(np.dot(audit['carried_parts'],[1,.25,.25])),found,audit))
    if not validated:
        return None,dict(failure='candidate_wave_validation',records=sum(a['records'] for a in attempts),
                         attempts=attempts,graph_optimiser=True,search_strategy='destination_guided_wave',search_complete=False)
    best=min(validated,key=lambda v:v[0]);refinement=None
    if not cost.neutral:
        # Permit modest guide-cost detours plus all feasible candidate edges.
        # This is a search domain, never a mutation of the walking network.
        threshold=forward[goal]*1.15+30.
        keys={k for k,w in weights.items() if forward.get(k[0],math.inf)+w+backward.get(k[1],math.inf)<=threshold}
        keys.update(k for path in candidates for k in path)
        keys.update((v,u) for u,v in list(keys) if (v,u) in edges)
        subset={k:edges[k] for k in keys};points={n:nodes[n] for k in keys for n in k}
        found,refinement=wave_solve(points,subset,origin,goal,density,cost,**options,
                                   max_records=min(max_records,3000),remaining_time=remaining,
                                   max_wave_time=best[0]*cost.reference_objective+dt_s)
        attempts.append(dict(kind='corridor',nodes=len(points),edges=len(subset),records=refinement['records'],failure=refinement['failure']))
        if found:
            candidate=(float(np.dot(refinement['carried_parts'],[1,.25,.25])),found,refinement)
            if candidate[0]<=best[0]:best=candidate
    _,path,audit=best
    audit.update(search_strategy='destination_guided_wave',search_complete=False,graph_optimiser=True,
                 candidate_generation='FIFO timed shortest path and frozen-environment guide; every candidate wave/CVAE validated',
                 earliest_arrival_s=earliest,attempts=attempts,
                 search_limited=bool(refinement and refinement['truncated']),
                 selected_from='corridor_wave' if audit is refinement else 'validated_candidate_wave',
                 failure=None,total_runtime_s=time.perf_counter()-begun,
                 scope='Best tested route within a bounded destination corridor; no global health-optimality claim')
    return path,audit
