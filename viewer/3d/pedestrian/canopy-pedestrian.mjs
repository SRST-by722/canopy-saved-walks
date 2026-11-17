import {clockTime,modelTime} from './journey-clock.mjs';
import * as THREE from 'three';
import {currentTerrain} from '../corridor-terrain.js';
import {flag,drawRoute} from './corridor-ui.mjs';
import {createCrossingPerson} from './crossing-person.mjs';
import {createWalkSignals} from './pedestrian-walk-signals.mjs';
import {createCorridorPlots} from './imperial-route-plots.mjs';
import {healthDetails,referenceAt} from './corridor-health-score.mjs';
import {sample} from './imperial-route-plots.mjs';
import {loadEnvironment} from './shared-environment.mjs';
import {connectedEndpoints,nearestWalkingNode,destinationChoice} from './walking-endpoints.mjs';
import {followWalker} from './follow-walker.mjs';
import {loadSavedCatalog,loadSavedMeta,loadSavedJourney,findJourney,journeyLabel} from './saved-journeys.mjs';

export async function installCanopyPedestrian(viewer,{enter,invalidate,onTime=()=>{},isSharedView=()=>true}) {
  const {scene,camera,controls,renderer}=viewer;
  const [catalog,meta]=await Promise.all([loadSavedCatalog(),loadSavedMeta()]);
  const config=meta.pollution_scenario;
  let selectedJourney=catalog.journeys.find(j=>j.id===new URLSearchParams(location.search).get('journey'))||findJourney(catalog,'p01-p03');
  const locations=new Map(catalog.locations.map(p=>[p.id,p]));
  const environment=await loadEnvironment(meta.environment,config);
  const group=new THREE.Group();group.name='canopy-pedestrian-overlay';group.visible=false;scene.add(group);
  const panel=document.createElement('aside');panel.id='canopy-pedestrian-panel';panel.hidden=true;
  panel.innerHTML=`<header><b>CANOPY · Healthy route recommendation</b><button id="ic-close" aria-label="Close pedestrian panel">×</button></header><p class="hint">Shared journey clock · pollution, temperature and traffic repeat every 10 minutes.</p>
    <p><label for="ic-travel-mode">Journey mode</label> <select id="ic-travel-mode">${Object.entries(meta.travel_modes).map(([key,m])=>`<option value="${key}">${m.label} · ${m.speed_km_h} km/h</option>`).join('')}</select> <button id="ic-new-journey">New journey</button></p><p id="ic-mode-note" class="hint"></p>
    <p><label for="ic-journey">Saved journey</label><select id="ic-journey" style="width:100%"></select></p><p id="ic-journey-summary"></p>
    <section class="health-card"><div id="ic-health-ring" role="img"><span id="ic-health-number">—</span></div><div><b>Health score / 100</b><p id="ic-health-state">Choose a route</p><small>Pollution · breathing · thermal comfort<br>Higher is better · experimental, not clinical</small></div></section><section id="ic-health-contributions" aria-live="polite"><b>Points deducted from 100</b><div id="ic-health-pollution">Pollution —</div><div id="ic-health-temperature">Thermal comfort —</div><small id="ic-health-sunlight">Sunlight —</small><div id="ic-health-breathing">Breathing —</div><small id="ic-health-reference">Personal reference available after route calculation.</small><small>Shares of the combined score reduction, not separate health risks.</small></section>
    <section id="imperial-route-plots"></section>
    <p id="ic-endpoints"></p><details><summary>Explore the 15 journeys</summary><div id="ic-route-atlas"></div></details>
    <p><label for="ic-solar-day">Sunlight scenario</label><br><select id="ic-solar-day"><option value="20260621">21 June · clear sky</option><option value="20261221">21 December · clear sky</option></select></p><p>Saved departure: 08:50 · maximum journey duration: 13 hours. 15 journeys, each calculated for walking/running and both sunlight days.</p><input id="ic-departure" type="hidden" value="08:50"><select id="ic-limit" hidden><option value="780">13 hours (maximum)</option></select>
    <p><button id="ic-run">Load saved journey</button> <button id="ic-focus">Show whole route</button></p>
    <p><button id="ic-play" disabled>Play journey</button> <label>Playback speed <select id="ic-speed">${[.25,.5,1,2,5,10,30,60].map(v=>`<option value="${v}"${v===1?' selected':''}>${v}×${v===1?' (real time)':''}</option>`).join('')}</select></label></p>
    <p id="ic-speed-note" class="hint"></p>
    <input id="ic-time" type="range" min="0" max="1" step="0.1" value="0" disabled aria-label="Journey elapsed time"><div id="ic-clock">0 s</div>
    <p><label><input id="ic-follow" type="checkbox" checked disabled> Follow walker</label> <button id="ic-view">Top-down / 3D</button></p>
    <p class="hint">Moving the map manually turns following off. Turn it back on to centre the walker.</p>
    <label><input id="ic-points" type="checkbox"> Show map sample points</label>
    <p><label><input id="ic-field" type="checkbox" checked> Walking pollution colours</label></p>
    <p id="ic-status">Choose a saved journey, mode and sunlight day.</p><p id="ic-field-legend" class="hint"></p>
    <details><summary>Model assumptions</summary><p class="hint">Canopy roads, terrain and recorded cars are preserved. Walking paths use Canopy's map geometry; access is not surveyed. Route search evaluates a bounded set of alternatives; it does not guarantee the globally best route. Our pedestrian lights are modelled and do not control vehicle motion. Crossing admission also checks the retained recorded cars: the entire crossing must be clear for the selected travel speed plus 2 seconds, with a 1.4 m footprint margin and a 1 second time buffer. Waits enter wave cost, exposure and CVAE history. These are conservative XY checks against a saved vehicle subset, not real-world safety assurance.</p><p class="hint">Native Canopy fields sampled at your position and current scenario time. Tracer-derived PM2.5: illustrative 6–40 µg/m³ conversion, not measured or calibrated. Temperature: time-varying Canopy field at 8 m above ground. The 10-minute environmental sequences and traffic replay repeat for the full route-model duration (up to 13 hours at start 0). Pollution and temperature gently blend back to their initial fields during the final minute of each cycle; this repeats a scenario, not a forecast. Journey time and breathing history continue across each repeat. Cars are time-aligned with the fields, but do not generate their emissions. Missing pollution and temperature cells are filled from the nearest valid simulation cell; these are illustrative estimates, not original simulated values. Health score uses a personal historical q10–q90 breathing band, not the departure prediction. Reference matching follows recorded activity/time with labelled fallbacks, not verified walking. PM reference 15 µg/m³ is a scale, not an instantaneous safety threshold; 18–26°C is a provisional comfort band. Thermal comfort uses air temperature + ${meta.environment.solar_warming_c_per_800}°C × clamp(sunlight / 800 W/m², 0, 1.5). This is an illustrative solar-warming proxy, not UTCI, WBGT or a validated feels-like temperature. Sunlight is interpolated on the selected June/December clear-sky day and is zero outside its daylight range; it does not repeat every 10 minutes. CVAE continues to receive air temperature. Weights and mapping are design choices. Walking is 4.8 km/h; running is a fixed 9 km/h scenario preset. Mode is selected before departure and affects travel time, field sampling and crossing gaps. The CVAE weights and recorded activity/humidity inputs are retained, with five-minute prediction updates; running-specific physiology and reference bands are not calibrated.</p></details>`;
  document.body.append(panel);
  const style=document.createElement('style');style.textContent=`
  #canopy-pedestrian-panel{position:fixed;left:16px;top:130px;bottom:90px;width:345px;box-sizing:border-box;overflow:auto;z-index:45;background:#102832f5;border:1px solid #6b948d;border-radius:12px;padding:12px;color:#eaf4f3;font:13px/1.5 system-ui;box-shadow:0 6px 28px #0007}
  #canopy-pedestrian-panel[hidden]{display:none}#canopy-pedestrian-panel header{display:flex;align-items:center;justify-content:space-between;font-size:17px;margin-bottom:12px}#canopy-pedestrian-panel button,#canopy-pedestrian-panel select,#canopy-pedestrian-panel input[type=number]{background:#25444c;color:white;border:1px solid #6b9398;border-radius:6px;padding:5px;font:inherit;max-width:100%}#canopy-pedestrian-panel button:disabled{opacity:.5}#canopy-pedestrian-panel input[type=number]{width:85px}#ic-time{width:100%}
  #canopy-pedestrian-panel .health-card{position:sticky;top:-12px;z-index:5;display:flex;align-items:center;gap:12px;padding:12px 6px;background:#142b36;border:1px solid #526778;border-radius:12px}#ic-health-contributions{padding:10px 8px;border:1px solid #526778;border-radius:8px;margin:8px 0;background:#142b36;font-size:12px}#ic-health-contributions div{margin:7px 0;display:flex;justify-content:space-between;gap:8px}#ic-health-contributions small{display:block;margin-top:7px;color:#bbd3d8}#ic-health-ring{--fill:0%;position:relative;flex:0 0 82px;height:82px;border-radius:50%;background:conic-gradient(#57dcc8 var(--fill),#344958 0);display:grid;place-items:center}#ic-health-ring:before{content:"";position:absolute;inset:8px;border-radius:50%;background:#142b36}#ic-health-ring span{position:relative;font-size:22px;font-weight:700}#canopy-pedestrian-panel .health-card p{margin:4px 0}#canopy-pedestrian-panel small{font-size:10px}
  #canopy-pedestrian-panel .metric{background:#203b45;padding:9px;margin:10px 0;border-radius:8px}#canopy-pedestrian-panel .metric svg{width:100%;display:block}#canopy-pedestrian-panel .metric text{fill:#c8dce6;font-size:10px}#canopy-pedestrian-panel .hint{font-size:11px;color:#b4c9d4}#canopy-pedestrian-panel details{margin-top:10px}#ic-status{color:#c9e8db}@media(max-width:650px){#canopy-pedestrian-panel{width:300px;top:145px}}`;
  document.head.append(style);
  const $=id=>panel.querySelector('#ic-'+id),plots=createCorridorPlots(panel.querySelector('#imperial-route-plots'));
  const mode=document.createElement('button');mode.id='canopy-walking-mode';mode.className='tab';mode.textContent='Healthy route recommendation';mode.title='Pedestrian route and breathing model';document.querySelector('#tabs').append(mode);
  let active=false,playing=false,elapsed=0,result=null,pick=null,revision=0,top=false,busy=false,disposed=false,followReady=false,journeyStarted=false;
  let origin=locations.get(selectedJourney.origin).node,goal=locations.get(selectedJourney.destination).node;
  const launch=new URLSearchParams(location.search);
  const height=(x,y,z)=>currentTerrain()?.enabled?(z ?? currentTerrain().sample(x,-y)):0;
  const starts=flag(0x33dd77),ends=flag(0xff4477);group.add(starts,ends);
  const person=createCrossingPerson('Person');person.group.visible=false;group.add(person.group);
  const routeGroup=new THREE.Group();routeGroup.name='selected-route';group.add(routeGroup);
  const entries=Object.entries(meta.nodes);
  const points=new THREE.Points(new THREE.BufferGeometry().setFromPoints(entries.map(([,p])=>new THREE.Vector3(p[0],height(p[0],p[1],p[2])+.5,-p[1]))),new THREE.PointsMaterial({color:0x94e7df,size:3,depthTest:false}));points.name='sample-points';points.visible=false;group.add(points);
  const vertices=[],vertexComponents=[];
  for(const [j,road] of meta.roads.entries())for(let i=1;i<road.length;i++)for(const p of [road[i-1],road[i]]){vertices.push(p[0],height(p[0],p[1],p[2])+.3,-p[1]);vertexComponents.push(meta.road_components[j]);}
  const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));geometry.setAttribute('color',new THREE.Float32BufferAttribute(new Float32Array(vertices.length),3));
  const roads=new THREE.LineSegments(geometry,new THREE.LineBasicMaterial({vertexColors:true,depthTest:true,depthWrite:false,transparent:true,opacity:.85}));roads.name='live-pollution-streets';group.add(roads);
  const signals=createWalkSignals({pedestrian_programs:meta.crossings,signals:meta.crossings.flatMap(c=>[c.points[0],c.points.at(-1)].map((p,i)=>({id:c.id+'-'+i,crossing_id:c.id,head:p})))});group.add(signals.group);
  const crossingById=new Map(meta.crossings.map(c=>[c.id,c]));
  for(const h of signals.heads){const c=crossingById.get(h.userData.crossingId),p=h.name.endsWith('-1')?c.points.at(-1):c.points[0];h.position.y=height(p[0],p[1],p[2])+4;h.scale.set(2,4,1);}
  const pm=(x,y,t)=>environment.sample(x,y,t).pollution;
  let lastTick=null;
  function paint(t){const tick=Math.floor(t*4);if(tick===lastTick)return;lastTick=tick;const pos=geometry.attributes.position,col=geometry.attributes.color,c=new THREE.Color();for(let i=0;i<pos.count;i++){const v=pm(pos.getX(i),-pos.getZ(i),t);if(pick)c.setHex(pick==='origin'||vertexComponents[i]===meta.node_components[origin]?0x50ffe0:0x50616a);else if(v===null)c.setHex(0x50616a);else c.setHSL((1-Math.max(0,Math.min(1,(v-6)/34)))*.65,.85,.5);col.setXYZ(i,c.r,c.g,c.b);}col.needsUpdate=true;roads.visible=Boolean(pick)||$('field').checked;roads.material.depthTest=!pick;$('field-legend').textContent=pick==='goal'?'Mint paths: connected to START · grey paths: disconnected':pick==='origin'?'Mint paths: mapped walking paths. Pick START first.':`Tracer-derived PM2.5 scenario · grey = unavailable · journey ${t.toFixed(0)} s · replay ${Math.floor(t/600)+1}, field ${(t%600).toFixed(0)} s`;}
  function connected(){return origin!==goal&&connectedEndpoints(meta.node_components,origin,goal);}
  function flags(){for(const [object,id] of [[starts,origin],[ends,goal]]){const p=meta.nodes[id];object.position.set(p[0],height(p[0],p[1],p[2])+.6,-p[1]);}$('endpoints').textContent=`START: ${locations.get(selectedJourney.origin).source_road} → END: ${locations.get(selectedJourney.destination).source_road}`;$('endpoints').dataset.origin=origin;$('endpoints').dataset.goal=goal;$('run').disabled=busy||!connected();}
  function setPick(value){pick=value;if(value)setFollow(false);lastTick=null;paint(departureSeconds()+elapsed);invalidate();}
  function clearRoute(){for(const child of [...routeGroup.children]){child.geometry?.dispose();child.material?.dispose();routeGroup.remove(child);}}
  function reset(){signals.setTrafficGaps({});journeyStarted=false;$('travel-mode').disabled=busy;revision++;playing=false;elapsed=0;result=null;followReady=false;$('follow').disabled=true;clearRoute();plots.reset();person.group.visible=false;$('play').disabled=true;$('play').textContent='Play journey';$('time').disabled=true;$('time').value=0;$('clock').textContent='0 s';$('health-number').textContent='—';for(const key of ['pollution','temperature','breathing'])$('health-'+key).textContent=key[0].toUpperCase()+key.slice(1)+' —';$('health-sunlight').textContent='Sunlight —';$('health-reference').textContent='Personal reference available after route calculation.';$('health-state').textContent='Load the selected journey';$('health-ring').style.setProperty('--fill','0%');speedNote();invalidate();}
  function format(minutes){const total=Math.round(minutes*60),h=Math.floor(total/3600),m=Math.floor(total%3600/60),s=total%60;return [h?`${h} ${h===1?'hour':'hours'}`:'',m?`${m} ${m===1?'minute':'minutes'}`:'',s?`${s} seconds`:''].filter(Boolean).join(' ')||'0 minutes';}
  function durationOptions(){
    const select=$('limit'),maximum=Math.max(0,Math.max(0,(meta.journey_horizon_s-departureSeconds())/60));
    const useMaximum=!select.value||select.selectedOptions[0]?.textContent.endsWith('(maximum)');
    const chosen=useMaximum?maximum:Math.min(+select.value,maximum);
    const choices=[...new Set([1,2,5,10,15,30,60,120,180,240,360,720,maximum,chosen])].filter(n=>n>0&&n<=maximum).sort((a,b)=>a-b);
    select.replaceChildren(...choices.map(n=>new Option(format(n)+(n===maximum?' (maximum)':''),String(n))));select.value=String(chosen);
  }
  function departureSeconds(){const t=modelTime($('departure').value);return Number.isFinite(t)?Math.max(0,Math.min(meta.journey_horizon_s-60,t)):0;}
  function focus(){const a=meta.nodes[origin],b=meta.nodes[goal],x=(a[0]+b[0])/2,y=(a[1]+b[1])/2,d=Math.max(120,Math.hypot(a[0]-b[0],a[1]-b[1])*1.2),h=height(x,y);controls.target.set(x,h,-y);camera.position.set(x+(top?0:d*.7),h+d*(top?1.5:1),-y+(top?.1:d*.8));controls.update();invalidate();}
  function updateFollow(frame=false){if(!active||!result||!$('follow').checked)return;followWalker(camera,controls,person.group.position,{frame:frame||!followReady,top});followReady=true;person.updateCamera(camera);invalidate();}
  function setFollow(value){$('follow').checked=value;followReady=false;if(value)updateFollow(true);}
  function manualCamera(){if(active&&$('follow').checked)setFollow(false);}
  controls.addEventListener('start',manualCamera);
  function journeyMode(){return result?.travel_speed??meta.travel_modes[$('travel-mode').value];}
  function speedNote(){const speed=+$('speed').value,m=journeyMode();$('speed-note').textContent=`${m.label}: ${m.speed_km_h} km/h. ${speed===1?'1 second of playback = 1 second of journey time.':`1 second of playback = ${speed} seconds of journey time.`}`;
    $('mode-note').textContent=(journeyStarted?'Mode fixed for this journey. Use New journey to choose again.':'Choose before calculating. Mode stays fixed after departure.')+($('travel-mode').value==='run'?' Running changes travel timing; breathing and health estimates use recorded activity, not calibrated running physiology.':'');}
  $('speed').onchange=()=>{speedNote();onTime(departureSeconds()+elapsed,environment);};speedNote();
  function seek(value){elapsed=Math.max(0,Math.min(result?.routes[1].duration_s??(meta.journey_horizon_s-departureSeconds()),value));const t=departureSeconds()+elapsed;if(result&&elapsed>0)journeyStarted=true;$('travel-mode').disabled=busy||journeyStarted;speedNote();paint(t);signals.update(t);onTime(t,environment);if(!result)return;
    const route=result.routes[1],event=route.timeline.find(e=>elapsed>=e.start&&elapsed<e.end)||route.timeline.at(-1);let p=event.points[0];
    if(event.points.length>1){const target=Math.min(1,(elapsed-event.start)/(event.end-event.start))*event.distance.at(-1);let j=1;while(j<event.distance.length-1&&event.distance[j]<target)j++;const f=(target-event.distance[j-1])/(event.distance[j]-event.distance[j-1]||1);p=event.points[j-1].map((v,k)=>v+f*(event.points[j][k]-v));}
    const status=elapsed>=route.duration_s?'Arrived':event.kind;person.setPose(status,elapsed,result.travel_mode==='run'?1.5:1);person.updateCamera(camera);person.group.position.set(p[0],height(p[0],p[1],p[2])+.15,-p[1]);person.group.visible=true;updateFollow();const conditions=environment.sample(p[0],p[1],t);plots.update(elapsed,conditions);
    const breathing=sample(route.breathing_profile,elapsed,'breathing',true),reference=referenceAt(route,elapsed);
    const details=healthDetails({...conditions,breathing,reference}),score=details?.score??null;
    const waitLabel=status==='Waiting'?(event.traffic_extra_wait_s>0?'Waiting for cars / crossing light':'Waiting for crossing light'):status;
    $('health-sunlight').textContent=`Air ${conditions.temperature?.toFixed(1)??'—'}°C · sunlight ${conditions.sunlight?.toFixed(0)??'—'} W/m² · ${clockTime(t)} · ${environment.solarDay==='20260621'?'21 June':'21 December'}`;
    for(const [key,label,value,unit] of [['pollution','Pollution',conditions.pollution,'µg/m³ · gaps estimated'],['temperature','Thermal comfort',conditions.thermal_proxy,'°C · solar proxy'],['breathing','Breathing',breathing,'breaths/min']]){
      const reading=Number.isFinite(value)?value.toFixed(1)+' '+unit:'unavailable';
      $('health-'+key).textContent=label+': '+reading+' · '+(details?'−'+details.contributions[key].toFixed(1)+' pts':'— pts');
    }
    const mode={activity_and_time:'activity + time matched',activity_only:'activity-only fallback',pooled_history_unsupported:'pooled-history fallback; activity match unsupported'};
    $('health-reference').textContent=reference?`Personal range ${reference.lower.toFixed(1)}–${reference.upper.toFixed(1)} breaths/min · ${mode[reference.mode]??reference.mode} · n=${reference.count}. Descriptive, not a clinical healthy range; recorded activity is not verified walking.`:'Personal breathing reference unavailable';
    $('health-number').textContent=score===null?'—':score.toFixed(1);$('health-state').textContent=score===null?'Score inputs unavailable':`${waitLabel} · current conditions`;$('health-ring').style.setProperty('--fill',(score??0)+'%');$('health-ring').setAttribute('aria-label',score===null?'Health score unavailable':`Health score ${score.toFixed(1)} out of 100`);$('time').value=elapsed;$('clock').textContent=`${(elapsed/60).toFixed(1)} / ${(route.duration_s/60).toFixed(1)} min · ${waitLabel} · clock ${clockTime(t)}`;invalidate();}
  async function calculate(){if(busy||!$('departure').reportValidity()||!$('limit').value)return;if(!connected()){$('status').textContent='Pick a destination on a mint path connected to START.';setPick('goal');return;}setPick(null);reset();const version=revision;busy=true;for(const id of ['run','journey','travel-mode','new-journey','solar-day'])$(id).disabled=true;$('status').textContent='Loading the saved journey…';
    try{const data=await loadSavedJourney(catalog,selectedJourney.id,$('travel-mode').value,environment.solarDay);if(disposed||version!==revision)return;result=data;signals.setTrafficGaps(data.traffic_gaps);const route=data.routes[1];drawRoute(route,routeGroup,height);plots.render(data);$('follow').disabled=false;$('follow').checked=true;followReady=false;$('play').disabled=false;$('time').disabled=false;$('time').max=route.duration_s;$('status').textContent=`${(route.duration_s/60).toFixed(1)} min ${data.travel_speed.label.toLowerCase()} + waits · ${route.wait_s.toFixed(1)} s crossing waits (${(route.traffic_wait_s??0).toFixed(1)} s extra from traffic gaps). Pink route on Canopy paths.`+(route.missing_temperature_samples?' Some temperature samples are unavailable; CVAE uses its training mean there.':'')+(data.wave_audit?.[1]?.search_limited?' Best evaluated route shown; wider route search was limited.':'');seek(0);
    }catch(error){$('status').textContent=error.message;}finally{busy=false;for(const id of ['run','journey','travel-mode','new-journey','solar-day'])$(id).disabled=false;flags();}}
  function setActive(value){active=value;group.visible=value;panel.hidden=!value;mode.setAttribute('aria-pressed',String(value));if(value){enter();flags();if(result&&$('follow').checked)updateFollow(true);else focus();}else{playing=false;$('play').textContent='Play journey';setPick(null);}invalidate();}
  mode.onclick=()=>setActive(!active);$('close').onclick=()=>setActive(false);$('run').onclick=calculate;$('focus').onclick=()=>{setFollow(false);focus();};$('follow').onchange=()=>setFollow($('follow').checked);$('view').onclick=()=>{top=!top;if(result&&$('follow').checked)updateFollow(true);else focus();};$('points').onchange=()=>{points.visible=$('points').checked;invalidate();};$('field').onchange=()=>{lastTick=null;paint(departureSeconds()+elapsed);invalidate();};
  $('travel-mode').onchange=()=>{if(journeyStarted)return;reset();seek(0);$('status').textContent='Journey mode changed. Calculate the route before starting.';};
  $('new-journey').onclick=()=>{reset();seek(0);$('status').textContent='Choose walking or running, then calculate a new route.';};
  for(const id of ['departure','limit'])$(id).onchange=()=>{reset();if(id==='departure')durationOptions();seek(0);};
  const solarSelect=document.querySelector('#solar-date');
  $('solar-day').value=solarSelect?.value||meta.environment.solar_default_day;environment.setSolarDay($('solar-day').value);
  function changeSolar(day){environment.setSolarDay(day);$('solar-day').value=day;if(solarSelect)solarSelect.value=day;reset();seek(0);$('status').textContent='Sunlight scenario changed. Calculate the route again.';}
  $('solar-day').onchange=()=>changeSolar($('solar-day').value);
  const solarListener=()=>changeSolar(solarSelect.value);solarSelect?.addEventListener('change',solarListener);
  $('departure').addEventListener('input',()=>{reset();durationOptions();seek(0);});
  $('time').oninput=()=>{playing=false;$('play').textContent='Play journey';seek(+$('time').value);};$('play').onclick=()=>{if(!result)return;if(elapsed>=(result?.routes[1].duration_s??(meta.journey_horizon_s-departureSeconds())))seek(0);playing=!playing;$('play').textContent=playing?'Pause journey':'Play journey';};
  document.querySelector('#tabs').addEventListener('click',event=>{if(event.target!==mode&&active)setActive(false);});
  $('health-ring').title='100 × exp(−ln(100/90) × burden): pollution 35%, thermal comfort (air + sunlight proxy) 15%, personal breathing deviation 50% with 1.5× deviation sensitivity. Experimental index, not clinical. No elapsed-time penalty.';
  function updateSelection(){
    origin=locations.get(selectedJourney.origin).node;goal=locations.get(selectedJourney.destination).node;
    $('journey').value=selectedJourney.id;
    $('journey-summary').textContent=journeyLabel(selectedJourney);
    for(const path of panel.querySelectorAll('[data-journey]')){
      const chosen=path.dataset.journey===selectedJourney.id;
      path.setAttribute('stroke',chosen?'#ff4fa3':'#6c999a');path.setAttribute('stroke-width',chosen?'5':'2');
    }
  }
  $('journey').replaceChildren(...catalog.journeys.map(j=>new Option(journeyLabel(j),j.id)));
  // The atlas uses the actual saved route centreline sampled for display only.
  const atlas=document.createElementNS('http://www.w3.org/2000/svg','svg');
  atlas.setAttribute('viewBox','0 0 320 320');atlas.setAttribute('aria-label','Map of 15 saved walking journeys');
  atlas.style.cssText='width:100%;background:#142b36;border-radius:8px';
  const xmin=-4100,xmax=4100,ymin=-4100,ymax=4100;
  const xy=p=>[16+288*(p[0]-xmin)/(xmax-xmin),304-288*(p[1]-ymin)/(ymax-ymin)];
  for(const journey of catalog.journeys){
    const path=document.createElementNS(atlas.namespaceURI,'path');
    path.setAttribute('d',journey.overview_points.map((p,i)=>(i?'L':'M')+xy(p).join(',')).join(' '));
    path.setAttribute('fill','none');path.dataset.journey=journey.id;
    path.setAttribute('tabindex','0');path.setAttribute('role','button');path.setAttribute('aria-label',journeyLabel(journey));
    path.style.cursor='pointer';const title=document.createElementNS(atlas.namespaceURI,'title');title.textContent=journeyLabel(journey);path.append(title);
    const choose=()=>{if(busy)return;selectedJourney=journey;updateSelection();calculate();};
    path.onclick=choose;path.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}};atlas.append(path);
  }
  for(const [i,place] of catalog.locations.entries()){
    const [x,y]=xy(place.point),circle=document.createElementNS(atlas.namespaceURI,'circle');circle.setAttribute('cx',x);circle.setAttribute('cy',y);circle.setAttribute('r','3');circle.setAttribute('fill','#d8f2ec');
    const title=document.createElementNS(atlas.namespaceURI,'title');title.textContent=place.label;circle.append(title);atlas.append(circle);
  }
  const north=document.createElementNS(atlas.namespaceURI,'text');north.setAttribute('x','290');north.setAttribute('y','15');north.setAttribute('fill','#cde7e1');north.textContent='N ↑';atlas.append(north);
  $('route-atlas').append(atlas);
  $('journey').onchange=()=>{selectedJourney=findJourney(catalog,$('journey').value);updateSelection();calculate();};
  updateSelection();
  flags();seek(0);
  let last=performance.now(),animation;
  function tick(now){animation=requestAnimationFrame(tick);const dt=Math.min(.25,(now-last)/1000);last=now;if(document.hidden||(!active&&!isSharedView()))return;if(playing){seek(elapsed+dt*+$('speed').value);if(elapsed>=(result?.routes[1].duration_s??(meta.journey_horizon_s-departureSeconds()))){playing=false;$('play').textContent='Play journey';}}else person.updateCamera(camera);for(const h of signals.heads)h.visible=Math.hypot(h.position.x-camera.position.x,h.position.z-camera.position.z)<700;}
  animation=requestAnimationFrame(tick);
  const api={group,person,meta,signals,environment,
    get time(){return departureSeconds()+elapsed},get playing(){return playing},get speed(){return +$('speed').value},get start(){return departureSeconds()},get end(){return result?departureSeconds()+result.routes[1].duration_s:meta.journey_horizon_s},
    seekWorld(t){playing=false;$('play').textContent='Play journey';seek(result&&t>=departureSeconds()+result.routes[1].duration_s-.100001?result.routes[1].duration_s:t-departureSeconds());},
    setSpeed(v){if(!Array.from($('speed').options).some(o=>+o.value===+v))$('speed').add(new Option(v+'×',v));$('speed').value=v;speedNote();},
    setPlaying(v){if(v&&elapsed>=(result?.routes[1].duration_s??(meta.journey_horizon_s-departureSeconds())))seek(0);playing=Boolean(v);$('play').textContent=playing?'Pause journey':'Play journey';},
get result(){return result},get active(){return active},get elapsed(){return elapsed},get endpoints(){return {origin,goal}},get following(){return $('follow').checked},seek,focus,calculate,setActive,setFollow,
    selectJourney(id){if(busy)return;selectedJourney=findJourney(catalog,id);updateSelection();return calculate();},
    dispose(){disposed=true;solarSelect?.removeEventListener('change',solarListener);controls.removeEventListener('start',manualCamera);cancelAnimationFrame(animation);clearRoute();signals.dispose();group.traverse(o=>{o.geometry?.dispose();o.material?.map?.dispose();o.material?.dispose();});scene.remove(group);panel.remove();mode.remove();style.remove();}};
  window.canopyPedestrian=api;onTime(api.time,environment);
  if(new URLSearchParams(location.search).get('pedestrian')==='1')setActive(true);
  if(new URLSearchParams(location.search).get('walkrun')==='1') await calculate();
  const savedElapsed=Number(launch.get('walk-elapsed'));
  if(result&&launch.has('walk-elapsed')&&Number.isFinite(savedElapsed)&&savedElapsed>=0)seek(savedElapsed);
  return api;
}
