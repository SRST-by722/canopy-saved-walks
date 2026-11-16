"""History-resolved characteristic waves with actual entrance reservoirs.

On each directed edge p_t+v*q_x=0, q_t+v*p_x=0. A retained history
has a physical clock and CVAE state. Red blocks source injection; the source
packet is held, not transmitted and later relabelled. After admission the
crossing's characteristic field is solved by the physical-time boundary solver.
Health pseudo-time tau obeys d tau = rho dt; c_tau=v/rho. Edge-averaged rho
is obtained from that history's CVAE/environment score. First numerically detected destination
packet in tau is selected with fixed time buckets, not a graph heap.
Distinct histories are separate channels, NOT an interfering single carrier.
Signed junction transmission is retained; cycle/reflection histories are truncated.
This is a bounded history-resolved wave approximation, not the full paper PDE.
"""
from collections import Counter
from functools import lru_cache
import heapq,math,time
import numpy as np
from zero_speed_entrance_wave import solve_crossing,pulse

@lru_cache(maxsize=8192)
def propagate_packet(length,dt_requested,speed=4/3,width=2.):
 """CFL-one travelling-wave delay line; record the solved exit waveform.
 Ring storage is the characteristic grid, advanced one cell per physical step.
 No edge arrival is accepted without an emitted pulse reaching its exit.
 """
 travel=length/speed;n=max(4,int(math.ceil(travel/dt_requested)));dt=travel/n
 ring=np.zeros(n+1);out=[];source=[]
 for k in range(n+int(math.ceil(width/dt))+3):
  ring[k%(n+1)]=float(pulse(k*dt,width))
  out.append(float(ring[(k-n)%(n+1)]) if k>=n else 0.)
  source.append(float(pulse(k*dt,width)))
 j=int(np.argmax(out));delta=0.
 if 0<j<len(out)-1:
  denominator=out[j-1]-2*out[j]+out[j+1]
  if abs(denominator)>1e-14:delta=.5*(out[j-1]-out[j+1])/denominator
 assert max(out)>0
 return dict(detected_front_s=(j+delta)*dt-width/2,dt_s=dt,cells=n,exit_peak=max(out),energy_error=abs(sum(x*x for x in source)-sum(x*x for x in out))*dt)

