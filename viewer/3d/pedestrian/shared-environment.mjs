import {solarBracket,solarValue,sampleSolar,thermalProxy} from './solar-environment.mjs';
import {f16} from '../../npy.js';

export function bracket(times,t){
  if(!Number.isFinite(t)||t<times[0]||t>times.at(-1))return null;
  let hi=times.findIndex(v=>v>t);if(hi<0)hi=times.length-1;
  const lo=Math.max(0,hi-1);return [lo,hi,hi===lo?0:(t-times[lo])/(times[hi]-times[lo])];
}
export function replayTime(t,period){return Number.isFinite(t)&&t>=0&&period>0?t%period:NaN;}
export function replayBlend(layer,t){
  if(!layer.replay)return 0;
  const duration=Math.min(layer.replay_blend_s??60,layer.times_s.at(-1)-layer.times_s[0]);
  const u=Math.max(0,Math.min(1,(t-(layer.times_s.at(-1)-duration))/duration));
  return u*u*(3-2*u);
}
export function sampleField(layer,x,y,t,mask){
  if(layer.replay)t=layer.times_s[0]+replayTime(t,layer.times_s.at(-1)-layer.times_s[0]);
  const b=bracket(layer.times_s,t),[h,w]=layer.shape;
  const i=Math.floor((x+4096)/(8192/w)),j=Math.floor((y+4096)/(8192/h));
  if(!b||i<0||j<0||i>=w||j>=h||mask?.[j*w+i])return null;
  const [lo,hi,f]=b,a=layer.frames[lo][j*w+i],z=layer.frames[hi][j*w+i];
  let v=f===0?a:f===1?z:a*(1-f)+z*f;const blend=replayBlend(layer,t);if(blend>0)v=v*(1-blend)+layer.frames[0][j*w+i]*blend;return Number.isFinite(v)?v:null;
}
export function tracerToPM(v,c){return v===null||!Number.isFinite(v)||v<0?null:c.min+(c.max-c.min)*Math.max(0,Math.min(1,Math.log1p(v/c.tracer_scale)/Math.log1p(c.tracer_reference/c.tracer_scale)));}
export async function loadEnvironment(meta,config,onProgress=()=>{}){
  const base=new URL('../../../scenes/imperial_corridor_8km/physics/',import.meta.url);
  async function bytes(path){const r=await fetch(new URL(path,base));if(!r.ok)throw Error('Environmental field unavailable: '+path);return new Response(r.body.pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();}
  const layers=structuredClone(meta.layers),jobs=[];
  for(const l of Object.values(layers)){l.replay=meta.replay;l.replay_blend_s=meta.replay_blend_s??60;}
  for(const l of Object.values(layers)){l.frames=[];l.times_s.forEach((_,i)=>jobs.push(async()=>{const buf=await bytes(l.transport.parts[i].file),q=l.transport.meta.quantization;l.frames[i]=q?Float32Array.from(new Uint8Array(buf),v=>v===255?NaN:Math.fround(Math.fround(v*q.scale)+q.offset)):f16(new Uint16Array(buf));if(l.frames[i].length!==l.shape[0]*l.shape[1])throw Error('Field shape mismatch');}));}
  const solar=structuredClone(meta.solar),solarMixed=new Float32Array(1024*1024);let solarDay=meta.solar_default_day;
  for(const l of Object.values(solar)){l.frames=[];l.times_s.forEach((_,i)=>jobs.push(async()=>{l.frames[i]=new Uint8Array(await bytes(l.transport.parts[i].file));if(l.frames[i].length!==l.shape[0]*l.shape[1])throw Error('Solar field shape mismatch');}));}
  let cursor=0,done=0;await Promise.all(Array.from({length:3},async()=>{while(cursor<jobs.length){await jobs[cursor++]();onProgress(++done,jobs.length);}}));
  const mask=new Uint8Array(await bytes('chunks/masks/temp_invalid/0000.gz'));
  for(const [target,source] of meta.temperature_fill??[]){for(const frame of layers.temp.frames)frame[target]=frame[source];mask[target]=0;}
  const pollMask=new Uint8Array(await bytes('chunks/masks_poll_invalid_8m/0000.gz'));
  for(const frame of layers.poll.frames)for(let i=0;i<pollMask.length;i++)if(pollMask[i])frame[i]=NaN;
  for(const [target,source] of meta.pollution_fill??[])for(const frame of layers.poll.frames)frame[target]=frame[source];
  const mixed=new Float32Array(layers.poll.frames[0].length);
  return {meta,layers,solar,
    get solarDay(){return solarDay;},
    setSolarDay(day){if(!solar[day])throw Error('Unsupported solar day');solarDay=day;},
    solarFrame(t){const l=solar[solarDay],b=solarBracket(l.times_s,t,meta.solar_clock_origin_s);for(let i=0;i<solarMixed.length;i++)solarMixed[i]=solarValue(l,i,b)??NaN;return solarMixed;},
    sample(x,y,t){if(t<0||t>meta.horizon_s)return {pollution:null,temperature:null,tracer:null};const tracer=sampleField(layers.poll,x,y,t),temperature=sampleField(layers.temp,x,y,t,mask),sunlight=sampleSolar(solar[solarDay],x,y,t,meta.solar_clock_origin_s);return {tracer,pollution:tracerToPM(tracer,config),temperature,sunlight,thermal_proxy:thermalProxy(temperature,sunlight,meta.solar_warming_c_per_800)};},
    pollutionFrame(t){if(meta.replay)t=replayTime(t,layers.poll.times_s.at(-1));const b=bracket(layers.poll.times_s,t);if(!b)return null;const [lo,hi,f]=b,a=layers.poll.frames[lo],z=layers.poll.frames[hi];const blend=replayBlend(layers.poll,t);if(blend===0&&f===0)return a;if(blend===0&&f===1)return z;for(let i=0;i<mixed.length;i++){const v=f===0?a[i]:f===1?z[i]:a[i]*(1-f)+z[i]*f;mixed[i]=blend>0?v*(1-blend)+layers.poll.frames[0][i]*blend:v;}return mixed;}
  };
}
