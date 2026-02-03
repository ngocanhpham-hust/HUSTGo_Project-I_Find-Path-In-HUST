import time, statistics

def time_astar(start_node, goal_node, repeats=30):
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        path, cost = astar(adj, nodes, start_node, goal_node)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    times.sort()
    return {
        "mean_ms": statistics.mean(times),
        "median_ms": statistics.median(times),
        "p95_ms": times[int(0.95 * len(times)) - 1],
        "min_ms": times[0],
        "max_ms": times[-1],
    }