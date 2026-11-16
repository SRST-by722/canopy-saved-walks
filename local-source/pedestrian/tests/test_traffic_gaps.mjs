import test from 'node:test';
import assert from 'node:assert/strict';
import {trafficGapClear} from '../../viewer/3d/pedestrian/traffic-gaps.mjs';
test('full crossing and clearance, fractional entries and replay seam',()=>{
 const g={period_s:600,crossing_s:4,clearance_s:2,blocked_intervals_s:[[0,4],[598,600]]};
 for(const t of [0,3.9,593,595,599,1199,46199])assert.equal(trafficGapClear(g,t),false);
 for(const t of [4,592,604,46204])assert.equal(trafficGapClear(g,t),true);
 assert.equal(trafficGapClear(undefined,0),true);
});
