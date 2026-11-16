"""Derive a separate pedestrian overlay from CANOPY's own mapped walking paths.

Never edits source lanes/traffic, imports the donor network, or removes paths due
to environmental masks. XY intersections are noded only within the same level.
"""
from pathlib import Path
from collections import defaultdict, Counter
import base64, hashlib, json, math, gzip
import numpy as np
from shapely.geometry import LineString, Point
from shapely.ops import unary_union, substring
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / 'scenes/imperial_corridor_8km/context'
OUT = ROOT / 'pedestrian/generated'
GRID_VALUES = None

def visible_parts(row):
    """Canopy's `covered` is a list of hidden segment indices, not a way flag.

    Match its original viewer's skip set. Keep contiguous unmarked runs and
    preserve a real break at each covered segment; never bridge that break.
    """
    covered = row.get('covered', [])
    if isinstance(covered, bool):
        covered = range(len(row['line'])-1) if covered else []
    hidden = set(covered)
    run = []
    for i, (a,b) in enumerate(zip(row['line'],row['line'][1:])):
        if i in hidden:
            if len(run)>1: yield LineString(run)
            run=[]
        else:
            if not run: run=[a]
            run.append(b)
    if len(run)>1: yield LineString(run)

def join_bridge_approaches(nodes, edges, crossings, source_ends):
    """Join exact mapped endpoints where native deck and terrain heights agree.

    Grade labels change at a bridge entrance. Do not connect crossing interiors,
    nearby paths, or endpoints with a vertical separation above 10 cm.
    """
    xy=lambda p:tuple(round(v,4) for v in p[:2])
    ground={xy(p):n for n,p in nodes.items() if n.startswith('0:0:0:') and xy(p) in source_ends[(0,False,False)]}
    aliases={}
    for e in edges:
        level=tuple(e['level'])
        if not level[1] or level[0]<=0: continue
        for n in (e['u'],e['v']):
            p=nodes[n];position=xy(p);target=ground.get(position)
            if position in source_ends[level] and target is not None and abs(p[2]-nodes[target][2])<=.1:
                aliases[n]=target
    for e in edges:
        for key,index in [('u',0),('v',-1)]:
            if e[key] in aliases:
                e[key]=aliases[e[key]]
                # Only the overlay entrance height is reconciled (<=10 cm).
                e['points'][index]=nodes[e[key]][:3]
    for c in crossings:
        c['edge']=[aliases.get(n,n) for n in c['edge']]
        for i in [0,-1]:
            if c['edge'][i] in aliases.values():c['points'][i]=nodes[c['edge'][i]][:3]
    return len(aliases)

def preserve_parallel_walks(nodes, edges, counts):
    """The planner keys edges by endpoints: give alternative paths a via node.

    Subdivide only ordinary walking paths. Crossing gates retain their complete
    geometry and timing; this must not create a waiting point inside a crossing.
    """
    pairs=defaultdict(list)
    for e in edges:pairs[tuple(sorted((e['u'],e['v'])))].append(e)
    result=[]
    for rows in pairs.values():
        # Keep an unsplit crossing when present, otherwise the shortest path.
        rows.sort(key=lambda e:(e['crossing_id'] is None,e['distance'][-1]))
        seen=[]
        for index,e in enumerate(rows):
            line=LineString([p[:2] for p in e['points']])
            if any(line.equals(other) for other in seen):continue
            seen.append(line)
            if index==0 or e['crossing_id']:
                result.append(e);continue
            ds=np.asarray(e['distance']);points=np.asarray(e['points']);middle=ds[-1]/2
            p=[float(np.interp(middle,ds,points[:,i])) for i in range(3)]
            via=f"walk-via:{len(nodes)}"
            nodes[via]=p+[0.]
            j=int(np.searchsorted(ds,middle,side='right'))
            before=points[:j].tolist()+[p];after=[p]+points[j:].tolist()
            for u,v,pts,dist in [(e['u'],via,before,ds[:j].tolist()+[middle]),
                                 (via,e['v'],after,[0.]+(ds[j:]-middle).tolist())]:
                result.append(dict(e,u=u,v=v,points=pts,distance=dist,routing_subdivision=True))
            counts['retained_parallel_walking_paths']+=1
    return result

