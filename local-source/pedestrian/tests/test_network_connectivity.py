"""Retain mapped junction pieces, without joining genuine gaps or levels."""
import base64
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from collections import defaultdict,Counter
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'pedestrian/dependencies'),str(ROOT/'pedestrian')]
import build_network

class NetworkConnectivityTests(unittest.TestCase):
    def test_parallel_walks_preserve_both_geometries_without_splitting_crossings(self):
        from shapely.geometry import LineString
        from shapely.ops import unary_union
        nodes={'a':[0,0,0,0],'b':[2,0,0,0]}
        rows=[dict(u='a',v='b',points=[[0,0,0],[2,0,0]],distance=[0,2],crossing_id='crossing'),
              dict(u='a',v='b',points=[[0,0,0],[1,1,0],[2,0,0]],distance=[0,2**.5,2*2**.5],crossing_id=None)]
        counts=Counter();result=build_network.preserve_parallel_walks(nodes,rows,counts)
        self.assertEqual(len(result),3)
        self.assertEqual([e for e in result if e['crossing_id']],[rows[0]])
        before=unary_union([LineString(e['points']) for e in rows])
        after=unary_union([LineString(e['points']) for e in result])
        self.assertTrue(before.equals(after))
        self.assertEqual(len({(e['u'],e['v']) for e in result}),3)
        self.assertEqual(counts['retained_parallel_walking_paths'],1)

    def test_covered_indices_keep_outdoor_runs_and_do_not_bridge_hidden_segments(self):
        row=dict(line=[[0,0],[1,0],[2,0],[3,0],[4,0]],covered=[1])
        parts=list(build_network.visible_parts(row))
        self.assertEqual([list(p.coords) for p in parts],[[(0,0),(1,0)],[(2,0),(3,0),(4,0)]])
        self.assertEqual(sum(p.length for p in parts),3)
        self.assertEqual(list(build_network.visible_parts(dict(line=[[0,0],[1,0]],covered=[0]))),[])
        # An unmarked crossing road must still intersect an outdoor run.
        from shapely.geometry import LineString
        self.assertTrue(parts[1].intersects(LineString([[3,-1],[3,1]])))

    def test_bridge_entrances_need_shared_source_endpoints_and_matching_heights(self):
        nodes={'0:0:0:a':[0,0,2,0],'0:0:0:b':[1,0,2,0],
               '0:0:0:c':[2,0,2,0],'1:1:0:a':[0,0,2.05,0],
               '1:1:0:b':[1,0,4,0],'1:1:0:c':[2,0,2.05,0]}
        edges=[dict(u='1:1:0:a',v='1:1:0:b',level=[1,True,False],points=[[0,0,2.05],[1,0,4]]),
               dict(u='1:1:0:b',v='1:1:0:c',level=[1,True,False],points=[[1,0,4],[2,0,2.05]])]
        ends=defaultdict(set,{(0,False,False):{(0,0),(1,0),(2,0)},(1,True,False):{(0,0),(1,0)}})
        self.assertEqual(build_network.join_bridge_approaches(nodes,edges,[],ends),1)
        self.assertEqual(edges[0]['u'],'0:0:0:a')
        self.assertEqual(edges[0]['points'][0],[0,0,2])
        self.assertEqual(edges[0]['v'],'1:1:0:b') # above ground: not a junction
        self.assertEqual(edges[1]['v'],'1:1:0:c') # bridge interior: not an entrance

    def test_centimetre_junction_survives_road_envelope_cut(self):
        # Keep generated fixture files under the verified workspace cache.
        cache=(ROOT/'pedestrian/cache').resolve()
        assert cache.is_relative_to(ROOT.resolve())
        cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            root=Path(tmp); context=root/'context';out=root/'generated'
            (context/'vector_landscape/source').mkdir(parents=True)
            (context/'terrain').mkdir()
            def path(points,cls='footway',**extra):
                return dict(line=points,cls=cls,w=2,**extra)
            # y=1 is the road edge. The mapped junction at y=1.05 must
            # remain connected through the 5 cm piece, not become a gap.
            rows=[path([[0,0],[0,1.05]]),path([[0,1.05],[0,3]]),
                  path([[-5,0],[5,0]],'residential'),
                  path([[0,4],[0,5]]), # genuine 1 m gap: keep separate
                  path([[-1,2],[1,2]],level=-1)] # unknown tunnel: no join
            (context/'vector_landscape/source/scene-meta.json').write_text(json.dumps(dict(roads=rows)))
            terrain=dict(z=base64.b64encode(bytes(8)).decode(),nx=2,ny=2,x0=-10,y0=-10,dx=20,base_m=0,scale_m=1)
            (context/'terrain/terrain.json').write_text(json.dumps(dict(terrain=terrain)))
            import gzip
            (context/'terrain/road-network.json.gz').write_bytes(gzip.compress(b'{"lanes":[],"edges":[]}'))
            with patch.multiple(build_network,ROOT=root,CONTEXT=context,OUT=out,GRID_VALUES=None),contextlib.redirect_stdout(io.StringIO()):
                build_network.build()
            graph=json.loads((out/'network.json').read_bytes())
            components={n:i for i,c in enumerate(graph['components']) for n in c}
            node=lambda x,y:f'0:0:0:{x:.4f},{y:.4f}'
            self.assertEqual(components[node(0,0)],components[node(0,3)])
            self.assertNotEqual(components[node(0,3)],components[node(0,4)])
            self.assertTrue(any(abs(e['distance'][-1]-.05)<1e-8 for e in graph['edges']))
            self.assertEqual(len(graph['components']),2)
            self.assertTrue(all(e['level']==[0,False,False] for e in graph['edges']))

if __name__=='__main__':unittest.main()
