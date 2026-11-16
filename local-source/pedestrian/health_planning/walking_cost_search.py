"""Bounded, time-dependent street search for matched out-and-back walks.

The paper's environmental-cost idea is adapted to the supplied street graph.
This is NOT a wave PDE solver or a globally optimal resource-constrained solver.
Physical speed and exact walking distance never change with preference weights.
"""
from __future__ import annotations

import heapq
import itertools
from dataclasses import dataclass
import xml.etree.ElementTree as ET

import numpy as np
from PIL import Image


@dataclass
class Edge:
    u: str
    v: str
    points: np.ndarray
    distance: np.ndarray
    name: str
    walking_speed: float = 4/3  # Physical travel speed; may be a running preset.

    @property
    def length(self):
        return float(self.distance[-1])

    def at(self, distance):
        return np.column_stack([
            np.interp(distance, self.distance, self.points[:, j]) for j in range(4)
        ])


def load_network(path, spatial):
    """Keep explicit OSM connections; geometric crossings never create nodes."""
    ns = {'g': 'http://graphml.graphdrawing.org/xmlns'}
    tree = ET.parse(path)
    names = {k.attrib['id']: k.attrib['attr.name'] for k in tree.findall('g:key', ns)}
    origin = spatial['origin']
    x0, y0, _ = spatial['bounds_m']['min']
    x1, y1, _ = spatial['bounds_m']['max']

    def enu(lon, lat):
        # Same local projection used by the retained baseline (verified on anchor).
        lon, lat = np.radians(lon), np.radians(lat)
        lo, la = np.radians([origin['longitude'], origin['latitude']])
        a, e2 = 6378137., 6.69437999014e-3
        n = a/np.sqrt(1-e2*np.sin(lat)**2)
        n0 = a/np.sqrt(1-e2*np.sin(la)**2)
        dx = n*np.cos(lat)*np.cos(lon)-n0*np.cos(la)*np.cos(lo)
        dy = n*np.cos(lat)*np.sin(lon)-n0*np.cos(la)*np.sin(lo)
        dz = n*(1-e2)*np.sin(lat)-n0*(1-e2)*np.sin(la)
        return (-np.sin(lo)*dx+np.cos(lo)*dy,
                -np.sin(la)*np.cos(lo)*dx-np.sin(la)*np.sin(lo)*dy+np.cos(la)*dz)

    def attrs(el):
        return {names[v.attrib['key']]: v.text for v in el.findall('g:data', ns)}

    nodes, edges, excluded = {}, {}, 0
    for el in tree.findall('.//g:node', ns):
        a = attrs(el)
        lon, lat = float(a['x']), float(a['y'])
        x, y = enu(lon, lat)
        if x0 <= x < x1 and y0 <= y < y1:
            nodes[el.attrib['id']] = np.array([x, y, lon, lat])
    for el in tree.findall('.//g:edge', ns):
        u, v, a = el.attrib['source'], el.attrib['target'], attrs(el)
        if u not in nodes or v not in nodes:
            continue
        if (any(s in a.get('access', '').lower() for s in ['private', 'no', 'customers'])
                or a.get('foot', '').lower() in ['no', 'private', 'customers']
                or a.get('highway') in ['motorway', 'motorway_link', 'construction', 'proposed']):
            excluded += 1
            continue
        if 'geometry' in a:
            geo = np.array([[float(v) for v in p.split()] for p in
                            a['geometry'].removeprefix('LINESTRING (').removesuffix(')').split(',')])
        else:
            geo = np.array([nodes[u][2:], nodes[v][2:]])
        x, y = enu(geo[:, 0], geo[:, 1])
        xy = np.column_stack([x, y])
        if np.any((x < x0) | (x >= x1) | (y < y0) | (y >= y1)):
            continue
        if np.linalg.norm(xy[-1]-nodes[u][:2]) < np.linalg.norm(xy[0]-nodes[u][:2]):
            xy, geo = xy[::-1], geo[::-1]
        points = np.column_stack([xy, geo])
        distance = np.r_[0., np.cumsum(np.linalg.norm(np.diff(xy, axis=0), axis=1))]
        if distance[-1] <= 0:
            continue
        edge = Edge(u, v, points, distance, a.get('name', 'Unnamed path'))
        if (u, v) not in edges or edge.length < edges[u, v].length:
            edges[u, v] = edge
    graph = {}
    for key, edge in edges.items():
        reverse = edges.get((edge.v, edge.u))
        # This experiment retraces the outward path: require the same usable reverse geometry.
        if (reverse is not None and edge.points.shape == reverse.points.shape
                and np.allclose(edge.points, reverse.points[::-1], atol=1e-6)):
            graph.setdefault(edge.u, []).append(key)
    return nodes, edges, graph, excluded


