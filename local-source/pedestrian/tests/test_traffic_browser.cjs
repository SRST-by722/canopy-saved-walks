const assert=require('node:assert/strict'),fs=require('node:fs');
const p=require('../../../imperial-corridor-integration-20261111/node_modules/puppeteer-core');
(async()=>{const browser=await p.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true,args:['--no-sandbox']});
try{
 const page=await browser.newPage();await page.setViewport({width:1500,height:1050});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:8811/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1',{timeout:120000});
 await page.waitForFunction(()=>window.canopyPedestrian&&window.corridorContext,{timeout:120000});
 await page.evaluate(()=>{const app=window.canopyPedestrian,c=app.meta.crossings.find(c=>c.id==='canopy-walk-4264');app.setEndpoints(...c.edge);const el=document.querySelector('#ic-departure');el.value='08:59:50';el.dispatchEvent(new Event('change'));});
 await page.evaluate(()=>window.canopyPedestrian.calculate());
 const report=await page.evaluate(async()=>{
  const app=window.canopyPedestrian,r=app.result?.routes[1];if(!r)throw Error(document.querySelector('#ic-status').textContent);
  const crossing=r.timeline.find(e=>e.kind==='Crossing'),wait=r.timeline.find(e=>e.kind==='Waiting');
  const {trafficGapClear}=await import('./pedestrian/traffic-gaps.mjs');
  app.seek(30);const a=app.person.group.position.clone(),state=document.querySelector('#ic-health-state').textContent;
  const head=app.signals.heads.find(h=>h.userData.crossingId===crossing.signal_id),red=head.userData.state==='red',blocked=head.userData.trafficBlocked;
  app.seek(wait.end-.01);const stationary=a.distanceTo(app.person.group.position)<1e-8;
  app.seek(crossing.start);const clear=trafficGapClear(app.result.traffic_gaps[crossing.signal_id],app.time),green=head.userData.state==='green';
  app.seek(crossing.start+1);const moved=a.distanceTo(app.person.group.position)>1;
  window.corridorContext.tick(0);const trafficFrame=window.corridorContext.frame,expectedFrame=Math.floor(app.time%600);
  app.seek(30);
  return {wait:r.wait_s,extra:r.traffic_wait_s,state,red,blocked,stationary,clear,green,moved,trafficFrame,expectedFrame,following:app.following,waitPlot:[...document.querySelectorAll('.metric b')].some(el=>el.textContent==='Crossing waiting · lights + traffic')};
 });
 assert.equal(report.wait,88);assert.equal(report.extra,58);for(const key of ['red','blocked','stationary','clear','green','moved','following','waitPlot'])assert.equal(report[key],true,key);
 assert.ok(report.state.includes('Waiting for cars'));assert.equal(report.trafficFrame,report.expectedFrame);assert.deepEqual(errors,[]);
 await page.screenshot({path:'pedestrian/cache/traffic-gap-wait-preview.png'});
 fs.writeFileSync('pedestrian/cache/traffic-gap-browser-report.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
