"""Compare the new overlay with the retained pre-repair overlay; no source edits."""
from collections import defaultdict
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'pedestrian/dependencies'))
from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree

cache=ROOT/'pedestrian/cache'
old=json.loads((cache/'network-before-visible-segments-fix.json').read_bytes())
new=json.loads((ROOT/'pedestrian/generated/network.json').read_bytes())
oc={n:i for i,c in enumerate(old['components']) for n in c}
nc={n:i for i,c in enumerate(new['components']) for n in c}
merged=[sorted({oc[n] for n in c if n in oc}) for c in new['components']]
joins=sum(max(0,len(c)-1) for c in merged)
def indices(graph):
    levels=defaultdict(list)
    for e in graph['edges']:levels[tuple(e['level'])].append(LineString([p[:2] for p in e['points']]))
    return {level:(lines,STRtree(lines)) for level,lines in levels.items()}
old_indices=indices(old);new_indices=indices(new)
def uncovered(line,index):
    lines,tree=index
    nearby=tree.query(line.buffer(1e-6))
    if len(nearby)==0:return line.length
    return line.difference(unary_union([lines[i] for i in nearby]).buffer(1e-6)).length
coverage={str(level):sum(uncovered(line,new_indices[level]) for line in lines)
          for level,(lines,_) in old_indices.items()}
assert all(v<.001 for v in coverage.values()),coverage
total=lambda graph:sum(e['distance'][-1] for e in graph['edges'])
largest=lambda graph,comp:sum(e['distance'][-1] for e in graph['edges'] if comp[e['u']]==0)
fresh=sorted(new['edges'],key=lambda e:(e['points'][0][0]-1776)**2+(e['points'][0][1]+848)**2)
restored=next(e for e in fresh if e['distance'][-1]>10 and not e['crossing_id'] and
              uncovered(LineString(e['points']),old_indices[tuple(e['level'])])>10)
bridge=next(e for e in new['edges'] if e['level'][1] and e['u'].startswith('0:0:0:') and e['v'].startswith('0:0:0:'))
report=dict(before=old['summary'],after=new['summary'],old_components_joined=joins,
            old_geometry_missing_length_m=coverage,total_mapped_length_m=[total(old),total(new)],
            largest_connected_length_m=[largest(old,oc),largest(new,nc)],
            regression_requests=[dict(origin=e['u'],goal=e['v'],departure_s=240,max_minutes=30) for e in [restored,bridge]])
(cache/'visible-segments-repair.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
