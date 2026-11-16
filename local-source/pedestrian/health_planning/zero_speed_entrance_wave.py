"""Literal zero-speed entrance strip for the right-going wave characteristic.

w_t+c(x,t)w_x=0. c=0 in an upstream holding strip while red, c=v
inside the crossing. On admission c=v everywhere for this packet. The
initial source pulse is stored spatially, rather than prescribed by a held
boundary source clock. No extra walking distance: strip lies upstream of x=0.
CFL-one upwind is an exact shift after release. This is the same one-way
characteristic reduction as the reservoir comparator, not a general second-
order variable-speed wave equation with interference.
"""
import math
import numpy as np
from crossing_boundary_wave import pulse

def solve_crossing(length,gate,*,departure=0.,arrival_s=0.,speed=4/3,dt_requested=.25,horizon_s=7200.,pulse_width_s=2.,force_closed=False):
 if not all(math.isfinite(v) and v>0 for v in [length,speed,dt_requested,horizon_s,pulse_width_s]):raise ValueError('Positive finite inputs required')
 if not math.isfinite(arrival_s) or arrival_s<0 or not math.isfinite(departure):raise ValueError('Invalid clock')
 if pulse_width_s<4*dt_requested:raise ValueError('Pulse underresolved')
 if gate is not None and pulse_width_s>gate.margin_s+1e-8:raise ValueError('Packet tail exceeds clearance')
 travel=length/speed;n=max(4,math.ceil(travel/dt_requested));dx=length/n;dt=dx/speed;m=math.ceil(pulse_width_s/dt)
 x=np.arange(-m,n+1)*dx;u=np.asarray(pulse(-x/speed,pulse_width_s));u[x>0]=0.;initial=u.copy();t=arrival_s;entry=None;held=[];closed_max=0.;checks=0;zero_steps=0
 def advance(h,closed):
  nonlocal u
  velocity=np.full(len(u),speed)
  if closed:velocity[:m+1]=0.
  old=u.copy();u[1:]=old[1:]-velocity[1:]*h/dx*(old[1:]-old[:-1]);u[0]=0.
 if gate is not None and getattr(gate,'exact_entry',False) and not force_closed:
  # During the hold, velocity is zero throughout the stored packet and the
  # downstream field is identically zero. Its exact evolution is stationary;
  # skip empty clock steps, not any waiting cost or physiological evolution.
  release=gate.next_entry(departure+arrival_s,travel,departure+horizon_s)
  target=horizon_s if release is None else release-departure
  if target>arrival_s:
   held=[arrival_s,target];zero_steps=math.ceil((target-arrival_s)/dt);t=target
  if release is None:force_closed=True
 while t<=horizon_s+1e-9:
  checks+=1;allowed=not force_closed and (gate is None or gate.permitted(departure+t,travel))
  if allowed and t+travel<=horizon_s+1e-8:entry=t;break
  closed_max=max(closed_max,float(np.max(np.abs(u[m:]))))
  if not held or t-held[-1]>=5.-1e-8:held.append(t)
  if t>=horizon_s-1e-8:break
  step=min(dt,horizon_s-t)
  if gate is not None:
   phase=(departure+t-gate.program.origin_s)%gate.program.period
   for a,b,c in gate.windows:
    for event in (a,b,max(a,c-travel-gate.margin_s)):
     ahead=(event-phase)%gate.program.period
     if 1e-7<ahead<step:step=ahead
  advance(step,True);zero_steps+=1;t=round(t+step,10)
 result=dict(entry_s=entry,arrival_s=arrival_s,walking_seconds=travel,wait_s=None if entry is None else entry-arrival_s,finish_s=None if entry is None else entry+travel,n_cells=n,dx_m=dx,dt_s=dt,requested_dt_s=dt_requested,cfl=1.,permission_checks=checks,closed_field_max=closed_max,graph_optimiser=False,terminal_delay_added_s=0.,entrance_speed_red=0.,entrance_speed_green=speed,holding_strip_m=m*dx,zero_speed_steps=zero_steps,stored_packet_change=float(np.max(np.abs(u[:m+1]-initial[:m+1]))),scope='Zero-speed upstream holding strip; one-way wave characteristic; admitted packet continues',x_m=(np.arange(n+1)*dx).tolist(),held_times_s=held)
 if entry is None:return dict(result,feasible=False,failure='No admissible entry within horizon',wave_times_s=[arrival_s,horizon_s],right_field=[u[m:].tolist(),u[m:].tolist()])
 times=[];fields=[];inputs=[];outputs=[];error=0.
 for k in range(math.ceil((travel+pulse_width_s+2*dt)/dt)+1):
  if k:advance(dt,False)
  age=k*dt;times.append(entry+age);fields.append(u[m:].copy());inputs.append(u[m]);outputs.append(u[-1]);error=max(error,float(np.max(np.abs(u[m:]-pulse(age-np.arange(n+1)*dt,pulse_width_s)))))
 j=int(np.argmax(outputs));delta=0.
 if 0<j<len(outputs)-1:
  den=outputs[j-1]-2*outputs[j]+outputs[j+1]
  if abs(den)>1e-12:delta=.5*(outputs[j-1]-outputs[j+1])/den
 detected=times[j]+delta*dt-pulse_width_s/2;fields=np.array(fields);errors=[]
 for k in range(len(times)):errors.extend((.5*(fields[k,:-1]+fields[k,1:])-pulse(k*dt-(np.arange(n)+.5)*dt,pulse_width_s)).tolist())
 source_energy=float(np.sum(np.array(inputs)**2)*dt);exit_energy=float(np.sum(np.array(outputs)**2)*dt)
 return dict(result,feasible=True,wave_times_s=times,right_field=fields.tolist(),left_field_max=0.,max_amplitude=float(fields.max()),nodal_analytic_error=error,reconstruction_rmse=float(np.sqrt(np.mean(np.array(errors)**2))),detected_finish_s=detected,detection_error_s=detected-entry-travel,source_energy=source_energy,exit_energy=exit_energy,relative_energy_error=abs(exit_energy-source_energy)/max(source_energy,1e-15))
