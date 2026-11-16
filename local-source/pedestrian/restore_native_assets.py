"""Fetch only checksum-identical missing CANOPY files using public release ZIP ranges."""
import io,json,hashlib,urllib.request,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
URL='https://github.com/acse-yl222/physics-grounded-4d-world-model-framework/releases/download/imperial-corridor-native-20261102/02-fields-4m.zip'
class Remote(io.RawIOBase):
    def __init__(self):self.pos=0;self.length=1612075430
    def seekable(self):return True
    def seek(self,offset,whence=0):
        self.pos=offset if whence==0 else self.pos+offset if whence==1 else self.length+offset
        return self.pos
    def tell(self):return self.pos
    def read(self,size=-1):
        if size<0:size=self.length-self.pos
        if size==0:return b''
        request=urllib.request.Request(URL,headers={'Range':f'bytes={self.pos}-{self.pos+size-1}'})
        with urllib.request.urlopen(request,timeout=60) as r:
            if r.status!=206 or not r.headers.get('Content-Range','').startswith(f'bytes {self.pos}-'):
                raise RuntimeError('Release server does not support verified byte ranges')
            result=r.read(size+1)
        if len(result)!=size:raise RuntimeError('Incorrect range length')
        self.pos+=size;return result

if __name__=='__main__':
    manifest={r['path']:r for r in json.loads((ROOT/'download-manifest.json').read_bytes())['files'] if not (ROOT/r['path']).exists()}
    with zipfile.ZipFile(Remote()) as archive:
        count=0
        for item in archive.infolist():
            name=item.filename
            if 'scenes/' not in name:continue
            rel=name[name.index('scenes/'):]
            if rel not in manifest:continue
            data=archive.read(item)
            if hashlib.sha256(data).hexdigest()!=manifest[rel]['sha256']:continue
            path=ROOT/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);count+=1
            print('Verified original asset:',rel,flush=True)
        print('Restored',count)