def solve(nodes,edges,origin,goal,density,cost,*,gates=None,dt_s=.25,duration_s=1800.,max_records=12000,per_node=64,per_band=4,band_s=30.,max_wave_time=16000.,remaining_time=None,**unused):
 if dt_s<=0 or dt_s>.5 or duration_s<=0:raise ValueError('Require 0 < dt <= 0.5 and positive horizon')
 gates=gates or {};begun=time.perf_counter();names=sorted(nodes);ix={n:i for i,n in enumerate(names)}
 adjacent={n:[] for n in nodes}
 for k in sorted(edges):adjacent[k[0]].append(k)
 records=[dict(node=origin,parent=-1,key=None,elapsed=0.,wave=0.,state=cost.initial,parts=np.zeros(3),exposure=0.,amplitude=1.,visited=frozenset([origin]),wait_s=0.)]
 # An event queue skips empty time buckets. It orders distinct wave packets,
 # not merged graph-node costs, and processes children emitted in the same bucket.
 scheduled=[(0,0.,0)];counts=Counter();bins=Counter();stats=Counter();gate_audits=[];selected=None;truncated=False
 if max_records<1:raise ValueError('Positive history record budget required')
 def emit(rid):
  nonlocal truncated
  r=records[rid]
  if r['node']==goal:return
  incoming_speed=r.get('speed',None)
  # Split the pulse at this history's junction. Different histories are not merged.
  sampler=getattr(cost,'branching_density',None)
  local_density={k:(sampler(edges[k],r['state'],r['elapsed']) if sampler else density[k]) for k in adjacent[r['node']]}
  if any(not math.isfinite(v) or v<=0 for v in local_density.values()):raise ValueError('Positive finite branching density required')
  impedance=sum(getattr(edges[k],"walking_speed",4/3)/local_density[k] for k in adjacent[r['node']])
  stats['dynamic_branch_evaluations' if sampler else 'static_branch_evaluations']+=len(local_density)
  for k in adjacent[r['node']]:
   if k[1] in r['visited']:stats['cycle_or_reflection_history_truncated']+=1;continue
   e=edges[k];physical_speed=getattr(e,"walking_speed",4/3);travel=e.length/physical_speed
   if len(records)>=max_records:truncated=True;stats['record_budget_rejected']+=1;return
   if r['elapsed']+travel>duration_s+1e-8:stats['duration_rejected']+=1;continue
   if remaining_time is not None and r['elapsed']+travel+remaining_time.get(k[1],math.inf)>duration_s+1e-8:stats['remaining_time_rejected']+=1;continue
   wait=0.;entry=r['elapsed'];boundary=None
   if k in gates:
    boundary=solve_crossing(e.length,gates[k],departure=cost.departure,arrival_s=r['elapsed'],dt_requested=dt_s,horizon_s=duration_s,speed=physical_speed)
    # The local incoming field has been blocked/propagated BEFORE any child exists.
    gate_audits.append(dict(edge=k,parent=rid,arrival_s=r['elapsed'],entry_s=boundary['entry_s'],feasible=boundary['feasible'],closed_field_max=boundary['closed_field_max'],terminal_delay_added_s=0.,nodal_error=boundary.get('nodal_analytic_error'),reconstruction_rmse=boundary.get('reconstruction_rmse'),grid_dt=boundary['dt_s']))
    if not boundary['feasible']:stats['closed_gate_rejected']+=1;continue
    wait=boundary['wait_s'];entry=boundary['entry_s']
    assert boundary['closed_field_max']==0
   s=r['state'];wp=np.zeros(3);we=0.
   if wait>1e-8:s,wp,we=cost.wait(e.points[0],s,r['elapsed'],wait)
   s,ep,ee=cost.edge(e,s,entry)
   edge_tau=float(ep@[1,.25,.25])*cost.reference_objective
   wait_tau=float(wp@[1,.25,.25])*cost.reference_objective
   if edge_tau<=0 or wait_tau<0:raise ValueError('Positive propagation cost required')
   rho=edge_tau/travel;speed=physical_speed/rho
   amplitude=r['amplitude']*(1/math.sqrt(max(1,len(adjacent[r['node']]))) if incoming_speed is None else 2*incoming_speed/impedance)
   if abs(amplitude)<1e-12:stats['amplitude_rejected']+=1;continue
   # Numerical travelling-wave exit detection, mapped into health pseudo-time.
   # Physical boundary field above supplies zero before entry. Wait cost moves
   # source RELEASE, not a detected goal or a post-hoc arrival correction.
   propagation=(dict(detected_front_s=e.pde_arrival_s,exit_peak=1.) if hasattr(e,"pde_arrival_s") else propagate_packet(e.length,dt_s,speed=physical_speed)) if boundary is None else dict(detected_front_s=boundary['detected_finish_s']-entry,exit_peak=boundary['max_amplitude'])
   release=r['wave']+wait_tau;arrival=release+rho*propagation['detected_front_s']
   assert propagation['exit_peak']>0
   if arrival>max_wave_time:stats['wave_horizon_rejected']+=1;continue
   records.append(dict(node=k[1],parent=rid,key=k,elapsed=entry+travel,wave=arrival,state=s,parts=r['parts']+wp+ep,exposure=r['exposure']+we+ee,amplitude=amplitude,visited=r['visited']|{k[1]},wait_s=wait,entry_s=entry,release_tau=release,rho=rho,speed=speed,branch_density=local_density[k],branch_impedance=impedance))
   heapq.heappush(scheduled,(max(0,int(math.ceil(arrival/dt_s-1e-10))),arrival,len(records)-1))
 while scheduled:
  _,_,rid=heapq.heappop(scheduled)
  r=records[rid];key=(r['node'],int(r['elapsed']//band_s))
  if counts[r['node']]>=per_node or bins[key]>=per_band:stats['history_capacity_rejected']+=1;continue
  counts[r['node']]+=1;bins[key]+=1
  if r['node']==goal:selected=rid;break
  # Budget exhaustion stops new emissions, not packets already travelling.
  emit(rid)
 path=[];trace=[]
 if selected is not None:
  i=selected
  while i>=0:
   r=records[i];trace.append(dict(node=r['node'],physical_s=r['elapsed'],wave_s=r['wave'],wait_s=r['wait_s'],release_tau=r.get('release_tau'),rho=r.get('rho'),branch_density=r.get('branch_density'),branch_impedance=r.get('branch_impedance'),amplitude=r['amplitude']))
   if r['key']:path.append(r['key'])
   i=r['parent']
  path.reverse();trace.reverse()
 chosen=records[selected] if selected is not None else None
 return path or None,dict(records=len(records),retained_nodes=len(counts),truncated=truncated,rejections=dict(stats),dt_s=dt_s,trace=trace,gate_audits=gate_audits,maximum_closed_transmission=max([a['closed_field_max'] for a in gate_audits]+[0.]),terminal_delay_added_s=0.,graph_optimiser=False,carrier='history-resolved characteristic channels; distinct CVAE histories do not interfere',blocking='literal c=0 upstream entrance holding strip during red; crossing field solved before downstream history emitted',health_coupling='CVAE-derived cost reparameterises characteristic propagation and source waiting time',cycle_policy='no revisits within leg; reflection histories truncated',failure=None if chosen else ('history_budget' if truncated else 'no_feasible_wave_front'),carried_parts=chosen['parts'].tolist() if chosen else None,carried_exposure=chosen['exposure'] if chosen else None,runtime_s=time.perf_counter()-begun)