class ReplayFields:
    """Exact legacy PNG decoding and interpolation; times are seconds after epoch."""
    def __init__(self, folder, spatial, solid_path=None):
        self.x0, self.y0, _ = spatial['bounds_m']['min']
        self.frames, self.paths = {}, []
        for name, last in [('poll', 99), ('temp', 60)]:
            # Only the final 24h of the 72h replay is queried.
            first = int(np.floor(2*last/3))
            paths = [folder / name / f'{k:03d}.png' for k in range(first, last+1)]
            self.frames[name] = (first, last, np.stack([
                np.asarray(Image.open(p).convert('RGB'))[:, :, 0] for p in paths]))
            self.paths.extend(paths)
        self.solid = None
        if solid_path is not None:
            # Source PNGs represent the inherited 12-16m layer. Never interpret
            # solid-cell concentration floors as clean outdoor air.
            self.solid = np.load(solid_path, mmap_mode='r')[3].astype(bool)
            self.paths.append(solid_path)
            self.row_map, self.col_map = np.indices(self.solid.shape)
            self.displacement = np.zeros(self.solid.shape, dtype=float)
            unresolved = self.solid.copy()
            rr, cc = np.where(self.solid)
            offsets = sorted([(dr, dc) for dr in range(-8, 9) for dc in range(-8, 9)
                              if 0 < dr*dr+dc*dc <= 64], key=lambda p: (p[0]**2+p[1]**2, p))
            for dr, dc in offsets:
                r, c = rr+dr, cc+dc
                inside = (r >= 0) & (c >= 0) & (r < self.solid.shape[0]) & (c < self.solid.shape[1])
                take = inside.copy()
                take[inside] &= ~self.solid[r[inside], c[inside]] & unresolved[rr[inside], cc[inside]]
                self.row_map[rr[take], cc[take]] = r[take]
                self.col_map[rr[take], cc[take]] = c[take]
                self.displacement[rr[take], cc[take]] = 4*np.hypot(dr, dc)
                unresolved[rr[take], cc[take]] = False
            self.displacement[unresolved] = np.inf

    def coverage(self, xy):
        rows = np.floor((xy[:, 1]-self.y0)/4).astype(int)
        cols = np.floor((xy[:, 0]-self.x0)/4).astype(int)
        if self.solid is None:
            return np.zeros(len(xy), dtype=bool), np.zeros(len(xy))
        return self.solid[rows, cols], self.displacement[rows, cols]

    def sample(self, xy, seconds):
        xy = np.asarray(xy)
        seconds = np.broadcast_to(seconds, len(xy))
        if np.any(seconds < 0) or np.any(seconds > 86400):
            raise ValueError('Exposure time outside supplied 24h replay')
        rows = np.floor((xy[:, 1]-self.y0)/4).astype(int)
        cols = np.floor((xy[:, 0]-self.x0)/4).astype(int)
        if self.solid is not None:
            if (np.any(rows < 0) or np.any(cols < 0) or np.any(rows >= self.solid.shape[0])
                    or np.any(cols >= self.solid.shape[1])):
                raise ValueError('Route outside environmental grid')
            if np.any(~np.isfinite(self.displacement[rows, cols])):
                raise ValueError('No outdoor field within 32m; cannot evaluate this route')
            rows, cols = self.row_map[rows, cols], self.col_map[rows, cols]
        values = []
        for name in ['poll', 'temp']:
            first, last, images = self.frames[name]
            if np.any(rows < 0) or np.any(cols < 0) or np.any(rows >= images.shape[1]) or np.any(cols >= images.shape[2]):
                raise ValueError('Route outside supplied environmental grid')
            z = (48*3600+seconds)/(72*3600)*last
            lo = np.floor(z).astype(int)
            hi = np.minimum(lo+1, last)
            a = images[lo-first, rows, cols].astype(float)
            b = images[hi-first, rows, cols].astype(float)
            if name == 'poll':
                a, b = 10**(-1+a/255*5), 10**(-1+b/255*5)
            else:
                a, b = 30+a/255*3, 30+b/255*3
            values.append(a*(1-z+lo)+b*(z-lo))
        return values[0], values[1]


