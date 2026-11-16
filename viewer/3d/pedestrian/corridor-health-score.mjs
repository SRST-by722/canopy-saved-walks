import { sample } from './imperial-route-plots.mjs';
// Proposed research index. Reference concentration is not an instantaneous safety threshold.
export function healthDetails({pollution,temperature,breathing,reference,thermal_proxy=temperature}) {
  if (![pollution,temperature,thermal_proxy,breathing,reference?.lower,reference?.upper,reference?.scale].every(Number.isFinite) || pollution<0 || breathing<=0 || reference.lower<=0 || reference.upper<reference.lower || reference.scale<=0) return null;
  const p=pollution/15, t=Math.max(18-thermal_proxy,thermal_proxy-26,0)/8;
  // Display sensitivity gain; does not change the empirical reference band.
  const b=1.5*Math.max(reference.lower-breathing,breathing-reference.upper,0)/reference.scale;
  const burdens={pollution:.35*p*p,temperature:.15*t*t,breathing:.50*b*b};
  const total=Object.values(burdens).reduce((a,b)=>a+b,0);
  const score=100*Math.exp(-Math.log(100/90)*total);
  // Shares of the combined loss, not separate causal health effects.
  const contributions=Object.fromEntries(Object.entries(burdens).map(([key,value])=>[key,total>0?(100-score)*value/total:0]));
  return {score,burdens,contributions};
}
export function currentHealthScore(input){return healthDetails(input)?.score??null;}
export function referenceAt(route,seconds){
  const rows=route.breathing_reference;
  if(!rows?.length||seconds<0||seconds>route.duration_s)return null;
  return rows.findLast(row=>row.seconds<=seconds)??null;
}
export function routeHealthScore(route,seconds){
  if(!route.profile?.length||!route.breathing_profile?.length)return null;
  const t=Math.max(0,Math.min(seconds,route.duration_s));
  return currentHealthScore({pollution:sample(route.profile,t,'pollution'),temperature:sample(route.profile,t,'temperature'),thermal_proxy:sample(route.profile,t,route.profile[0].thermal_proxy===undefined?'temperature':'thermal_proxy'),breathing:sample(route.breathing_profile,t,'breathing',true),reference:referenceAt(route,t)});
}
