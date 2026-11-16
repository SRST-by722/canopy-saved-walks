"""Physical-time wave PDE with a held source packet and direct entrance gate.

p_t + v*q_x = 0; q_t + v*p_x = 0. Characteristics w+ = p+q,
w- = p-q travel at +/-v. The right-going incoming packet is stored in a
boundary reservoir while entry is closed. Its source age advances only after
admission. There is zero injected field while closed, not a delayed goal label.

For this single interval, w- has zero incoming data at the far boundary.
Uniform-grid characteristic stepping at CFL=1 is an exact nodal shift. This
is a crossing-scale physical-time prototype, NOT the old cost-time network
PDE, a junction optimisation algorithm, or a passive reflecting wall model.
"""
import math
import numpy as np


def pulse(age,width):
    age=np.asarray(age,dtype=float)
    return np.where((age>=0)&(age<=width),np.sin(np.pi*np.clip(age,0,width)/width)**2,0.)


def solve_crossing(length,gate,*,departure=0.,arrival_s=0.,speed=4/3,
                   dt_requested=.25,horizon_s=7200.,pulse_width_s=2.,
                   force_closed=False):
    values=[length,speed,dt_requested,horizon_s,pulse_width_s]
    if not all(math.isfinite(x) and x>0 for x in values):raise ValueError('Positive finite solver inputs required')
    if not math.isfinite(arrival_s) or arrival_s<0 or not math.isfinite(departure):raise ValueError('Invalid physical clock')
    if pulse_width_s<4*dt_requested:raise ValueError('Pulse needs at least four time intervals')
    if gate is not None and pulse_width_s>gate.margin_s+1e-8:raise ValueError('Packet tail must fit within the clearance allowance')
    travel=length/speed;n=max(4,math.ceil(travel/dt_requested));dx=length/n;dt=dx/speed
    x=np.linspace(0,length,n+1);right=np.zeros(n+1);left=np.zeros(n+1)
    t=float(arrival_s);held=[];entry=None;checks=0;closed_field_max=0.
    # Event alignment is only for known schedule boundaries. No next-entry or
    # goal-delay routine is used. Permission is evaluated at the current clock.
    while t<=horizon_s+1e-9:
        allowed=not force_closed and (gate is None or gate.permitted(departure+t,travel))
        checks+=1
        if allowed and t+travel<=horizon_s+1e-8:entry=t;break
        closed_field_max=max(closed_field_max,float(np.max(np.abs(right))))
        if not held or t-held[-1]>=5.-1e-8:held.append(t)
        if t>=horizon_s-1e-8:break
        step=min(dt_requested,horizon_s-t)
        if gate is not None:
            phase=(departure+t-gate.program.origin_s)%gate.program.period
            for a,b,c in gate.windows:
                for event in (a,b,max(a,c-travel-gate.margin_s)):
                    ahead=(event-phase)%gate.program.period
                    if 1e-7<ahead<step:step=ahead
        if step<=1e-9:raise ArithmeticError('Clock stalled')
        t=round(t+step,10)
    result=dict(entry_s=entry,arrival_s=arrival_s,walking_seconds=travel,
                wait_s=None if entry is None else entry-arrival_s,
                finish_s=None if entry is None else entry+travel,
                n_cells=n,dx_m=dx,dt_s=dt,requested_dt_s=dt_requested,cfl=1.,
                permission_checks=checks,closed_field_max=closed_field_max,
                graph_optimiser=False,terminal_delay_added_s=0.,
                source_reservoir='Packet source age frozen at zero before admission',
                clock='Physical seconds; wave speed equals walking speed',
                scope='One-way excited scalar wave on one crossing, absorbing exterior; not full network health optimisation')
    if entry is None:
        return dict(result,feasible=False,failure='No admissible entry within horizon',
                    x_m=x.tolist(),wave_times_s=[arrival_s,horizon_s],right_field=[right.tolist(),right.tolist()],held_times_s=held)
    # One admitted cohort may finish even when permission for NEW entry closes.
    # No spatial speed is zeroed after admission and the outgoing end absorbs.
    count=math.ceil((travel+pulse_width_s+2*dt)/dt)
    times=[];fields=[];incoming=[];outgoing=[];max_error=0.
    for k in range(count+1):
        age=k*dt
        if k:
            right[1:]=right[:-1].copy();left[:-1]=left[1:].copy()
        right[0]=float(pulse(age,pulse_width_s));left[-1]=0.
        times.append(entry+age);fields.append(right.copy());incoming.append(right[0]);outgoing.append(right[-1])
        exact=pulse(age-x/speed,pulse_width_s)
        max_error=max(max_error,float(np.max(np.abs(right-exact))))
    fields=np.array(fields);times=np.array(times);outgoing=np.array(outgoing);incoming=np.array(incoming)
    if not np.isfinite(fields).all() or np.max(np.abs(fields))>1+1e-10:raise ArithmeticError('Unstable field')
    # Peak timing from the SOLVED destination waveform, not entry + travel.
    j=int(np.argmax(outgoing));delta=0.
    if 0<j<len(outgoing)-1:
        den=outgoing[j-1]-2*outgoing[j]+outgoing[j+1]
        if abs(den)>1e-12:delta=.5*(outgoing[j-1]-outgoing[j+1])/den
    detected=times[j]+delta*dt-pulse_width_s/2
    # Compare piecewise-linear spatial reconstruction at half-grid positions.
    mids=(x[:-1]+x[1:])/2;errors=[]
    for k,age in enumerate(times-entry):
        errors.extend((.5*(fields[k,:-1]+fields[k,1:])-pulse(age-mids/speed,pulse_width_s)).tolist())
    source_energy=float(np.sum(incoming**2)*dt);exit_energy=float(np.sum(outgoing**2)*dt)
    return dict(result,feasible=True,held_times_s=held,x_m=x.tolist(),wave_times_s=times.tolist(),
                right_field=fields.tolist(),left_field_max=float(np.max(np.abs(left))),
                max_amplitude=float(np.max(np.abs(fields))),nodal_analytic_error=max_error,
                reconstruction_rmse=float(np.sqrt(np.mean(np.array(errors)**2))),
                detected_finish_s=float(detected),detection_error_s=float(detected-entry-travel),
                source_energy=source_energy,exit_energy=exit_energy,
                relative_energy_error=abs(exit_energy-source_energy)/max(source_energy,1e-15))
