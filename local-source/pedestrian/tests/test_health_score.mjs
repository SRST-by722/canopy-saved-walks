import test from 'node:test';
import assert from 'node:assert/strict';
import { currentHealthScore, routeHealthScore, healthDetails, referenceAt } from '../../viewer/3d/pedestrian/corridor-health-score.mjs';

const conditions = { pollution: 10, temperature: 22, breathing: 16, reference: {lower:14,upper:18,scale:2} };
test('masked native temperature cannot become a zero or fabricated health score', () => {
  const route = { breathing_reference:[{seconds:0,lower:14,upper:18,scale:2}],duration_s: 20, profile: [{seconds: 0,pollution:10,temperature:22},{seconds:10,pollution:10,temperature:null},{seconds:20,pollution:10,temperature:22}],breathing_profile:[{seconds:0,breathing:16}]};
  assert.equal(routeHealthScore(route,10),null);
  assert.equal(routeHealthScore(route,15),null);
  assert(routeHealthScore(route,0)>90);
  assert.equal(routeHealthScore(route,0),routeHealthScore(route,20));
});
test('each current condition affects score and ordinary scenario scores stay high', () => {
  const initial = currentHealthScore(conditions);
  assert(initial > 90 && initial < 100);
  for (const change of [{ pollution: 40 }, { temperature: 35 }, { temperature: 9 }, { breathing: 20 }, { breathing: 12 }]) {
    const score = currentHealthScore({ ...conditions, ...change });
    assert(score < initial && score > 0 && score <= 100);
  }
  assert.equal(currentHealthScore({ ...conditions, breathing: NaN }), null);
});

test('score recovers with cleaner conditions, ignores cumulative time cost and respects breathing updates', () => {
  const route = { breathing_reference:[{seconds:0,lower:14,upper:18,scale:2}],
    duration_s: 600,
    profile: [0, 100, 200, 600].map((seconds, i) => ({
      seconds, pollution: i === 1 ? 40 : 10, temperature: 22, health_cost: seconds * 10,
    })),
    breathing_profile: [{ seconds: 0, breathing: 16 }, { seconds: 300, breathing: 20 }, { seconds: 600, breathing: 16 }],
  };
  assert(routeHealthScore(route, 100) < routeHealthScore(route, 200));
  assert.equal(routeHealthScore(route, 0), routeHealthScore(route, 200));
  assert.equal(routeHealthScore(route, 200), routeHealthScore(route, 299));
  assert(routeHealthScore(route, 300) < routeHealthScore(route, 299));
  assert.equal(routeHealthScore(route, 600), routeHealthScore(route, 0));
  assert.equal(routeHealthScore({ ...route, breathing_profile: [] }, 10), null);
});

test('proposed equation and point shares match known examples',()=>{
 for(const [pollution,temperature,breathing,expected] of [[6, 22, 16, 99.4117183054868], [15, 22, 16, 96.37954646528334], [25, 30, 20, 79.85837488417967], [40, 34, 22, 47.13487493134232]]){
  const d=healthDetails({...conditions,pollution,temperature,breathing});
  assert.ok(Math.abs(d.score-expected)<.03);
  assert.ok(Math.abs(Object.values(d.contributions).reduce((a,b)=>a+b,0)-(100-d.score))<1e-10);
 }
 assert.equal(currentHealthScore({...conditions,reference:null}),null);
 assert.equal(currentHealthScore({...conditions,reference:{lower:14,upper:18,scale:0}}),null);
});
test('personal reference follows model time instead of resetting on replay',()=>{
 const route={duration_s:2000,breathing_reference:[{seconds:0,lower:14,upper:18,scale:2},{seconds:1800,lower:16,upper:20,scale:2}]};
 assert.equal(referenceAt(route,600).lower,14);
 assert.equal(referenceAt(route,1799).lower,14);
 assert.equal(referenceAt(route,1800).lower,16);
});

test('breathing sensitivity increases outside-band burden without penalising in-band variation',()=>{
 const low=healthDetails({...conditions,breathing:14});
 const high=healthDetails({...conditions,breathing:18});
 assert.equal(low.score,high.score);
 const d=healthDetails({...conditions,breathing:19});
 assert.equal(d.burdens.breathing,0.28125);
 assert.ok(d.score<high.score);
 assert.ok(currentHealthScore({...conditions,breathing:20})<d.score);
 assert.equal(healthDetails({...conditions,breathing:13}).score,d.score);
});
