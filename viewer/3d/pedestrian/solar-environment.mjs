// Clear-sky scenario clock, never the ten-minute traffic replay clock.
export function solarBracket(times,seconds,origin=31800){
  const t=origin+seconds;
  if(!Number.isFinite(t)||seconds<0)return null;
  if(t<times[0]||t>times.at(-1))return [];
  let hi=times.findIndex(v=>v>t);if(hi<0)hi=times.length-1;
  const lo=Math.max(0,hi-1);return [lo,hi,hi===lo?0:(t-times[lo])/(times[hi]-times[lo])];
}
export function solarValue(layer,index,b){
  if(!b)return null;if(!b.length)return 0;
  const [lo,hi,f]=b,a=layer.frames[lo][index],z=layer.frames[hi][index];
  if(a===255||z===255||a===undefined||z===undefined)return null;
  const q=layer.transport.meta.quantization;return (a*(1-f)+z*f)*q.scale+(q.offset??0);
}
export function sampleSolar(layer,x,y,seconds,origin=31800){
  const [h,w]=layer.shape,i=Math.floor((x+4096)*w/8192),j=Math.floor((y+4096)*h/8192);
  if(i<0||j<0||i>=w||j>=h)return null;
  return solarValue(layer,j*w+i,solarBracket(layer.times_s,seconds,origin));
}
export function thermalProxy(air,irradiance,warming=6){
  return Number.isFinite(air)&&Number.isFinite(irradiance)?air+warming*Math.max(0,Math.min(1.5,irradiance/800)):null;
}
