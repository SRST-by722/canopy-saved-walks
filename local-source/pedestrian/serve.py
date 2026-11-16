"""Local CANOPY + pedestrian API. Private model files are never served as static assets."""
from pathlib import Path
import sys, json, threading, mimetypes, posixpath
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'pedestrian/health_planning'),str(ROOT/'pedestrian')]
from canopy_planner import CanopyPlanner
mimetypes.add_type('text/javascript','.mjs')

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def end_headers(self):
        self.send_header('Cache-Control','no-store')
        super().end_headers()
    def api(self,value,status=200):
        data=json.dumps(value,allow_nan=False).encode();self.send_response(status)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=posixpath.normpath(unquote(urlsplit(self.path).path))
        if path=='/api/pedestrian/meta':return self.api(self.server.planner.metadata())
        if path.startswith('/api/'):return self.api({'error':'Unknown endpoint'},404)
        if (path=='/pedestrian' or '/pedestrian/' in path) and not path.startswith('/viewer/3d/pedestrian/'):
            return self.send_error(403,'Private integration resources')
        return super().do_GET()
    def do_HEAD(self):
        path=posixpath.normpath(unquote(urlsplit(self.path).path))
        if path=='/pedestrian' or (path.startswith('/pedestrian/')):
            return self.send_error(403,'Private integration resources')
        return super().do_HEAD()
    def do_POST(self):
        if urlsplit(self.path).path!='/api/pedestrian/plan':return self.api({'error':'Unknown endpoint'},404)
        try:
            size=int(self.headers.get('Content-Length',0))
            if not 0<size<10000:raise ValueError('Invalid request size')
            request=json.loads(self.rfile.read(size))
            if not isinstance(request,dict):raise ValueError('Expected an object')
            with self.server.lock:result=self.server.planner.plan(request)
            self.api(result)
        except (ValueError,KeyError,TypeError) as e:self.api({'error':str(e)},400)
        except Exception as e:
            import traceback;traceback.print_exc();self.api({'error':'Route calculation failed; see server log'},500)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8811);args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    server.planner=CanopyPlanner(ROOT);server.lock=threading.Lock()
    print(f'CANOPY pedestrian ready: http://127.0.0.1:{args.port}/viewer/3d/?scene=imperial_corridor_8km&pedestrian=1',flush=True)
    server.serve_forever()
