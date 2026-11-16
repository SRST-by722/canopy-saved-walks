const assert=require('node:assert/strict');
const p=require('../../../imperial-corridor-integration-20261111/node_modules/puppeteer-core');
(async()=>{
 const browser=await p.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8811/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1&quality=lite',{timeout:120000});
  await page.waitForFunction(()=>window.canopyPedestrian,{timeout:120000});
  await page.click('[data-field="solar"]');
  await page.waitForFunction(()=>document.querySelector('#stage').textContent.includes('shared scenario'));
  await page.evaluate(()=>window.canopyPedestrian.seekWorld(11400));
  assert.ok((await page.$eval('#time-label',el=>el.textContent)).includes('12:00:00'));
  await page.select('#solar-mode','shadow');
  await page.waitForFunction(()=>document.querySelector('#solar-mode').value==='shadow');
  await page.evaluate(()=>window.canopyPedestrian.seekWorld(12000));
  await page.select('#solar-mode','ghi');
  await page.select('#solar-date','20261221');
  await page.evaluate(()=>window.canopyPedestrian.seekWorld(40200));
  const frame=await page.evaluate(()=>{
   const a=window.canopyPedestrian;return {day:a.environment.solarDay,max:Math.max(...a.environment.solarFrame(a.time).subarray(0,50000)),time:document.querySelector('#time-label').textContent};
  });
  assert.equal(frame.day,'20261221');assert.equal(frame.max,0);assert.ok(frame.time.includes('20:00:00'));
  assert.deepEqual(errors,[]);console.log(JSON.stringify({passed:true,frame,errors}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
