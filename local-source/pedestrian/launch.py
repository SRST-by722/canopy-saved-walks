"""Relocatable release launcher: original viewer + private pedestrian backend."""
from pathlib import Path
import argparse,json,sys,threading,webbrowser
from urllib.parse import urlsplit,unquote
import posixpath
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'pedestrian'),str(ROOT/'pedestrian/health_planning')]
from serve import Handler,ThreadingHTTPServer,CanopyPlanner

class ReleaseHandler(Handler):
    # Serve only the viewer's declared public files. Runtime, release manifests,
    # participant/model inputs and developer handoffs are never browser assets.
    public={e['path'] for e in json.loads((ROOT/'download-manifest.json').read_bytes())['files']}|{'download-manifest.json'}
    def permitted(self):
        path=posixpath.normpath(unquote(urlsplit(self.path).path)).lstrip('/')
        if path.startswith('api/'):return True
        if path in {'','.'}:path='index.html'
        if path in self.public:return True
        return path.rstrip('/')+'/index.html' in self.public
    def do_GET(self):
        if not self.permitted():return self.send_error(403,'Not a public viewer asset')
        return super().do_GET()
    def do_HEAD(self):
        if not self.permitted():return self.send_error(403,'Not a public viewer asset')
        return super().do_HEAD()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    (ROOT/'pedestrian/cache').mkdir(exist_ok=True)
    server=None
    for port in ([args.port] if args.port else range(8811,8821)):
        try:server=ThreadingHTTPServer(('127.0.0.1',port),ReleaseHandler);break
        except OSError:
            if args.port:raise
    if server is None:raise RuntimeError('Ports 8811-8820 are busy; run with --port followed by a free port.')
    print('Loading CANOPY and the breathing model...',flush=True)
    server.planner=CanopyPlanner(ROOT);server.lock=threading.Lock()
    url=f'http://127.0.0.1:{server.server_address[1]}/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1&walkrun=1'
    print('Ready: '+url+'\nKeep this window open. Press Ctrl+C to stop.',flush=True)
    if not args.no_browser:threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
