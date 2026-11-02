"""Tìm đường BFS trên lưới ô, tránh công trình (trừ cổng) và cây/đá."""
from collections import deque
import heapq

from settings import COLS, ROWS, TILE, TERRAIN
from utils import tile_center


def find_path(game, start, goal):
    """Danh sách tâm các ô (pixel) từ start tới goal (bỏ ô start), hoặc None nếu không có đường.

    Ô đích được phép bị chặn (ví dụ đích là mỏ đá hay cái cây): người đi tới sát ô đó.
    """
    if start == goal:
        return []
    prev, queue = {start: None}, deque([start])
    while queue:
        cur = queue.popleft()
        if cur == goal:
            break
        c, r = cur
        for nxt in ((c + 1, r), (c - 1, r), (c, r + 1), (c, r - 1)):
            if nxt in prev or not (0 <= nxt[0] < COLS and 0 <= nxt[1] < ROWS):
                continue
            b = game.buildings.get(nxt)
            # Địa hình chặn (núi/nước/lava) — cầu thì đi được
            terr = game.get_terrain(nxt[0], nxt[1]) if hasattr(game, "get_terrain") else "none"
            if nxt != goal and TERRAIN.get(terr, {}).get("block"):
                continue
            if nxt != goal and ((b and not b.info.get("gate") and not b.info.get("floor")) or nxt in game.nodes):
                continue   # cổng thì đi xuyên qua được
            prev[nxt] = cur
            queue.append(nxt)
    if goal not in prev:
        return None
    path, cur = [], goal
    while cur != start:
        path.append(tile_center(*cur))
        cur = prev[cur]
    path.reverse()
    return path


# ----- Đường đi của zombie: bản đồ chi phí (flow field) tính một lần từ lõi, cả bầy dùng chung -----

GATE_COST = 5.0          # cổng: rẻ -> zombie ưu tiên chọc vào cổng (cửa phễu của khu tiêu diệt)
DIRS8 = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def zombie_tile_cost(b):
    """Chi phí để zombie đi vào một ô: ô trống = 1, công trình = phải phá nên đắt (tường đá > tường gỗ)."""
    if b is None or b.info.get("floor"):
        return 1.0
    if b.info.get("gate"):
        return GATE_COST
    return 6.0 + max(0.0, b.hp) / 8.0


def zombie_field(game):
    """Dijkstra từ ô lõi ra ngoài. Trả về dict ô -> chi phí còn lại để tới lõi.
    Đường hở luôn rẻ hơn đường phải phá tường; có hở lối thì cả bầy kéo qua lối đó."""
    goal = (game.core.c, game.core.r)
    dist_map, heap = {goal: 0.0}, [(0.0, goal)]
    while heap:
        d, cur = heapq.heappop(heap)
        if d > dist_map.get(cur, 1e9):
            continue
        c, r = cur
        terr_cur = game.get_terrain(c, r) if hasattr(game, "get_terrain") else "none"
        if TERRAIN.get(terr_cur, {}).get("block") and cur != goal:
            enter = 80.0  # núi/nước/lava rất đắt
        else:
            enter = 1.0 if cur == goal else zombie_tile_cost(game.buildings.get(cur))
        for dc, dr in DIRS8:
            n = (c + dc, r + dr)
            if not (0 <= n[0] < COLS and 0 <= n[1] < ROWS):
                continue
            step = 1.0
            if dc and dr:   # đi chéo: không cắt góc qua công trình
                if game.buildings.get((c + dc, r)) or game.buildings.get((c, r + dr)):
                    continue
                step = 1.414
            nd = d + enter * step
            if nd < dist_map.get(n, 1e9):
                dist_map[n] = nd
                heapq.heappush(heap, (nd, n))
    return dist_map


def zombie_step(game, field, x, y):
    """Điểm (pixel) zombie ở (x, y) nên hướng tới: tâm ô láng giềng có chi phí thấp nhất."""
    c, r = int(x // TILE), int(y // TILE)
    if not (0 <= c < COLS and 0 <= r < ROWS):          # đang ở ngoài bản đồ: vào ô biên gần nhất
        return tile_center(min(max(c, 0), COLS - 1), min(max(r, 0), ROWS - 1))
    goal = (game.core.c, game.core.r)
    best, best_d = None, 1e9
    for dc, dr in DIRS8:
        n = (c + dc, r + dr)
        if n not in field:
            continue
        step = 1.0
        if dc and dr:
            if game.buildings.get((c + dc, r)) or game.buildings.get((c, r + dr)):
                continue
            step = 1.414
        enter = 1.0 if n == goal else zombie_tile_cost(game.buildings.get(n))
        d = field[n] + enter * step          # chi phí đi vào ô n rồi tiếp tục tới lõi
        if d < best_d:
            best, best_d = n, d
    return tile_center(*best) if best else (game.core.x, game.core.y)


def trace_route(game, field, x, y, limit=120):
    """Danh sách điểm đường đi dự kiến của một zombie xuất phát từ (x, y) (để vẽ xem trước)."""
    pts, cur = [(x, y)], (x, y)
    for _ in range(limit):
        nxt = zombie_step(game, field, *cur)
        pts.append(nxt)
        if (int(nxt[0] // TILE), int(nxt[1] // TILE)) == (game.core.c, game.core.r) or nxt == cur:
            break
        cur = nxt
    return pts
