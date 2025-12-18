# AStar.py
import heapq
from typing import Dict, List, Tuple

from calcDist import calcDist
from point import Point

def astar(adj: Dict[int, List[Tuple[int, float]]],
          nodes: Dict[int, Point],
          start: int,
          goal: int) -> Tuple[List[int], float]:
    """A* on adjacency list. Returns (path_node_list, total_cost_m)."""
    if start == goal:
        return [start], 0.0

    g_score = {start: 0.0}
    f_score = {start: calcDist(nodes[start].to_tuple(), nodes[goal].to_tuple())}

    open_heap = []
    heapq.heappush(open_heap, (f_score[start], 0.0, start, None))
    came_from = {}
    closed = set()

    while open_heap:
        f, g, current, parent = heapq.heappop(open_heap)

        # skip outdated heap entries
        if g > g_score.get(current, float('inf')) + 1e-9:
            continue

        if parent is not None:
            came_from[current] = parent

        if current == goal:
            # reconstruct
            path = [current]
            while path[-1] in came_from:
                path.append(came_from[path[-1]])
            path.reverse()
            return path, g_score.get(goal, 0.0)

        closed.add(current)

        for neighbor, weight in adj.get(current, []):
            if neighbor in closed:
                continue
            tentative_g = g_score.get(current, float('inf')) + weight
            if tentative_g < g_score.get(neighbor, float('inf')):
                g_score[neighbor] = tentative_g
                h = calcDist(nodes[neighbor].to_tuple(), nodes[goal].to_tuple())
                f_new = tentative_g + h
                heapq.heappush(open_heap, (f_new, tentative_g, neighbor, current))

    return [], float('inf')

def nearest_node_by_coord(nodes: Dict[int, Point], lat: float, lon: float) -> int:
    best = None
    best_d = float('inf')
    for nid, p in nodes.items():
        d = calcDist((lat, lon), (p.lat, p.lon))
        if d < best_d:
            best_d = d
            best = nid
    return best
