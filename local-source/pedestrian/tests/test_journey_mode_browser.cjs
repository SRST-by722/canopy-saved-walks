const assert=require('node:assert/strict'),fs=require('node:fs');
const p=require('../../../imperial-corridor-integration-20261111/node_modules/puppeteer-core');
(async()=>{const browser=await p.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true,args:['--no-sandbox']});
try{
 const page=await browser.newPage();await page.setViewport({width:1500,height:1050});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8811/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1',{timeout:120000});
 await page.waitForFunction(()=>window.canopyPedestrian,{timeout:120000});
 assert.equal(await page.$eval('#ic-travel-mode',e=>e.value),'walk');
 await page.evaluate(()=>window.canopyPedestrian.calculate());
 const walk=await page.evaluate(()=>{const a=window.canopyPedestrian,r=a.result.routes[1];return {mode:a.result.travel_mode,speed:r.speed_m_s,duration:r.duration_s,wait:r.wait_s,distance:r.profile.at(-1).distance};});
 await page.select('#ic-travel-mode','run');
 assert.equal(await page.evaluate(()=>window.canopyPedestrian.result),null);
 await page.evaluate(()=>window.canopyPedestrian.calculate());
 const run=await page.evaluate(()=>{
  const a=window.canopyPedestrian,r=a.result.routes[1];a.seek(10);
  const modeLocked=document.querySelector('#ic-travel-mode').disabled,status=a.person.group.userData.status;
  a.setSpeed(10);const independent=a.result.travel_speed.speed_m_s===2.5;
  const notes=document.querySelector('#ic-mode-note').textContent;
  return {mode:a.result.travel_mode,speed:r.speed_m_s,duration:r.duration_s,wait:r.wait_s,distance:r.profile.at(-1).distance,modeLocked,status,independent,notes,activityMode:a.result.breathing_model.activity_mode,
   correctSpeeds:r.timeline.filter(e=>e.kind!=='Waiting').every(e=>Math.abs(e.distance.at(-1)/(e.end-e.start)-2.5)<1e-8)};
 });
 assert.equal(walk.mode,'walk');assert.equal(walk.speed,4/3);assert.equal(run.mode,'run');assert.equal(run.speed,2.5);
 assert.ok(run.duration<walk.duration);assert.equal(run.correctSpeeds,true);assert.equal(run.modeLocked,true);assert.equal(run.status,'Running');assert.equal(run.independent,true);assert.ok(run.notes.includes('not calibrated running physiology'));
 await page.screenshot({path:'pedestrian/cache/running-mode-preview.png'});
 await page.evaluate(()=>window.canopyPedestrian.seek(0));assert.equal(await page.$eval('#ic-travel-mode',e=>e.disabled),true);
 await page.click('#ic-new-journey');assert.equal(await page.$eval('#ic-travel-mode',e=>e.disabled),false);assert.equal(await page.evaluate(()=>window.canopyPedestrian.result),null);
 await page.select('#ic-travel-mode','walk');await page.evaluate(()=>window.canopyPedestrian.calculate());
 assert.equal(await page.evaluate(()=>window.canopyPedestrian.result.routes[1].duration_s),walk.duration);
 const bad=await page.evaluate(async()=>{const a=window.canopyPedestrian,r=await fetch('/api/pedestrian/plan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...a.endpoints,travel_mode:'cycling',departure_s:0,max_minutes:20})});return {status:r.status,body:await r.json()};});
 assert.equal(bad.status,400);assert.ok(bad.body.error.includes('walking or running'));assert.deepEqual(errors,[]);
 const report={walk,run,walkRestored:true,modeLockedAfterStart:true,invalidModeRejected:true,errors};fs.writeFileSync('pedestrian/cache/journey-mode-browser-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
