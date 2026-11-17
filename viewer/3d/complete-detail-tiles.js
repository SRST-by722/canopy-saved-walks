// Retain every source mesh and transform; no distance eviction or simplification.
import {drapeBuildings} from './corridor-terrain.js';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// co_demo_001: focus (optional) returns the viewer [x, z] to load around; each worker then takes the pending asset whose tile is nearest to it.
export function createDetailTiles({scene, coarse, indexUrl, priorityCentre = null, focus = null, onChange = () => {}}) {
  const group = new THREE.Group();
  group.name = 'complete_detail_geometry';
  scene.add(group);
  coarse.visible = false;
  const progress = {loaded: 0, total: 0, complete: false, errors: []};
  const loaded = [];
  let tileIndex=[];
  const badge = document.createElement('div');
  badge.id = 'complete-geometry-status';
  badge.style.cssText = 'position:fixed;bottom:12px;left:12px;z-index:30;background:#10202ee8;color:white;padding:8px 12px;border-radius:6px;font:13px sans-serif;pointer-events:none';
  document.body.append(badge);
  function status() {
    badge.textContent = progress.errors.length
      ? `Geometry incomplete · ${progress.loaded}/${progress.total} assets · ${progress.errors.length} failed (reload to retry)`
      : progress.complete ? `Complete geometry · ${loaded.length} tiles · ${progress.loaded} assets`
      : `Loading complete geometry · ${progress.loaded}/${progress.total} assets`;
  }
  status();
  const ready = (async () => {
    const response = await fetch(indexUrl);
    if (!response.ok) throw new Error(`Geometry index HTTP ${response.status}`);
    const index = await response.json();tileIndex=index.tiles;
    const jobs = [];
    const tiles = [...index.tiles];
    if(priorityCentre) tiles.sort((a,b)=>Math.hypot(a.centre_xz[0]-priorityCentre[0],a.centre_xz[1]-priorityCentre[2])-Math.hypot(b.centre_xz[0]-priorityCentre[0],b.centre_xz[1]-priorityCentre[2]));
    for (const tile of tiles) {
      const root = new THREE.Group(); root.name = `detail:${tile.id}`; group.add(root);
      const files = [tile.file, ...(tile.landmarks || []).map(l => l.file)].filter(Boolean);
      let remaining = files.length;
      for (const file of files) jobs.push({centre: tile.centre_xz, run: async loader => {
        const gltf = await loader.loadAsync(new URL(file, indexUrl).href);
        root.add(gltf.scene);
        drapeBuildings(gltf.scene);
        // These source buildings never move. Compute their world transforms once.
        group.updateWorldMatrix(true, false);
        root.updateWorldMatrix(true, false);
        gltf.scene.updateWorldMatrix(true, true);
        gltf.scene.traverse(object => {
          object.matrixAutoUpdate = false;
          object.matrixWorldAutoUpdate = false;
        });
        progress.loaded++;
        if (--remaining === 0) loaded.push(tile.id);
      }});
    }
    progress.total = jobs.length; status();
    const take = () => {
      if (!jobs.length) return null;
      let best = 0; const f = focus?.();
      if (f) { let bd = Infinity; for (let i = 0; i < jobs.length; i++) { const c = jobs[i].centre, d = Math.hypot(c[0] - f[0], c[1] - f[1]); if (d < bd) { bd = d; best = i; } } }
      return jobs.splice(best, 1)[0];
    };
    await Promise.all(Array.from({length: 3}, async () => {
      const loader = new GLTFLoader();
      for (let job; (job = take());) {
        try { await job.run(loader); }
        catch (error) { progress.errors.push(String(error)); console.error(error); }
        status(); onChange();
      }
    }));
    progress.complete = progress.errors.length === 0;
    status(); onChange();
    return loaded.length;
  })().catch(error => {progress.errors.push(String(error)); status(); console.error(error); return 0;});
  return {ready, group, progress, hasPoints(points) {if(!tileIndex.length)return false;const needed=new Set();for(const p of points){const tile=tileIndex.find(t=>Math.abs(p[0]-t.centre_xz[0])<=t.half_m&&Math.abs(p[2]-t.centre_xz[1])<=t.half_m);if(!tile)return false;needed.add(tile.id);}return [...needed].every(id=>loaded.includes(id));}, get loaded() {return [...loaded];},
    update() {coarse.visible = false;},
    setEnabled(on) {group.visible = on; coarse.visible = false; onChange();}};
}
