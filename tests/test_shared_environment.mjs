import test from 'node:test';
import assert from 'node:assert/strict';
import {sampleField,tracerToPM,bracket,replayTime} from '../viewer/3d/pedestrian/shared-environment.mjs';
test('environment and traffic repeat while absolute journey seconds continue',()=>{
 const l={replay:true,times_s:[0,600],shape:[1,1],frames:[[10],[30]]};
 for(const t of [0,150,599.9])for(const cycle of [1,2,77])assert.ok(Math.abs(sampleField(l,0,0,t)-sampleField(l,0,0,t+600*cycle))<1e-8);
 assert.equal(sampleField(l,0,0,600),10);
 assert.equal(replayTime(1205,600),5);
 assert.equal(replayTime(46800,600),0);
 assert.equal(sampleField(l,0,0,-1),null);
});
test('shared field samples ENU position and interpolates seconds without looping',()=>{
 const l={times_s:[0,30],shape:[2,2],frames:[[1,2,3,4],[11,12,13,14]]};
 assert.equal(sampleField(l,-2048,-2048,15),6);
 assert.equal(sampleField(l,2048,-2048,15),7);
 assert.equal(sampleField(l,-2048,2048,15),8);
 assert.equal(sampleField(l,2048,2048,30),14);
 assert.equal(sampleField(l,4096,0,15),null);
 assert.equal(sampleField(l,0,0,31),null);
 assert.equal(sampleField(l,-2048,-2048,15,[1,0,0,0]),null);
 assert.equal(bracket([0,30],-1),null);
});
test('tracer conversion is labelled bounded scenario and preserves missing values',()=>{
 const c={min:6,max:40,tracer_scale:.001,tracer_reference:33.81};
 assert.equal(tracerToPM(0,c),6);assert.equal(tracerToPM(33.81,c),40);
 assert.equal(tracerToPM(null,c),null);assert.equal(tracerToPM(NaN,c),null);
});

test('final minute crossfade is continuous at each cycle boundary',()=>{
 const l={replay:true,times_s:[0,600],shape:[1,1],frames:[[10],[30]]};
 assert.equal(sampleField(l,0,0,540),28);
 assert.equal(sampleField(l,0,0,570),19.5);
 for(const end of [600,1200,46800])assert.ok(Math.abs(sampleField(l,0,0,end-.001)-sampleField(l,0,0,end))<1e-6);
 assert.equal(sampleField({...l,frames:[[NaN],[30]]},0,0,570),null);
});
