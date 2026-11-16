const fs=require('node:fs');
const p=require('../../imperial-corridor-integration-20261111/node_modules/puppeteer-core');
(async()=>{
 const browser=await p.launch({executablePath:'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();await page.setViewport({width:1600,height:1050});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text().slice(0,180));});
  await page.goto('http://127.0.0.1:8811/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1&pose=campus&step=1',{timeout:120000});
  try{await page.waitForFunction(()=>window.canopyPedestrian&&window.corridorContext,{timeout:90000});}catch(e){console.log('WAIT',e.message);}
  console.log(await page.evaluate(()=>({walker:!!window.canopyPedestrian,traffic:!!window.corridorContext,stage:document.querySelector('#stage')?.textContent,loading:document.querySelector('#pct')?.textContent,info:document.querySelector('#info')?.textContent})));
  console.log('errors',errors);await page.screenshot({path:'pedestrian/cache/canopy-integration.png'});
  if(await page.evaluate(()=>!!window.canopyPedestrian)){await page.click('#ic-run');await page.waitForFunction(()=>window.canopyPedestrian.result,{timeout:120000});console.log(await page.evaluate(()=>({duration:window.canopyPedestrian.result.routes[1].duration_s,score:document.querySelector('#ic-health-number').textContent,status:document.querySelector('#ic-status').textContent})));await page.screenshot({path:'pedestrian/cache/canopy-route.png'});}
  fs.writeFileSync('pedestrian/cache/browser-errors.json',JSON.stringify(errors,null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
