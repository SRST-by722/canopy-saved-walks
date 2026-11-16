const assert=require('node:assert/strict'),fs=require('node:fs');
const puppeteer=require('../../../imperial-corridor-integration-20261111/node_modules/puppeteer-core');
(async()=>{
 const browser=await puppeteer.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true,args:['--no-sandbox']});
 const report={cases:[],errors:[]};
 try{
  const page=await browser.newPage();await page.setViewport({width:1500,height:1050});
  page.on('pageerror',e=>report.errors.push(e.message));
  await page.goto('http://127.0.0.1:8811/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1',{timeout:120000});
  await page.waitForFunction(()=>window.canopyPedestrian,{timeout:120000});
  for(const [day,time] of [['20260621','12:00'],['20261221','12:00'],['20261221','20:00']]){
   await page.select('#ic-solar-day',day);
   await page.$eval('#ic-departure',(el,value)=>{el.value=value;el.dispatchEvent(new Event('change'));},time);
   await page.evaluate(()=>window.canopyPedestrian.calculate());
   const result=await page.evaluate(async()=>{
    const app=window.canopyPedestrian,r=app.result?.routes[1];
    if(!r)throw Error(document.querySelector('#ic-status').textContent);
    const {healthDetails,referenceAt}=await import('./pedestrian/corridor-health-score.mjs');
    const {sample}=await import('./pedestrian/imperial-route-plots.mjs');
    let maxError=0;
    for(const row of r.profile){
     app.seek(row.seconds);const pos=app.person.group.position,env=app.environment.sample(pos.x,-pos.z,app.time);
     maxError=Math.max(maxError,Math.abs(env.sunlight-row.sunlight),Math.abs(env.thermal_proxy-row.thermal_proxy));
     const details=healthDetails({...env,breathing:sample(r.breathing_profile,row.seconds,'breathing',true),reference:referenceAt(r,row.seconds)});
     if(document.querySelector('#ic-health-number').textContent!==details.score.toFixed(1))throw Error('Score differs from live conditions');
    }
    app.seek(0);
    return {day:app.result.solar_day,start:app.start,duration:r.duration_s,maxError,sunlight:r.profile[0].sunlight,thermal:r.profile[0].thermal_proxy,air:r.profile[0].temperature,score:document.querySelector('#ic-health-number').textContent,reading:document.querySelector('#ic-health-sunlight').textContent,cvae:app.result.cvae_enabled,following:app.following};
   });
   assert.equal(result.day,day);assert.ok(result.maxError<1e-6);assert.equal(result.cvae,true);assert.equal(result.following,true);
   if(time==='20:00')assert.equal(result.sunlight,0);
   report.cases.push(result);
  }
  assert.notEqual(report.cases[0].sunlight,report.cases[1].sunlight);
  // Changing the existing main solar selector also invalidates the route and synchronises the walking panel.
  await page.select('#solar-date','20260621');
  assert.equal(await page.evaluate(()=>window.canopyPedestrian.result),null);
  assert.equal(await page.$eval('#ic-solar-day',el=>el.value),'20260621');
  await page.$eval('#ic-departure',el=>{el.value='12:00';el.dispatchEvent(new Event('change'));});
  await page.evaluate(()=>window.canopyPedestrian.calculate());
  await page.screenshot({path:'pedestrian/cache/solar-health-preview.png'});
  assert.deepEqual(report.errors,[]);
  fs.writeFileSync('pedestrian/cache/solar-browser-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