def grid_sample(meta, x, y):
    global GRID_VALUES
    if GRID_VALUES is None:
        GRID_VALUES = np.frombuffer(base64.b64decode(meta['z']), dtype='<i2').reshape(meta['ny'], meta['nx'])
    values = GRID_VALUES
    u = np.clip((np.asarray(x) - meta['x0']) / meta['dx'], 0, meta['nx'] - 1)
    v = np.clip((np.asarray(y) - meta['y0']) / meta['dx'], 0, meta['ny'] - 1)
    a = np.minimum(np.floor(u).astype(int), meta['nx'] - 2)
    b = np.minimum(np.floor(v).astype(int), meta['ny'] - 2)
    fx, fy = u - a, v - b
    q = values[b,a]*(1-fx)*(1-fy)+values[b,a+1]*fx*(1-fy)+values[b+1,a]*(1-fx)*fy+values[b+1,a+1]*fx*fy
    return meta['base_m'] + meta['scale_m']*q

def build():
    src = CONTEXT / 'vector_landscape/source/scene-meta.json'
    data = json.loads(src.read_bytes())
    terrain = json.loads((CONTEXT / 'terrain/terrain.json').read_bytes())['terrain']
    native=json.loads(gzip.decompress((CONTEXT/'terrain/road-network.json.gz').read_bytes()))
    decks=[]
    for lane in native['lanes']:
        if lane['edge'] is None:continue
        edge=native['edges'][lane['edge']]
        if 'bridge' not in edge.get('structure',[]):continue
        xy=np.asarray(lane['shape']);line=LineString(xy[:,:2])
        if line.length>0:decks.append((line,xy,np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy[:,:2],axis=0),axis=1))],edge.get('level',1)))
    deck_tree=STRtree([d[0] for d in decks])
    groups, roads = defaultdict(list), defaultdict(list)
    source_ends=defaultdict(set)
    counts = Counter()
    for row in data['roads']:
        if len(row['line']) < 2: continue
        level = (row.get('level', 0), bool(row.get('bridge')), False)
        walking = row['cls'] in {'footway', 'path', 'pedestrian', 'steps'}
        parts = [line for line in visible_parts(row) if line.length>1e-8]
        if walking:
            counts['source_walking_lines'] += 1
            if row.get('covered'):
                hidden=row['covered']
                counts['hidden_walking_segments'] += len(hidden) if isinstance(hidden,list) else len(row['line'])-1
                if parts:
                    counts['restored_partly_hidden_paths'] += 1
                    counts['restored_visible_runs'] += len(parts)
                    counts['restored_visible_length_m'] += sum(line.length for line in parts)
        for line in parts:
            if walking:
                groups[level].append(line)
                source_ends[level].update(tuple(round(v,4) for v in p) for p in [line.coords[0],line.coords[-1]])
            elif row['cls'] not in {'cycleway', 'bridleway', 'track', 'unknown'}:
                roads[level].append((line, line.buffer(max(1., float(row['w']) / 2), cap_style=2)))
    nodes, edges, crossings = {}, [], []
    for level, walking in sorted(groups.items()):
        merged = unary_union(walking)
        geometry = list(merged.geoms) if hasattr(merged, 'geoms') else [merged]
        road_rows = roads.get(level, [])
        envelopes = [r[1] for r in road_rows]
        index = STRtree(envelopes)
        for line in geometry:
            if line.length <= 1e-8: continue
            candidates = index.query(line)
            envelope = unary_union([envelopes[j] for j in candidates]) if len(candidates) else None
            cuts = {0., line.length}
            def cut(g):
                if g.is_empty: return
                if g.geom_type == 'Point': cuts.add(line.project(g))
                elif hasattr(g, 'geoms'):
                    for child in g.geoms: cut(child)
                elif g.geom_type == 'LineString':
                    cuts.update(line.project(Point(p)) for p in [g.coords[0], g.coords[-1]])
            if envelope is not None: cut(line.intersection(envelope.boundary))
            cuts = sorted(cuts)
            for a,b in zip(cuts,cuts[1:]):
                # A short section is still a topological connection. Road-envelope
                # cuts often create centimetre pieces at existing junctions.
                # Dropping them strands otherwise continuous mapped paths.
                if b-a <= 1e-8: continue
                part = substring(line,a,b)
                crossing = False
                if envelope is not None and envelope.covers(part.interpolate(.5, normalized=True)):
                    for j in candidates:
                        centre = road_rows[j][0]
                        if not part.intersects(centre): continue
                        q = centre.project(part.interpolate(.5,normalized=True))
                        tangent = np.subtract(centre.interpolate(min(centre.length,q+1)).coords[0], centre.interpolate(max(0,q-1)).coords[0])
                        direction = np.subtract(part.coords[-1],part.coords[0])
                        den = np.linalg.norm(tangent)*np.linalg.norm(direction)
                        if den and abs(tangent@direction)/den < math.cos(math.pi/6): crossing=True; break
                xy = np.asarray(part.coords)
                # Heights are presentation only; no slope-dependent speed/cost.
                height = grid_sample(terrain,xy[:,0],xy[:,1])
                if level[1] or level[0]>0:
                    supported=True
                    for i,p in enumerate(xy):
                        point=Point(p);matches=[]
                        for j in deck_tree.query(point.buffer(12)):
                            deck,xyz,ds,deck_level=decks[j]
                            if deck_level!=(level[0] or 1):continue
                            distance=deck.distance(point)
                            if distance<=12:matches.append((distance,j))
                        if not matches:supported=False;break
                        _,j=min(matches);deck,xyz,ds,_=decks[j]
                        height[i]=np.interp(deck.project(point),ds,xyz[:,2])
                    if not supported:
                        counts['unresolved_elevated_sections']+=1
                        continue
                    counts['bridge_sections'] += 1
                if level[0]<0:
                    # No native tunnel deck/depth or indoor accessibility is supplied.
                    counts['unresolved_tunnel_sections']+=1
                    continue
                ids = [f'{level[0]}:{int(level[1])}:{int(level[2])}:{p[0]:.4f},{p[1]:.4f}' for p in [xy[0],xy[-1]]]
                if ids[0] == ids[1]: continue
                if b-a < .1: counts['retained_sub_10cm_sections'] += 1
                for ident,p,h in zip(ids,[xy[0],xy[-1]],[height[0],height[-1]]): nodes[ident]=[float(p[0]),float(p[1]),float(h),0.]
                distance = np.r_[0,np.cumsum(np.linalg.norm(np.diff(xy,axis=0),axis=1))]
                cid = f'canopy-walk-{len(crossings)}' if crossing else None
                points = np.c_[xy,height].tolist()
                edges.append(dict(u=ids[0],v=ids[1],points=points,distance=distance.tolist(),
                    name='Modelled pedestrian crossing' if crossing else 'Canopy mapped walking path',
                    crossing_id=cid,level=list(level),source='CANOPY landscape walking geometry'))
                if crossing:
                    crossings.append(dict(id=cid,edge=ids,points=points,length_m=float(distance[-1]),
                        program=dict(red_s=40.,green_s=10.,clearance_s=math.ceil(distance[-1]/(4/3)+2),origin_s=0.),
                        evidence='Mapped pedestrian path crosses mapped vehicle road at same level; timing is a pedestrian-only assumption, not coupled to recorded cars'))
    counts['native_height_matched_bridge_joins']=join_bridge_approaches(nodes,edges,crossings,source_ends)
    edges=preserve_parallel_walks(nodes,edges,counts)
    # Parallel duplicate endpoint pairs are collapsed only within the new overlay.
    unique = {}
    for edge in edges:
        key = tuple(sorted((edge['u'],edge['v'])))
        if key not in unique or edge['distance'][-1] < unique[key]['distance'][-1]: unique[key] = edge
    edges = list(unique.values())
    active = {e['crossing_id'] for e in edges}
    crossings = [c for c in crossings if c['id'] in active]
    adj = defaultdict(list)
    for e in edges: adj[e['u']].append(e['v']); adj[e['v']].append(e['u'])
    unseen, components = set(adj), []
    while unseen:
        stack=[min(unseen)];unseen.remove(stack[0]);component=[]
        while stack:
            n=stack.pop();component.append(n)
            for v in adj[n]:
                if v in unseen: unseen.remove(v);stack.append(v)
        components.append(sorted(component))
    components.sort(key=lambda c:(-len(c),c[0]));component_id={n:i for i,c in enumerate(components) for n in c}
    pavement={n for e in edges if not e['crossing_id'] for n in (e['u'],e['v'])}
    for c in crossings:
        c['component']=component_id[c['edge'][0]]
        c['both_pavement_approaches']=all(n in pavement for n in c['edge'])
    nodes={k:v for k,v in nodes.items() if k in adj}
    counts.update(nodes=len(nodes),undirected_links=len(edges),crossings=len(crossings),components=len(components),
                  largest_component_nodes=len(components[0]),environmental_exclusions=0)
    result=dict(nodes=nodes,edges=edges,crossings=crossings,components=components,summary=dict(counts),
        provenance=dict(source=src.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
        topology='Geometric same-level noding of visible mapped footway/path/pedestrian/steps. Covered segment indices are skipped individually. Bridge entrances join only at exact shared mapped endpoints with native deck/terrain heights within 0.1 m. Not surveyed access. No added pavement along vehicle lanes; no proximity bridges across gaps.',
        traffic='Original CANOPY vehicle graph and replays untouched. Pedestrian signals are independent demo assumptions.'))
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'network.json').write_text(json.dumps(result,separators=(',',':'),allow_nan=False),encoding='utf-8')
    print(json.dumps(dict(counts),indent=2))

if __name__=='__main__': build()
