from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
original=json.loads((ROOT/'pedestrian/original-canopy-hashes.json').read_bytes())
allowed={'asset-router.js','viewer/3d/main.js','viewer/3d/corridor-context.js','download-manifest.json'}
changed=[p for p,h in original.items() if not (ROOT/p).is_file() or hashlib.sha256((ROOT/p).read_bytes()).hexdigest()!=h]
assert set(changed)<=allowed,changed
manifest=json.loads((ROOT/'download-manifest.json').read_bytes())
for entry in manifest['files']:
    path=ROOT/entry['path']
    assert path.is_file(),entry['path']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'],entry['path']
assert not any('/private/' in e['path'] or '/cache/' in e['path'] for e in manifest['files'])
report={'passed':True,'original_files':len(original),'changed_entrypoints_only':changed,
        'verified_public_assets':len(manifest['files']),
        'original_road_traffic_terrain_fields_unchanged':True}
(ROOT/'pedestrian/cache/preservation-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