def route_points(edge_keys, edges, outward_m=1200.):
    points, distances, walked = [], [], 0.
    for key in edge_keys:
        edge = edges[key]
        take = min(edge.length, outward_m-walked)
        ds = np.unique(np.r_[edge.distance[edge.distance < take], take])
        points.extend(edge.at(ds)[1:] if points else edge.at(ds))
        distances.extend((walked+ds[1:]).tolist() if distances else (walked+ds).tolist())
        walked += take
        if walked >= outward_m-1e-8:
            break
    if abs(walked-outward_m) > 1e-6:
        raise ValueError('Path does not meet activity budget')
    pts, ds = np.array(points), np.array(distances)
    return np.concatenate([pts, pts[-2::-1]]), np.r_[ds, 2*outward_m-ds[-2::-1]]


def search(graph, edges, anchor, fields, departure_s, pollution_scale,
           weight=.5, outward_m=1200., speed=4/3, max_expansions=6000,
           distance_bin_m=25., labels_per_bin=3, max_candidates=40):
    """Bounded label search with exact distance, no repeated outward nodes.

    Paired outward/return samples make environmental penalties additive:
    outward coordinate s is visited at departure+s/v and departure+(2L-s)/v.
    Distance buckets and label caps are heuristic pruning, not optimality proofs.
    """
    counter = itertools.count()
    queue = [(0., next(counter), anchor, 0., (anchor,), (), 0.)]
    labels, terminals = {}, []
    expanded, discarded = 0, 0
    while queue and expanded < max_expansions:
        _, _, u, distance, visited, path, cost = heapq.heappop(queue)
        expanded += 1
        for key in graph.get(u, []):
            edge = edges[key]
            if edge.v in visited:
                continue
            take = min(edge.length, outward_m-distance)
            n = max(1, int(np.ceil(take/2)))
            s = (np.arange(n)+.5)*take/n
            xy = edge.at(s)
            pos = distance+s
            pm1, t1 = fields.sample(xy, departure_s+pos/speed)
            pm2, t2 = fields.sample(xy, departure_s+(2*outward_m-pos)/speed)
            penalty = weight*(pm1+pm2)/pollution_scale + (1-weight)*(np.maximum(t1-30, 0)+np.maximum(t2-30, 0))/3
            new_cost = cost+float(penalty.mean()*take/speed)
            new_distance = distance+take
            new_path = path+(key,)
            if new_distance >= outward_m-1e-8:
                terminals.append((new_cost, new_path))
                continue
            bucket = (edge.v, int(new_distance/distance_bin_m))
            kept = labels.setdefault(bucket, [])
            if len(kept) >= labels_per_bin and new_cost >= max(kept):
                discarded += 1
                continue
            kept.append(new_cost)
            kept.sort()
            del kept[labels_per_bin:]
            # Project average cost to the full distance so a bounded search reaches
            # complete walks instead of spending its budget on short prefixes.
            # This heuristic is not an admissible bound; optimality is not claimed.
            priority = new_cost*outward_m/new_distance
            heapq.heappush(queue, (priority, next(counter), edge.v, new_distance,
                                  visited+(edge.v,), new_path, new_cost))
    unique = {}
    for cost, path in sorted(terminals):
        unique.setdefault(path, cost)
    paths = list(unique)[:max_candidates]
    return paths, {'expanded': expanded, 'pruned': discarded,
                   'terminal_paths': len(unique), 'shortlisted': len(paths),
                   'expansion_limit_reached': bool(queue), 'global_optimum_claimed': False}
