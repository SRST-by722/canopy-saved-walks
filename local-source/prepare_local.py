"""Assemble the local solver app without changing the GitHub Pages viewer."""
from pathlib import Path
import hashlib
import json
import shutil

SOURCE = Path(__file__).resolve().parent
REPO = SOURCE.parent
DEST = SOURCE / '.work' / 'app'

def main():
    manifest = json.loads((SOURCE / 'download-manifest.json').read_bytes())
    # Verify every source before writing the assembly; fail on an incompatible checkout.
    assets = []
    for entry in manifest['files']:
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid asset path')
        override = SOURCE / 'overrides' / relative
        source = override if override.is_file() else REPO / relative
        if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != entry['sha256']:
            raise RuntimeError(f'Missing or changed local-app asset: {relative}')
        assets.append((source, relative))
    for source, relative in assets:
        target = DEST / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copy2(SOURCE / 'download-manifest.json', DEST / 'download-manifest.json')
    shutil.copytree(SOURCE / 'pedestrian', DEST / 'pedestrian', dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc', 'cache', 'private'))
    (DEST / 'pedestrian' / 'cache').mkdir(exist_ok=True)
    model = DEST / 'pedestrian' / 'private' / 'breathing_model'
    model.mkdir(parents=True, exist_ok=True)
    print(f'Local app prepared: {DEST}')
    print(f'Copy your authorised breathing_model files into: {model}')
    print('Then run: python local-source/.work/app/pedestrian/launch.py')

if __name__ == '__main__':
    main()
