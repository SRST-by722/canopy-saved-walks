import test from 'node:test';
import assert from 'node:assert/strict';
import {sampleSolar,thermalProxy} from '../../viewer/3d/pedestrian/solar-environment.mjs';
import {healthDetails} from '../../viewer/3d/pedestrian/corridor-health-score.mjs';
const layer={times_s:[31800,32400,33000],shape:[1,2],frames:[[0,10],[40,20],[0,0]],transport:{meta:{quantization:{scale:2,offset:0}}}};
test('solar uses departure clock, position and interpolates without a ten minute repeat',()=>{
 assert.equal(sampleSolar(layer,-2000,0,0),0);
 assert.equal(sampleSolar(layer,-2000,0,300),40);
 assert.equal(sampleSolar(layer,-2000,0,600),80);
 assert.equal(sampleSolar(layer,2000,0,600),40);
 assert.equal(sampleSolar(layer,2000,0,1201),0);
 assert.equal(sampleSolar(layer,4096,0,0),null);
 assert.equal(sampleSolar(layer,0,0,-1),null);
});
test('sunlight changes thermal burden in context; missing irradiance cannot improve score',()=>{
 const score=(air,sun)=>healthDetails({pollution:10,temperature:air,thermal_proxy:thermalProxy(air,sun),breathing:18,reference:{lower:15,upper:20,scale:5}});
 assert.equal(thermalProxy(24,800),30);
 assert.ok(score(28,800).score<score(28,0).score);
 assert.ok(score(12,800).score>score(12,0).score);
 assert.equal(score(24,null),null);
 assert.equal(thermalProxy(24,0),24);
});
