import test from 'node:test';
import assert from 'node:assert/strict';
import {connectedEndpoints,destinationChoice} from '../viewer/3d/pedestrian/walking-endpoints.mjs';
const entries=[['start',[0,0]],['reachable',[10,0]],['isolated',[11,1]]];
const components={start:0,reachable:0,isolated:1};
test('disconnected path does not silently snap to the nearby reachable path',()=>{
  assert.deepEqual(destinationChoice(entries,components,'start',11,1),{node:null,reason:'disconnected'});
});
test('reachable destination accepted; same endpoint and outside network rejected',()=>{
  assert.deepEqual(destinationChoice(entries,components,'start',10,0),{node:'reachable',reason:null});
  assert.equal(destinationChoice(entries,components,'start',0,0).reason,'same');
  assert.equal(destinationChoice(entries,components,'start',100,100).reason,'outside');
  assert.equal(connectedEndpoints(components,'missing','also-missing'),false);
});
