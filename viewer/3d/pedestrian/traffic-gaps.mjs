// Same half-open periodic blocked intervals used by the backend crossing gate.
export function trafficGapClear(gap,time){
  if(!gap)return true;
  const duration=gap.crossing_s+gap.clearance_s,end=time+duration,period=gap.period_s;
  for(let cycle=Math.floor(time/period);cycle<=Math.floor(end/period);cycle++){
    for(const [a,b] of gap.blocked_intervals_s)
      if(cycle*period+b>time+1e-9&&cycle*period+a<end-1e-9)return false;
  }
  return true;
}
