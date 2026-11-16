const assert=require('node:assert/strict'),fs=require('node:fs');
const p=require('../../imperial-corridor-integration-20261111/node_modules/puppeteer-core');
(async()=>{
 const browser=await p.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();await page.setViewport({width:1600,height:1050});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8811/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1&step=1',{timeout:120000});
  await page.waitForFunction(()=>window.canopyPedestrian&&window.corridorContext,{timeout:120000});
  assert.equal(await page.$eval('#ic-example',()=>true).catch(()=>false),false);
  assert.equal(await page.$eval('.health-card',e=>e.nextElementSibling.id),'imperial-route-plots');
  assert.equal(await page.$eval('#canopy-walking-mode',e=>e.textContent),'Healthy route recommendation');
  assert.equal(await page.$eval('#ic-departure',e=>e.value),'0');
  assert.equal(await page.$eval('#ic-limit',e=>e.selectedOptions[0].textContent),'13 hours (maximum)');
  // Retain the existing 240 s departure fixture for the physiological checks below.
  await page.$eval('#ic-departure',e=>{e.value='240';e.dispatchEvent(new Event('change'));});
  assert.equal(await page.$eval('#ic-limit',e=>e.selectedOptions[0].textContent),'12 hours 56 minutes (maximum)');
  await page.click('#ic-run');await page.waitForFunction(()=>window.canopyPedestrian.result,{timeout:120000});
  const report=await page.evaluate(async()=>{
   const app=window.canopyPedestrian,r=app.result.routes[1],traffic=window.corridorContext;
   const {routeHealthScore}=await import('./pedestrian/corridor-health-score.mjs');
   const scores=[];
   for(let t=0;t<=r.duration_s;t+=2){app.seek(t);const shown=document.getElementById('ic-health-number').textContent,expected=routeHealthScore(r,t);if(shown!==(expected===null?'—':expected.toFixed(1)))throw Error('Displayed score differs from current conditions');scores.push(expected);}
   const before=r.breathing_profile[0].breathing;app.seek(59);const br59=document.getElementById('ic-value-breathing').textContent;app.seek(61);const br61=document.getElementById('ic-value-breathing').textContent;
   app.seek(r.duration_s);const arrived=app.person.group.userData.status;
   app.seek(0);const initial=document.getElementById('ic-health-number').textContent;
   const waits=r.timeline.filter(e=>e.kind==='Waiting');let stationary=true,green=true;
   for(const w of waits){app.seek(w.start+.01);const a=app.person.group.position.clone();app.seek(w.end-.01);stationary&&=a.distanceTo(app.person.group.position)<1e-6;app.seek(w.end+.001);const head=app.signals.heads.find(h=>h.userData.crossingId===w.signal_id);green&&=head?.userData.state==='green';}
   traffic.show(0);const first=traffic.frame;traffic.show(10);const next=traffic.frame;const count=traffic.meta.frames;
   return {duration:r.duration_s,waiting:r.wait_s,missingTemperature:r.missing_temperature_samples,initial,scores,br59,br61,arrived,stationary,green,traffic:{first,next,count,visible:traffic.cars.visible,staticSignals:traffic.signals.userData.timed},
    paths:app.meta.summary,source:app.meta.provenance.source,
    routeChildren:app.group.getObjectByName('selected-route').children.map(c=>({name:c.name,color:c.material.color.getHexString()})),hiddenSamples:!app.group.getObjectByName('sample-points').visible};
  });
  assert.equal(report.arrived,'Arrived');assert(report.stationary);assert(report.green);assert.notEqual(report.br59,report.br61);
  assert(report.scores.some((v,i,a)=>i&&v!==null&&a[i-1]!==null&&v>a[i-1]));assert(report.scores.some((v,i,a)=>i&&v!==null&&a[i-1]!==null&&v<a[i-1]));
  assert.equal(report.traffic.next,10);assert.equal(report.traffic.count,600);assert(report.traffic.visible);assert.equal(report.traffic.staticSignals,false);
  assert.equal(report.paths.environmental_exclusions,0);assert(report.paths.undirected_links>30000);assert.equal(report.routeChildren[0].color,'ff59c7');assert.equal(report.routeChildren.length,2);assert(report.hiddenSamples);
  assert.deepEqual(await page.$$eval('.route-trace',es=>es.map(e=>e.getAttribute('stroke'))),Array(5).fill('#ff2020'));
  await page.click('#ic-points');assert(await page.evaluate(()=>window.canopyPedestrian.group.getObjectByName('sample-points').visible));await page.click('#ic-points');
  await page.select('#ic-speed','10');await page.click('#ic-play');await page.waitForFunction(()=>window.canopyPedestrian.elapsed>2);await page.click('#ic-play');
  await page.evaluate(()=>{window.corridorContext.setPlaying(true);window.canopyPedestrian.setActive(false);});
  await page.waitForFunction(()=>window.corridorContext.frame>10);assert.equal(await page.evaluate(()=>window.canopyPedestrian.group.visible),false);
  await page.evaluate(()=>{window.canopyPedestrian.setActive(true);window.corridorContext.setPlaying(false);window.canopyPedestrian.seek(0);});
  await page.click('#ic-goal');
  const location=await page.evaluate(()=>{window.canopyPedestrian.focus();const viewer=window.viewer,p=window.canopyPedestrian.meta.nodes[window.canopyPedestrian.meta.example[1]];const v=new viewer.THREE.Vector3(p[0],p[2],-p[1]).project(viewer.camera);const r=viewer.renderer.domElement.getBoundingClientRect();return{x:r.left+(v.x+1)*r.width/2,y:r.top+(1-v.y)*r.height/2};});
  await page.mouse.click(location.x,location.y);
  assert.equal(await page.$eval('#ic-status',e=>e.textContent),'Endpoint selected. Calculate the route.');
  // Duration change resets route/score and updates the maximum without touching traffic range.
  await page.$eval('#ic-departure',e=>{e.value='0';e.dispatchEvent(new Event('change'));});
  assert.equal(await page.$eval('#ic-limit option:last-child',e=>e.textContent),'13 hours (maximum)');
  assert.equal(await page.$eval('#ic-health-number',e=>e.textContent),'—');assert.equal(await page.evaluate(()=>window.canopyPedestrian.result),null);
  await page.$eval('#ic-departure',e=>{e.value='240';e.dispatchEvent(new Event('change'));});await page.click('#ic-run');await page.waitForFunction(()=>window.canopyPedestrian.result);
  // Full native buildings finish loading; the overlay must coexist with them.
  console.log('Core walking/traffic assertions passed; waiting for native geometry');
  await page.waitForFunction(()=>window.cityDetailTiles?.progress.complete,{timeout:180000});
  await page.evaluate(()=>{window.canopyPedestrian.focus();window.canopyPedestrian.seek(100);document.getElementById('canopy-pedestrian-panel').scrollTop=0;document.getElementById('layers').classList.remove('open');});
  await page.screenshot({path:'pedestrian/cache/canopy-complete.png'});
  report.geometry=await page.evaluate(()=>window.cityDetailTiles.progress);
  assert.deepEqual(errors,[]);report.errors=errors;report.passed=true;fs.writeFileSync('pedestrian/cache/browser-validation.json',JSON.stringify(report,null,2));console.log('PASS walking, score recovery, CVAE, signal waits, independent traffic, controls and full native geometry');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
