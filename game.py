"""Trạng thái thế giới và vòng lặp ngày/đêm. Các đối tượng tự cập nhật trong thư mục entities/."""
import math
import random

import pygame

from settings import (W, H, TILE, COLS, ROWS, RESOURCES, DAY_LEN, MAX_REFUGEES,
                      REFUGEES_PER_DAY, ARRIVAL_LEAD, FOOD_PER_REFUGEE, STARVE_DMG,
                      SPAWN_RULES, BOSS_EVERY, BOSS_REWARD, MORALE_START, MORALE_DEATH,
                      MARKET_TRADES, RETRAIN_COST, GAME_SPEEDS,
                      SEASON_DAYS, SEASONS, SEASON_EFFECTS, RESEARCHES,
                      VIEW_W, VIEW_H, SAVE_FILE, BIOMES, MIDDLE_RATIO, NODE_BIOME,
                      TERRAIN, VOLCANO_ERUPT_INTERVAL, VOLCANO_ERUPT_DURATION,
                      VOLCANO_ERUPT_RADIUS, VOLCANO_ERUPT_DMG,
                      SEA_SIDES, SEA_NAMES, BIOME_EFFECTS, REGION_BOSSES, REGION_TRADE_OFFERS)
import json
import os
from utils import tile_center, dist
from pathfinding import zombie_field, trace_route
from hud import Hud
from entities.player import Player
from entities.building import Building
from entities.resource_node import ResourceNode
from entities.zombie import Zombie
from entities.animal import Animal
from entities.refugee import Refugee, NAMES
from entities.faction import Faction, FACTIONS, BLACK_MARKET_TRADES, REL_HOSTILE, REL_FRIENDLY, REL_ALLY
from entities.region_content import (
    REGION_MONSTERS, REGION_ANIMALS, REGION_PLANTS, REGION_TRIBES,
    SEA_MONSTERS, RegionMonster, RegionAnimal, RegionTribe, TribeUnit, SeaMonster,
    RegionBoss, RegionLeader
)


class Game:
    def __init__(self, screen):
        self.screen = screen
        self.hud = Hud(screen)
        self.night_overlay = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
        self.reset()

    # ----- khởi tạo -----
    def reset(self):
        self.res = {k: info["start"] for k, info in RESOURCES.items()}
        self.player = Player()
        self.buildings, self.nodes = {}, {}
        self.zombies, self.bullets, self.refugees, self.popups = [], [], [], []
        self.animals = []
        self.effects = []                 # vụ nổ...
        self.log = []                     # thông báo góc màn hình (text, màu, thời gian còn lại)
        self.morale = float(MORALE_START)
        self.hungry = 0                   # số người đói sáng nay (để tính tinh thần)
        self.field, self.field_age = None, 99.0   # bản đồ đường đi của zombie
        self.show_routes = False
        self.boss_due = False
        self.panel = None                 # bảng đang mở: "shop" / "trainer" / "market"
        self.sel_ref = None               # người tị nạn đang chọn trong bảng huấn luyện
        self.paused, self.speed, self.want_quit = False, 1, False
        self.day, self.phase, self.timer = 1, "day", DAY_LEN
        self.to_spawn, self.spawn_t = 0, 0.0
        self.region_spawn_queue, self.region_spawn_t = [], 0.0
        self.season_idx = 0
        self.season = SEASONS[0]
        self.researched = set()
        self.plan_arrivals()
        self.over = False
        self.generate_biomes()
        self.generate_terrain()
        self.invalidate_terrain_cache()
        cc, cr = COLS // 2, ROWS // 2
        # Dọn địa hình quanh lõi
        for dr in range(-5, 6):
            for dc in range(-5, 6):
                nc, nr = cc + dc, cr + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if self.terrain_map[nr][nc] in ("mountain", "river", "lake", "pond", "sea", "lava"):
                        self.terrain_map[nr][nc] = "road" if abs(dc) + abs(dr) <= 2 else "none"
        self.core = Building("core", cc, cr)
        self.buildings[(cc, cr)] = self.core
        self.respawn_t = {k: rule["interval"] for k, rule in SPAWN_RULES.items()}
        for key, rule in SPAWN_RULES.items():          # bản đồ khởi đầu đầy giới hạn
            for _ in range(rule["limit"]):
                self.spawn_entity(key, rule)
        self._clear_blocked_tiles()
        self.cam = (0, 0)
        self.particles = []   # tuyết / lá rơi
        self.last_biome = "middle"
        # ----- 3 phe AI -----
        self.factions = {}
        self.faction_units = []
        self.player_relation = {fid: 0 for fid in FACTIONS}   # -100..100
        self.faction_relations = {          # giữa các phe
            ("gov", "rebel"): -60,
            ("rebel", "gov"): -60,
            ("gov", "nomad"): 20,
            ("nomad", "gov"): 25,
            ("rebel", "nomad"): 15,
            ("nomad", "rebel"): 20,
        }
        self.black_market_open = True
        self.war_timer = 45.0               # đếm ngược tới đợt xung đột tiếp
        self.alignment = None               # None | "gov" | "rebel" | "nomad"
        for fid in FACTIONS:
            f = Faction(fid)
            self.factions[fid] = f
            f.build_base(self)
            f.spawn_initial_units(self)
        # Nội dung vùng: tộc, động vật, thực vật, quái, thủy quái, boss
        self.region_monsters = []
        self.region_animals = []
        self.sea_monsters = []
        self.region_bosses = []
        self.region_leaders = {}  # region_id -> RegionLeader
        self.diplomacy_region = None  # đang mở panel đàm phán với vùng nào
        self.vehicles = []
        self.tribe_units = []
        self.tribes = {}
        self.player_poison = 0.0
        self.player_poison_dps = 0.0
        self.biome_effect_label = ""
        self.setup_region_content()
        self.say("Click thanh Xây để chọn công trình. F: cưỡi ngựa / lên xe.", 6)
        self.say("Nhà máy: xe máy, ô tô, bọc thép, tăng, trực thăng, máy bay. Ga tàu vận chuyển hàng.", 5)
        self.say("Lãnh đạo vùng (E): đàm phán. Quái & thú hung dữ có thể giết bạn!", 5)


    def generate_biomes(self):
        """Tạo bản đồ biome: Trung địa ở giữa, 6 vùng xung quanh theo góc.
        Bắc=arctic, Đông=wizard, Đông-Nam=tropical, Nam=volcano,
        Tây-Nam=rainforest, Tây=spirit."""
        self.biome_map = [["middle"] * COLS for _ in range(ROWS)]
        cx, cy = (COLS - 1) / 2.0, (ROWS - 1) / 2.0
        rx = COLS * MIDDLE_RATIO * 0.5
        ry = ROWS * MIDDLE_RATIO * 0.5
        for r in range(ROWS):
            for c in range(COLS):
                noise = (hash((c * 17 + r * 31)) % 1000) / 1000.0 * 0.16 - 0.08
                dx = (c - cx) / max(rx, 1)
                dy = (r - cy) / max(ry, 1)
                d = (dx * dx + dy * dy) ** 0.5 + noise
                if d <= 1.0:
                    self.biome_map[r][c] = "middle"
                    continue
                ang = math.atan2(r - cy, c - cx)  # -pi .. pi
                # 6 cung ~60° mỗi vùng
                # -pi..-2pi/3: spirit (Tây-Bắc)
                # -2pi/3..-pi/3: arctic (Bắc)
                # -pi/3..0: wizard (Đông-Bắc)
                # 0..pi/3: tropical (Đông-Nam)
                # pi/3..2pi/3: volcano (Nam)
                # 2pi/3..pi: rainforest (Tây-Nam)
                if -math.pi <= ang < -math.pi * 2 / 3:
                    self.biome_map[r][c] = "spirit"
                elif -math.pi * 2 / 3 <= ang < -math.pi / 3:
                    self.biome_map[r][c] = "arctic"
                elif -math.pi / 3 <= ang < 0:
                    self.biome_map[r][c] = "wizard"
                elif 0 <= ang < math.pi / 3:
                    self.biome_map[r][c] = "tropical"
                elif math.pi / 3 <= ang < math.pi * 2 / 3:
                    self.biome_map[r][c] = "volcano"
                else:
                    self.biome_map[r][c] = "rainforest"
        sums = {k: [0, 0, 0] for k in BIOMES}
        for r in range(ROWS):
            for c in range(COLS):
                b = self.biome_map[r][c]
                sums[b][0] += c
                sums[b][1] += r
                sums[b][2] += 1
        self.biome_centers = {}
        for k, (sc, sr, n) in sums.items():
            if n:
                self.biome_centers[k] = (sc / n * TILE + TILE / 2, sr / n * TILE + TILE / 2)

    def get_biome(self, c, r):
        """Trả về id biome của ô (c, r). Ngoài map coi như middle."""
        if 0 <= c < COLS and 0 <= r < ROWS:
            return self.biome_map[r][c]
        return "middle"

    def biome_at_world(self, x, y):
        c, r = int(x // TILE), int(y // TILE)
        return self.get_biome(c, r)

    def get_terrain(self, c, r):
        if 0 <= c < COLS and 0 <= r < ROWS:
            return self.terrain_map[r][c]
        return "none"

    def terrain_at_world(self, x, y):
        return self.get_terrain(int(x // TILE), int(y // TILE))

    def generate_terrain(self):
        """Sinh núi, biển, sông, hồ, ao, đường, cầu, miệng núi lửa."""
        import math
        self.terrain_map = [["none"] * COLS for _ in range(ROWS)]
        self.volcano_peaks = []   # list (c, r)
        self.erupt_t = random.uniform(*VOLCANO_ERUPT_INTERVAL)
        self.erupting = False
        self.erupt_left = 0.0

        self._gen_sea()
        self._gen_ports()
        self._gen_mountains()
        self._gen_lakes_ponds()
        self._gen_rivers()
        self._gen_volcano_peaks()
        self._gen_roads_and_bridges()
        # Xóa node/động vật trên ô bị block
        self._clear_blocked_tiles()

    def _gen_sea(self):
        """Bốn vùng biển Đông/Tây/Nam/Bắc, phân cách bằng giải đất red_line (không đi xuyên)."""
        self.ports = []
        self.naval_bases = []  # (c, r, side)
        self.sea_side_map = [[None] * COLS for _ in range(ROWS)]  # ô biển thuộc hướng nào
        # Độ dày biển mỗi phía (có nhiễu)
        def thick(seed, base=3):
            return base + (1 if (hash(seed) % 100) < 45 else 0)

        # Vùng góc không có biển (giải đất ngăn 4 biển)
        corner = 10  # độ rộng giải đất ở 4 góc

        for r in range(ROWS):
            for c in range(COLS):
                # --- Biển Bắc ---
                n_th = thick((c, r, 11), 3)
                if r < n_th and corner <= c < COLS - corner:
                    self.terrain_map[r][c] = "sea"
                    self.sea_side_map[r][c] = "north"
                    continue
                # --- Biển Nam ---
                s_th = thick((c, r, 13), 3)
                if r >= ROWS - s_th and corner <= c < COLS - corner:
                    self.terrain_map[r][c] = "sea"
                    self.sea_side_map[r][c] = "south"
                    continue
                # --- Biển Tây ---
                w_th = thick((c, r, 3), 3)
                if c < w_th and corner <= r < ROWS - corner:
                    self.terrain_map[r][c] = "sea"
                    self.sea_side_map[r][c] = "west"
                    continue
                # --- Biển Đông ---
                e_th = thick((c, r, 5), 3)
                if c >= COLS - e_th and corner <= r < ROWS - corner:
                    self.terrain_map[r][c] = "sea"
                    self.sea_side_map[r][c] = "east"
                    continue

        # Red lines: giải đất ngăn cách 4 vùng biển tại 4 góc + dải dọc/ngang mỏng
        # Dải ngăn Bắc-Tây, Bắc-Đông, Nam-Tây, Nam-Đông
        for r in range(ROWS):
            for c in range(COLS):
                # Góc Tây-Bắc
                if c < corner and r < corner:
                    if self.terrain_map[r][c] == "none":
                        # Vạch đỏ ở biên trong của góc
                        if c == corner - 1 or r == corner - 1:
                            self.terrain_map[r][c] = "red_line"
                # Góc Đông-Bắc
                if c >= COLS - corner and r < corner:
                    if self.terrain_map[r][c] == "none":
                        if c == COLS - corner or r == corner - 1:
                            self.terrain_map[r][c] = "red_line"
                # Góc Tây-Nam
                if c < corner and r >= ROWS - corner:
                    if self.terrain_map[r][c] == "none":
                        if c == corner - 1 or r == ROWS - corner:
                            self.terrain_map[r][c] = "red_line"
                # Góc Đông-Nam
                if c >= COLS - corner and r >= ROWS - corner:
                    if self.terrain_map[r][c] == "none":
                        if c == COLS - corner or r == ROWS - corner:
                            self.terrain_map[r][c] = "red_line"

    def _gen_ports(self):
        """Mỗi vùng biển 1 căn cứ hải quân (port lớn) + 1 cảng phụ."""
        candidates = {s: [] for s in SEA_SIDES}
        for r in range(2, ROWS - 2):
            for c in range(2, COLS - 2):
                if self.terrain_map[r][c] not in ("none",):
                    continue
                if self.terrain_map[r][c] == "red_line":
                    continue
                near_side = None
                for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nc, nr = c + dc, r + dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS and self.terrain_map[nr][nc] == "sea":
                        near_side = self.sea_side_map[nr][nc]
                        break
                if near_side:
                    candidates[near_side].append((c, r))

        self.ports = []
        self.naval_bases = []
        for side in SEA_SIDES:
            cands = candidates[side]
            if not cands:
                continue
            # Sắp theo trục chính của hướng
            if side in ("north", "south"):
                cands.sort(key=lambda p: p[0])
            else:
                cands.sort(key=lambda p: p[1])
            # Căn cứ hải quân (giữa) + 1 cảng phụ
            mid = cands[len(cands) // 2]
            aux = cands[len(cands) // 4] if len(cands) >= 4 else None
            for idx, (c, r) in enumerate([mid] + ([aux] if aux else [])):
                size = 3 if idx == 0 else 2  # căn cứ lớn hơn
                for dr in range(0, size):
                    for dc in range(0, size):
                        nc, nr = c + dc, r + dr
                        if 0 <= nc < COLS and 0 <= nr < ROWS and self.terrain_map[nr][nc] in ("none", "sea"):
                            self.terrain_map[nr][nc] = "port"
                self.ports.append((c, r, side))
                if idx == 0:
                    self.naval_bases.append((c, r, side))

    def _gen_mountains(self):
        """Cụm núi: nhiều ở Bắc cực & rìa, một ít ở Trung địa."""
        clusters = []
        # Bắc cực
        for _ in range(5):
            clusters.append((random.randrange(8, COLS - 8), random.randrange(2, max(8, ROWS // 4)), random.randint(3, 6)))
        # Núi lửa biome (nam)
        for _ in range(4):
            clusters.append((random.randrange(8, COLS - 8), random.randrange(ROWS * 2 // 3, ROWS - 4), random.randint(2, 5)))
        # Rải rác
        for _ in range(6):
            clusters.append((random.randrange(5, COLS - 5), random.randrange(5, ROWS - 5), random.randint(2, 4)))
        for cx, cy, rad in clusters:
            for r in range(max(0, cy - rad), min(ROWS, cy + rad + 1)):
                for c in range(max(0, cx - rad), min(COLS, cx + rad + 1)):
                    if (c - cx) ** 2 + (r - cy) ** 2 <= rad * rad + random.uniform(-1, 1):
                        if self.terrain_map[r][c] == "none":
                            # Không chắn core player
                            if abs(c - COLS // 2) + abs(r - ROWS // 2) > 6:
                                self.terrain_map[r][c] = "mountain"

    def _gen_lakes_ponds(self):
        """Hồ lớn + ao nhỏ."""
        # Hồ
        for _ in range(4):
            cx = random.randrange(10, COLS - 10)
            cy = random.randrange(10, ROWS - 10)
            rad = random.randint(3, 5)
            if abs(cx - COLS // 2) + abs(cy - ROWS // 2) < 12:
                continue
            for r in range(max(0, cy - rad), min(ROWS, cy + rad + 1)):
                for c in range(max(0, cx - rad), min(COLS, cx + rad + 1)):
                    if (c - cx) ** 2 + (r - cy) ** 2 <= rad * rad * 0.9:
                        if self.terrain_map[r][c] == "none":
                            self.terrain_map[r][c] = "lake"
        # Ao
        for _ in range(8):
            cx = random.randrange(5, COLS - 5)
            cy = random.randrange(5, ROWS - 5)
            rad = random.randint(1, 2)
            if abs(cx - COLS // 2) + abs(cy - ROWS // 2) < 8:
                continue
            for r in range(max(0, cy - rad), min(ROWS, cy + rad + 1)):
                for c in range(max(0, cx - rad), min(COLS, cx + rad + 1)):
                    if (c - cx) ** 2 + (r - cy) ** 2 <= rad * rad:
                        if self.terrain_map[r][c] == "none":
                            self.terrain_map[r][c] = "pond"

    def _gen_rivers(self):
        """Vài con sông từ núi/biên chảy xuống biển/hồ."""
        for _ in range(3):
            # Điểm bắt đầu: núi hoặc rìa bắc
            starts = [(c, r) for r in range(ROWS) for c in range(COLS)
                      if self.terrain_map[r][c] == "mountain"]
            if not starts:
                c, r = random.randrange(COLS), random.randrange(ROWS // 3)
            else:
                c, r = random.choice(starts)
            length = random.randint(25, 55)
            dir_prefer = random.choice([(0, 1), (1, 1), (-1, 1), (1, 0), (-1, 0)])
            for step in range(length):
                if not (0 <= c < COLS and 0 <= r < ROWS):
                    break
                t = self.terrain_map[r][c]
                if t in ("sea", "lake"):
                    break
                if t not in ("mountain", "road", "bridge"):
                    self.terrain_map[r][c] = "river"
                # Meander
                if random.random() < 0.35:
                    dc, dr = random.choice([(0, 1), (1, 0), (-1, 0), (0, 1), (1, 1), (-1, 1)])
                else:
                    dc, dr = dir_prefer
                c, r = c + dc, r + dr

    def _gen_volcano_peaks(self):
        """Miệng núi lửa trong biome volcano + vài ô lava quanh đó."""
        candidates = [(c, r) for r in range(ROWS) for c in range(COLS)
                      if self.get_biome(c, r) == "volcano" and self.terrain_map[r][c] in ("none", "mountain")]
        random.shuffle(candidates)
        for c, r in candidates[:3]:
            self.volcano_peaks.append((c, r))
            self.terrain_map[r][c] = "lava"
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    nc, nr = c + dc, r + dr
                    if 0 <= nc < COLS and 0 <= nr < ROWS and self.terrain_map[nr][nc] == "none":
                        if random.random() < 0.6:
                            self.terrain_map[nr][nc] = "lava"

    def _gen_roads_and_bridges(self):
        """Đường nối core player với 3 căn cứ phe; cầu khi cắt sông/hồ."""
        centers = [(COLS // 2, ROWS // 2)]
        # Căn cứ phe (tọa độ ô gần đúng — scale theo map lớn)
        for fid, base in (("gov", (22, 22)), ("rebel", (COLS - 23, ROWS - 23)), ("nomad", (COLS - 23, 22))):
            centers.append(base)
        core = centers[0]
        for target in centers[1:]:
            self._carve_road(core[0], core[1], target[0], target[1])
        self._carve_road(22, 22, COLS - 23, 22)
        self._carve_road(COLS - 23, 22, COLS - 23, ROWS - 23)
        # Đường sắt nối các hướng (ray + ga)
        self._gen_rails()

    def _gen_rails(self):
        """Sinh đường ray và vài ga sơ bộ nối Trung địa với rìa."""
        core = (COLS // 2, ROWS // 2)
        ends = [
            (COLS // 2, 8),
            (COLS - 10, ROWS // 2),
            (COLS // 2, ROWS - 9),
            (10, ROWS // 2),
        ]
        for ec, er in ends:
            self._carve_rail(core[0], core[1], ec, er)
            # Đặt ga nếu ô trống
            if 0 <= ec < COLS and 0 <= er < ROWS:
                if self.terrain_map[er][ec] in ("none", "road", "rail"):
                    self.terrain_map[er][ec] = "rail"
                # Ga như building sẽ do player xây; đánh dấu terrain rail

    def _carve_rail(self, c0, r0, c1, r1):
        c, r = c0, r0
        for _ in range(COLS + ROWS + 10):
            if not (0 <= c < COLS and 0 <= r < ROWS):
                break
            t = self.terrain_map[r][c]
            if t in ("none", "road"):
                self.terrain_map[r][c] = "rail"
            elif t in ("river", "lake", "pond"):
                self.terrain_map[r][c] = "bridge"
            if c == c1 and r == r1:
                break
            if abs(c1 - c) > abs(r1 - r):
                c += 1 if c1 > c else -1
            else:
                r += 1 if r1 > r else -1

    def _carve_road(self, c0, r0, c1, r1):
        """Bresenham-ish đường: núi -> đường hầm, nước/hồ -> cầu, còn lại -> đường."""
        c, r = c0, r0
        for _ in range(COLS + ROWS + 20):
            if not (0 <= c < COLS and 0 <= r < ROWS):
                break
            t = self.terrain_map[r][c]
            if t in ("river", "lake", "pond", "sea"):
                self.terrain_map[r][c] = "bridge"
            elif t == "mountain":
                self.terrain_map[r][c] = "tunnel"
            elif t == "red_line":
                pass  # không đục xuyên red line
            elif t not in ("lava", "port"):
                self.terrain_map[r][c] = "road"
            if c == c1 and r == r1:
                break
            if abs(c1 - c) > abs(r1 - r):
                c += 1 if c1 > c else -1
            else:
                r += 1 if r1 > r else -1
            # Nhiễu nhẹ
            if random.random() < 0.08:
                if abs(c1 - c) > abs(r1 - r):
                    r += random.choice([-1, 0, 1])
                else:
                    c += random.choice([-1, 0, 1])

    def _clear_blocked_tiles(self):
        """Gỡ node trên ô núi/nước/lava/đường/cầu/cảng/hầm (giữa đường không mọc cây/tài nguyên)."""
        no_grow = ("road", "bridge", "port", "tunnel", "red_line")
        for pos in list(self.nodes.keys()):
            c, r = pos
            t = self.get_terrain(c, r)
            if TERRAIN.get(t, {}).get("block") or t in no_grow:
                del self.nodes[pos]

    # ----- quan hệ phe -----

    def setup_region_content(self):
        """Sinh tộc người, động vật, thực vật đặc trưng từng vùng."""
        # Tộc: đặt base gần tâm vùng
        for region, info in REGION_TRIBES.items():
            cx, cy = self.biome_centers.get(region, (W / 2, H / 2))
            bc, br = int(cx // TILE), int(cy // TILE)
            # tìm ô trống gần tâm
            found = None
            for rad in range(0, 12):
                for dc in range(-rad, rad + 1):
                    for dr in range(-rad, rad + 1):
                        c, r = bc + dc, br + dr
                        if not (0 <= c < COLS and 0 <= r < ROWS):
                            continue
                        if self.get_biome(c, r) != region:
                            continue
                        if TERRAIN.get(self.get_terrain(c, r), {}).get("block"):
                            continue
                        if (c, r) in self.buildings:
                            continue
                        found = (c, r)
                        break
                    if found:
                        break
                if found:
                    break
            if found:
                tribe = RegionTribe(region, found[0], found[1])
                tribe.setup(self)
                self.tribes[region] = tribe
        # Động vật vùng
        for region, animals in REGION_ANIMALS.items():
            for kind, ad in animals.items():
                for _ in range(4):
                    self.spawn_region_animal(region, kind)
        # Thực vật đặc trưng (node)
        for region, plants in REGION_PLANTS.items():
            for plant_id, pd in plants.items():
                for _ in range(8):
                    self.spawn_region_plant(region, plant_id, pd)
        # Quái ban ngày ít
        for region in REGION_MONSTERS:
            for _ in range(2):
                self.spawn_region_monster(region)
        # Thủy quái mỗi vùng biển
        for side in SEA_SIDES:
            for _ in range(2):
                self.spawn_sea_monster(side)
        # Boss mỗi vùng (1 con, gần tâm vùng)
        for region in REGION_BOSSES:
            self.spawn_region_boss(region)
        # Lãnh đạo mỗi vùng (tại căn cứ tộc hoặc tâm vùng)
        for region in REGION_TRIBES:
            if region in self.tribes:
                t = self.tribes[region]
                lx, ly = t.base_x + 20, t.base_y + 10
            else:
                cx, cy = self.biome_centers.get(region, (W / 2, H / 2))
                lx, ly = cx, cy
            self.region_leaders[region] = RegionLeader(region, lx, ly)

    def spawn_region_animal(self, region, kind):
        for _ in range(30):
            c, r = random.randrange(COLS), random.randrange(ROWS)
            if self.get_biome(c, r) != region:
                continue
            if TERRAIN.get(self.get_terrain(c, r), {}).get("block"):
                continue
            x, y = tile_center(c, r)
            if self.blocked(x, y, 12):
                continue
            self.region_animals.append(RegionAnimal(region, kind, x, y))
            return True
        return False

    def spawn_region_plant(self, region, plant_id, pd):
        """Đặt node tài nguyên vùng với màu riêng. Không mọc trên đường/cầu/cảng."""
        from entities.resource_node import ResourceNode
        res = pd["resource"]
        no_grow = ("road", "bridge", "port", "tunnel", "red_line")
        for _ in range(40):
            c, r = random.randrange(COLS), random.randrange(ROWS)
            if self.get_biome(c, r) != region:
                continue
            t = self.get_terrain(c, r)
            if TERRAIN.get(t, {}).get("block") or t in no_grow:
                continue
            if (c, r) in self.nodes or (c, r) in self.buildings:
                continue
            n = ResourceNode(res, c, r, amount=pd.get("amount", 4))
            n.plant_name = pd["name"]
            n.plant_color = pd["node_color"]
            self.nodes[(c, r)] = n
            return True
        return False

    def spawn_region_monster(self, region, kind=None):
        kinds = list(REGION_MONSTERS[region].keys())
        kind = kind or random.choice(kinds)
        for _ in range(30):
            c, r = random.randrange(COLS), random.randrange(ROWS)
            if self.get_biome(c, r) != region:
                continue
            if TERRAIN.get(self.get_terrain(c, r), {}).get("block"):
                continue
            x, y = tile_center(c, r)
            self.region_monsters.append(RegionMonster(region, kind, x, y, self.day))
            return True
        return False

    def spawn_sea_monster(self, side, kind=None):
        """Sinh thủy quái trên ô biển của hướng tương ứng."""
        kinds = list(SEA_MONSTERS.get(side, {}).keys())
        if not kinds:
            return False
        kind = kind or random.choice(kinds)
        sea_tiles = [(c, r) for r in range(ROWS) for c in range(COLS)
                     if self.terrain_map[r][c] == "sea" and getattr(self, "sea_side_map", [[None]])[r][c] == side]
        if not sea_tiles:
            return False
        random.shuffle(sea_tiles)
        for c, r in sea_tiles[:40]:
            x, y = tile_center(c, r)
            self.sea_monsters.append(SeaMonster(side, kind, x, y, self.day))
            return True
        return False

    def spawn_region_boss(self, region):
        """Spawn 1 boss gần tâm vùng."""
        cx, cy = self.biome_centers.get(region, (W / 2, H / 2))
        bc, br = int(cx // TILE), int(cy // TILE)
        for rad in range(2, 16):
            for dc in range(-rad, rad + 1):
                for dr in range(-rad, rad + 1):
                    if abs(dc) != rad and abs(dr) != rad:
                        continue
                    c, r = bc + dc, br + dr
                    if not (0 <= c < COLS and 0 <= r < ROWS):
                        continue
                    if self.get_biome(c, r) != region:
                        continue
                    if TERRAIN.get(self.get_terrain(c, r), {}).get("block"):
                        continue
                    if abs(c - COLS // 2) + abs(r - ROWS // 2) < 12:
                        continue
                    x, y = tile_center(c, r)
                    self.region_bosses.append(RegionBoss(region, x, y, self.day))
                    return True
        # fallback
        x, y = cx + random.uniform(-80, 80), cy + random.uniform(-80, 80)
        self.region_bosses.append(RegionBoss(region, x, y, self.day))
        return True

    def get_relation(self, a, b):
        if a == b:
            return 100
        return self.faction_relations.get((a, b), self.faction_relations.get((b, a), 0))

    def change_relation(self, a, b, delta):
        key = (a, b)
        if key not in self.faction_relations:
            key = (b, a)
        cur = self.faction_relations.get(key, 0)
        self.faction_relations[key] = max(-100, min(100, cur + delta))
        # mirror
        self.faction_relations[(b, a)] = self.faction_relations[key]

    def change_player_relation(self, fid, delta):
        self.player_relation[fid] = max(-100, min(100, self.player_relation.get(fid, 0) + delta))

    def nearest_faction_base(self, x, y, max_dist=140):
        best, best_d = None, max_dist
        for fid, f in self.factions.items():
            d = dist(x, y, f.base_x, f.base_y)
            if d < best_d:
                best, best_d = fid, d
        return best


    def declare_allegiance(self, fid):
        """Người chơi ngả theo 1 phe (hoặc trung lập nếu fid=None)."""
        if fid is not None and fid not in FACTIONS:
            return
        old = self.alignment
        self.alignment = fid
        if fid is None:
            self.say("Bạn chọn đứng trung lập.", 3)
            return
        # Tăng quan hệ phe được chọn, giảm phe còn lại
        for other in FACTIONS:
            if other == fid:
                self.change_player_relation(other, 35)
            else:
                self.change_player_relation(other, -20)
        self.say(f"Bạn đã ngả theo {FACTIONS[fid]['name']}! Quan hệ thay đổi.", 4, "good")
        # Phe còn lại có thể thù hơn
        if fid in ("gov", "rebel"):
            enemy = "rebel" if fid == "gov" else "gov"
            self.change_relation(fid, enemy, -10)

    def open_black_market(self):
        """Mở bảng chợ đen nếu đứng gần căn cứ Du mục và quan hệ không quá xấu."""
        rel = self.player_relation.get("nomad", 0)
        if rel <= REL_HOSTILE:
            self.say("Du mục từ chối giao dịch - quan hệ quá xấu!", 3, "warn")
            return
        if not self.black_market_open:
            self.say("Chợ đen đang hỗn loạn / tạm đóng!", 3, "warn")
            return
        self.panel = "black_market"

    def black_market_trade(self, idx):
        if idx < 0 or idx >= len(BLACK_MARKET_TRADES):
            return
        give_k, give_n, take_k, take_n = BLACK_MARKET_TRADES[idx]
        if self.res.get(give_k, 0) < give_n:
            self.say("Không đủ tài nguyên để giao dịch!", 2, "warn")
            return
        if self.is_full(take_k):
            self.say("Kho nhận đã đầy!", 2, "warn")
            return
        self.res[give_k] -= give_n
        self.add_res(take_k, take_n)
        self.change_player_relation("nomad", 2)
        self.say(f"Chợ đen: đổi {give_n} {RESOURCES[give_k]['name']} → {take_n} {RESOURCES[take_k]['name']}", 2, "good")

    # ----- tiện ích cho các đối tượng -----
    LOG_COLORS = {"info": (235, 235, 215), "warn": (255, 130, 110), "good": (150, 235, 150)}

    def say(self, text, t=3.0, kind="info"):
        """Ghi một dòng vào nhật ký góc màn hình. Cùng nội dung thì chỉ làm mới thời gian (khỏi spam)."""
        life = max(t, 2.5) + 2.0
        for e in self.log:
            if e["text"] == text:
                e["life"] = life
                return
        self.log.append(dict(text=text, color=self.LOG_COLORS[kind], life=life, max=life))
        del self.log[:-7]

    def popup(self, text, x, y, color):
        self.popups.append(dict(text=text, x=x, y=y, color=color, life=1.0))

    # ----- kho chứa -----
    def cap(self, kind):
        """Sức chứa tài nguyên `kind` = mức cơ bản + các kho tương ứng đã xây."""
        extra = sum(b.info["store_amount"] for b in self.buildings.values()
                    if b.info.get("store") == kind)
        return RESOURCES[kind]["cap"] + extra

    def is_full(self, kind):
        return self.res[kind] >= self.cap(kind)

    def add_res(self, kind, n=1):
        """Cộng tài nguyên nhưng không vượt sức chứa. Trả về số thực sự nhận được."""
        got = max(0, min(n, self.cap(kind) - self.res[kind]))
        self.res[kind] += got
        return got

    def can_afford(self, cost):
        return all(self.res[k] >= v for k, v in cost.items())

    def blocked(self, x, y, r, pass_gates=False):
        """Tâm (x, y) bán kính r có đụng công trình, tài nguyên, địa hình block hay ra ngoài bản đồ?
        pass_gates=True (người chơi, người tị nạn): đi xuyên qua cổng được."""
        for ox, oy in ((-r, -r), (r, -r), (-r, r), (r, r)):
            t = (int((x + ox) // TILE), int((y + oy) // TILE))
            # Địa hình chặn (núi, nước, lava) — cầu/đường thì không
            tc, tr = t
            terr = self.get_terrain(tc, tr)
            if TERRAIN.get(terr, {}).get("block"):
                return True
            b = self.buildings.get(t)
            if b and not b.info.get("floor") and not (pass_gates and b.info.get("gate")):
                return True
            if t in self.nodes:
                return True
        return not (r < x < W - r and r < y < H - r)

    def terrain_speed_mult(self, x, y):
        """Hệ số tốc độ theo địa hình (đường nhanh hơn) × hệ số biome."""
        t = self.terrain_at_world(x, y)
        base = TERRAIN.get(t, TERRAIN["none"]).get("slow", 1.0)
        bid = self.biome_at_world(x, y)
        bfx = BIOME_EFFECTS.get(bid, {}).get("speed_mult", 1.0)
        return base * bfx

    def apply_biome_effects(self, dt):
        """Sát thương môi trường, độc, nhãn hiệu ứng theo biome hiện tại."""
        bid = self.biome_at_world(self.player.x, self.player.y)
        fx = BIOME_EFFECTS.get(bid, BIOME_EFFECTS["middle"])
        self.biome_effect_label = fx.get("label", "")
        dps = fx.get("dmg_per_sec", 0)
        if dps > 0 and self.player.hp > 0:
            # Giảm một chút nếu đã research armor
            reduce = self.player_armor_reduction() * 0.5
            self.player.hp -= dps * (1.0 - reduce) * dt
            if self.player.hp < 0:
                self.player.hp = 0
        # Độc từ boss rainforest
        if self.player_poison > 0:
            self.player_poison -= dt
            self.player.hp -= getattr(self, "player_poison_dps", 3) * dt
            if self.player.hp < 0:
                self.player.hp = 0
            if self.player_poison <= 0:
                self.player_poison = 0

    def unit_in_tile(self, c, r):
        tx, ty = tile_center(c, r)
        return any(abs(u.x - tx) < TILE and abs(u.y - ty) < TILE
                   for u in self.zombies + self.refugees + self.animals)

    def housing_capacity(self):
        return sum(b.info.get("capacity", 0) for b in self.buildings.values())

    def free_house(self):
        """Nhà còn chỗ trống đầu tiên, hoặc None."""
        for b in self.buildings.values():
            cap = b.info.get("capacity", 0)
            if cap and sum(1 for r in self.refugees if r.home is b) < cap:
                return b
        return None

    # ----- tinh thần dân cư -----
    def morale_mult(self):
        """Hệ số làm việc theo tinh thần: vui làm nhanh, chán làm chậm."""
        m = self.morale
        return 1.2 if m >= 75 else 1.0 if m >= 40 else 0.8 if m >= 20 else 0.65

    def morale_label(self):
        m = self.morale
        return ("Hăng hái", (140, 235, 140)) if m >= 75 else ("Ổn định", (225, 225, 140)) if m >= 40 \
            else ("Chán nản", (255, 170, 100)) if m >= 20 else ("Sắp bỏ đi", (255, 100, 90))

    def change_morale(self, d):
        self.morale = max(0.0, min(100.0, self.morale + d))

    def dawn_morale(self):
        """Mỗi sáng: tính lại tinh thần theo ăn uống, chỗ ở, độ vững của căn cứ. Dân quá chán thì bỏ đi."""
        n = len(self.refugees)
        if n == 0:
            return
        delta, notes = 0, []
        if self.hungry:
            delta -= 8 + 4 * self.hungry
            notes.append("đói")
        else:
            delta += 6
            if self.res["food"] >= 3 * n:
                delta += 2
                notes.append("ăn no")
        homeless = sum(1 for r in self.refugees if r.home is None)
        if homeless:
            delta -= 6 * homeless
            notes.append("mất nhà")
        else:
            delta += 3
        kinds = [b.kind for b in self.buildings.values()]
        walls = kinds.count("wall") + kinds.count("stone_wall")
        turrets = sum(1 for b in self.buildings.values() if b.info.get("behavior") == "turret")
        sec = (3 if walls >= 12 else 0) + (2 if walls >= 30 else 0) + (2 if "gate" in kinds else 0) \
            + (2 if turrets >= 3 else 0)
        if sec:
            delta += sec
            notes.append("tường/cổng vững")
        delta += 3 if self.core.hp >= self.core.max * 0.5 else -3
        self.change_morale(delta)
        self.say(f"Tinh thần dân cư {delta:+d} ({', '.join(notes) or 'bình thường'}) -> {int(self.morale)}/100",
                 4, "good" if delta >= 0 else "warn")
        if self.morale < 25:
            leaving = [r for r in self.refugees if not r.elite]
            for r in random.sample(leaving, min(len(leaving), 2 if self.morale < 10 else 1)):
                r.left = True
                if r.job is not None and r.job.worker is r:
                    r.job.worker = None

    # ----- bảng giao dịch (xưởng vũ khí / nhà huấn luyện / chợ) -----
    def near_interactive(self, kind=None, rng=110):
        """Công trình tương tác gần người chơi nhất (lọc theo loại nếu có)."""
        best, best_d = None, rng
        for b in self.buildings.values():
            it = b.info.get("interact")
            if it and (kind is None or it == kind):
                d = dist(b.x, b.y, self.player.x, self.player.y)
                if d <= best_d:
                    best, best_d = b, d
        return best

    def interact(self):
        """Phím E: mở bảng công trình gần, lãnh đạo vùng, hoặc chợ đen."""
        if self.panel:
            self.panel = None
            self.diplomacy_region = None
            return
        # Lãnh đạo vùng gần
        leader = self.near_leader(120)
        if leader:
            self.open_diplomacy(leader.region)
            return
        # Ưu tiên chợ đen nếu đứng gần căn cứ Du mục
        nomad = self.factions.get("nomad")
        if nomad and dist(self.player.x, self.player.y, nomad.base_x, nomad.base_y) < 130:
            self.open_black_market()
            return
        b = self.near_interactive()
        if b:
            self.panel = b.info["interact"]
            self.sel_ref = None
        else:
            self.say("Lại gần Lãnh đạo vùng / Xưởng / Huấn luyện / Chợ / Du mục rồi bấm E.", 2)

    def near_leader(self, rng=120):
        best, best_d = None, rng
        for leader in self.region_leaders.values():
            if not leader.alive:
                continue
            d = dist(self.player.x, self.player.y, leader.x, leader.y)
            if d < best_d:
                best, best_d = leader, d
        return best

    def open_diplomacy(self, region):
        if region not in self.region_leaders:
            return
        self.panel = "diplomacy"
        self.diplomacy_region = region
        leader = self.region_leaders[region]
        self.say(f"Đàm phán với {leader.name} — {BIOMES[region]['name']}", 2)

    def handle_diplomacy(self, action, region, extra=None):
        leader = self.region_leaders.get(region)
        if not leader:
            return
        if action == "peace":
            leader.set_peace(self)
        elif action == "war":
            leader.set_war(self)
        elif action == "neutral":
            leader.set_neutral(self)
        elif action == "trade" and extra is not None:
            if 0 <= extra < len(REGION_TRADE_OFFERS):
                leader.trade(self, REGION_TRADE_OFFERS[extra])
        elif action == "give_refugee":
            leader.trade_refugee(self, "give")
        elif action == "get_refugee":
            leader.trade_refugee(self, "get")

    def trade(self, idx):
        give, gn, get, rn = MARKET_TRADES[idx]
        if self.res[give] < gn:
            self.say("Không đủ để đổi!", 1.5, "warn")
        elif self.cap(get) - self.res[get] < rn:
            self.say(f"Kho {RESOURCES[get]['name'].lower()} không còn chỗ chứa!", 2, "warn")
        else:
            self.res[give] -= gn
            self.add_res(get, rn)

    def retrain(self, refugee, skill):
        if refugee.skill == skill:
            return
        if not self.can_afford(RETRAIN_COST):
            self.say("Không đủ vật liệu để đào tạo lại!", 2, "warn")
            return
        for k, v in RETRAIN_COST.items():
            self.res[k] -= v
        refugee.retrain(skill)
        self.say(f"{refugee.name} đổi nghề thành {refugee.info['name']}.", 3, "good")

    def set_speed(self, n):
        self.speed = n if n in GAME_SPEEDS else 1

    # ----- mùa -----
    def season_info(self):
        return SEASON_EFFECTS[self.season]

    def season_grow_mult(self):
        return self.season_info()["grow_mult"]

    def season_produce_mult(self):
        return self.season_info()["produce_mult"]

    def season_animal_speed(self):
        return self.season_info()["animal_speed"]

    def season_zombie_speed(self):
        return self.season_info()["zombie_speed"]

    def season_food_yield(self):
        return self.season_info()["food_yield"]

    def advance_season(self):
        """Mỗi SEASON_DAYS ngày chuyển mùa. Đông: cây chết, động vật giảm."""
        if (self.day - 1) % SEASON_DAYS == 0 and self.day > 1:
            self.season_idx = (self.season_idx + 1) % len(SEASONS)
            self.season = SEASONS[self.season_idx]
            info = self.season_info()
            self.say(f"Mùa {info['name']}: {info['desc']}", 5, "info")
        # mỗi sáng mùa đông: một số cây chết, động vật hoang giảm
        info = self.season_info()
        if info.get("tree_die_chance"):
            dead = []
            for pos, n in list(self.nodes.items()):
                if n.kind == "wood" and random.random() < info["tree_die_chance"]:
                    dead.append(pos)
            for pos in dead:
                del self.nodes[pos]
            if dead:
                self.say(f"Giá lạnh: {len(dead)} cây chết!", 3, "warn")
        if info.get("animal_die_chance"):
            survivors = []
            lost = 0
            for a in self.animals:
                if a.alive and random.random() < info["animal_die_chance"]:
                    a.hp = 0
                    lost += 1
                else:
                    survivors.append(a)
            self.animals = [a for a in self.animals if a.alive]
            if lost:
                self.say(f"Đông giá: {lost} động vật hoang biến mất.", 3, "warn")

    def total_horses(self):
        return sum(getattr(b, "horses", 0) for b in self.buildings.values() if b.kind == "stable")

    def player_speed_bonus(self):
        """Ngựa trong chuồng + nghiên cứu bio_speed."""
        bonus = 1.0 + 0.04 * self.total_horses()
        if "animal_bond" in self.researched:
            bonus += 0.03 * self.total_horses()
        if "bio_speed" in self.researched:
            bonus *= 1.15
        return bonus

    def player_armor_reduction(self):
        base = 0.0
        if "armor_adv" in self.researched:
            base = 0.35
        elif "armor_basic" in self.researched:
            base = 0.20
        m = getattr(self.player, "mounted", None)
        if m not in (None, "horse") and hasattr(m, "armor"):
            base = min(0.85, base + m.armor)
        return base

    def do_research(self, key):
        """Nghiên cứu một mục. Trả về True nếu thành công."""
        if key in self.researched:
            self.say("Đã nghiên cứu rồi!", 1.5)
            return False
        info = RESEARCHES[key]
        if info.get("requires") and info["requires"] not in self.researched:
            self.say(f"Cần nghiên cứu {RESEARCHES[info['requires']]['name']} trước!", 2, "warn")
            return False
        if not self.can_afford(info["cost"]):
            self.say("Không đủ tài nguyên để nghiên cứu!", 2, "warn")
            return False
        for k, v in info["cost"].items():
            self.res[k] -= v
        self.researched.add(key)
        # áp dụng hiệu ứng ngay
        if key == "bio_hp":
            self.player.max_hp += 20
            self.player.hp = min(self.player.max_hp, self.player.hp + 20)
            for r in self.refugees:
                r.max_hp = getattr(r, "max_hp", 30) + 20
                r.hp = min(r.max_hp, r.hp + 20)
        self.say(f"Đã nghiên cứu: {info['name']}!", 4, "good")
        return True

    def get_field(self):
        """Bản đồ đường đi của zombie, làm mới mỗi 0.4s (đủ để thấy tường bị phá / xây thêm)."""
        if self.field is None or self.field_age >= 0.4:
            self.field, self.field_age = zombie_field(self), 0.0
        return self.field

    # ----- cập nhật -----
    def update(self, dt, keys, mouse_pos, mouse_down):
        if self.over:
            return
        self.field_age += dt
        if self.panel == "diplomacy":
            leader = self.region_leaders.get(self.diplomacy_region)
            if not leader or dist(self.player.x, self.player.y, leader.x, leader.y) > 180:
                self.panel = None
                self.diplomacy_region = None
        elif self.panel and self.panel != "black_market":
            if self.near_interactive(self.panel, 160) is None:
                self.panel = None              # đi xa quá / công trình bị phá -> đóng bảng
        elif self.panel == "black_market":
            nomad = self.factions.get("nomad")
            if nomad and dist(self.player.x, self.player.y, nomad.base_x, nomad.base_y) > 180:
                self.panel = None
        # chuột theo tọa độ thế giới (camera)
        wmouse = self.screen_to_world(mouse_pos)
        self.player.update(self, dt, keys, wmouse, mouse_down)
        # Thông báo khi bước sang vùng mới
        cur = self.biome_at_world(self.player.x, self.player.y)
        if cur != self.last_biome:
            self.last_biome = cur
            binfo = BIOMES[cur]
            self.say(f"Bạn đã vào {binfo['name']}. {binfo.get('desc', '')}", 4)
        # Gần căn cứ hải quân
        if not hasattr(self, "_last_sea_msg"):
            self._last_sea_msg = 0.0
        self._last_sea_msg = max(0.0, self._last_sea_msg - dt)
        if self._last_sea_msg <= 0:
            pc, pr = int(self.player.x // TILE), int(self.player.y // TILE)
            for bc, br, side in getattr(self, "naval_bases", []):
                if abs(pc - bc) + abs(pr - br) <= 5:
                    self.say(f"Căn cứ hải quân — {SEA_NAMES.get(side, side)}. Thủy quái tuần tra ngoài khơi.", 3)
                    self._last_sea_msg = 12.0
                    break
        # Hiệu ứng môi trường theo biome
        self.apply_biome_effects(dt)
        self.update_phase(dt)
        self.update_particles(dt)
        for b in list(self.buildings.values()):
            b.update(self, dt)
        for r in self.refugees:
            r.update(self, dt)
        for z in self.zombies:
            z.update(self, dt)
        for a in self.animals:
            a.update(self, dt)
        # Unit phe
        for u in self.faction_units:
            u.update(self, dt)
        # Tộc + quái + thú vùng
        for t in self.tribes.values():
            t.update(self, dt)
        for u in self.tribe_units:
            u.update(self, dt)
        for m in self.region_monsters:
            m.update(self, dt)
        for a in self.region_animals:
            a.update(self, dt)
        for sm in self.sea_monsters:
            sm.update(self, dt)
        for boss in self.region_bosses:
            boss.update(self, dt)
        for leader in self.region_leaders.values():
            leader.update(self, dt)
        for v in self.vehicles:
            v.update(self, dt)
        self.vehicles = [v for v in self.vehicles if v.alive]
        # AI phe (giai đoạn 3)
        self.war_timer -= dt
        for f in self.factions.values():
            f.update_ai(self, dt)
        if self.war_timer <= 0:
            self.war_timer = random.uniform(50, 90)
            self._trigger_war_event()
        # Mở lại chợ đen sau một lúc
        if not self.black_market_open and random.random() < 0.008 * dt * 60:
            self.black_market_open = True
            self.say("Chợ đen đã mở cửa trở lại.", 3, "good")
        self.update_volcano(dt)
        self.update_spawns(dt)
        for b in self.bullets:
            b.update(self, dt)
        self.cleanup(dt)
        if self.core.hp <= 0 or self.player.hp <= 0:
            self.over = True



    def update_volcano(self, dt):
        """Núi lửa phun trào theo chu kỳ: sát thương + hiệu ứng quanh miệng núi lửa."""
        if not self.volcano_peaks:
            return
        if self.erupting:
            self.erupt_left -= dt
            # Gây damage cho player / unit / refugee / zombie trong bán kính
            for vc, vr in self.volcano_peaks:
                cx, cy = tile_center(vc, vr)
                rad = VOLCANO_ERUPT_RADIUS * TILE
                for obj in [self.player] + self.refugees + self.zombies + self.faction_units:
                    if getattr(obj, "hp", 0) <= 0:
                        continue
                    if dist(obj.x, obj.y, cx, cy) <= rad:
                        dmg = VOLCANO_ERUPT_DMG * dt
                        obj.hp -= dmg
                        if hasattr(obj, "hit_t"):
                            obj.hit_t = 0.3
                # Đôi khi tạo particle lửa
                if random.random() < 0.3:
                    self.particles.append(dict(
                        x=cx + random.uniform(-rad, rad),
                        y=cy + random.uniform(-rad * 0.3, rad * 0.3),
                        vx=random.uniform(-20, 20), vy=random.uniform(-80, -30),
                        life=random.uniform(0.6, 1.4), kind="ember", r=random.randint(2, 5)))
            if self.erupt_left <= 0:
                self.erupting = False
                self.erupt_t = random.uniform(*VOLCANO_ERUPT_INTERVAL)
                self.say("Núi lửa dịu lại...", 2)
        else:
            self.erupt_t -= dt
            if self.erupt_t <= 0:
                self.erupting = True
                self.erupt_left = VOLCANO_ERUPT_DURATION
                self.say("NÚI LỬA PHUN TRÀO! Tránh xa vùng núi lửa!", 5, "warn")

    def _trigger_war_event(self):
        """Chiến tranh định kỳ Chính phủ ↔ Phiến quân."""
        gov, rebel = self.factions["gov"], self.factions["rebel"]
        # Làm quan hệ xấu hơn
        self.change_relation("gov", "rebel", -15)
        gov.state = "attack"
        gov.war_target = "rebel"
        gov.state_timer = 20
        rebel.state = "attack"
        rebel.war_target = "gov"
        rebel.state_timer = 20
        # Ra lệnh một phần unit tấn công
        for u in gov.units:
            if random.random() < 0.6:
                u.state = "attack"
                u.target = (rebel.base_x, rebel.base_y)
        for u in rebel.units:
            if random.random() < 0.6:
                u.state = "attack"
                u.target = (gov.base_x, gov.base_y)
        # Ảnh hưởng chợ đen
        if random.random() < 0.4:
            self.black_market_open = False
            self.say("Chiến tranh bùng nổ! Chợ đen tạm đóng cửa.", 5, "warn")
        else:
            self.say("Chính phủ và Phiến quân giao tranh! Hãy cẩn thận.", 4, "warn")
        # Hẹn mở lại chợ
        if not self.black_market_open:
            # sẽ mở lại sau một khoảng trong update_ai nomad hoặc timer riêng
            pass

    def on_boss_killed(self):
        got = [f"{v} {RESOURCES[k]['name'].lower()}" for k, v in BOSS_REWARD.items() if self.add_res(k, v)]
        self.change_morale(10)
        self.say("BOSS ĐÃ BỊ HẠ! Nhận " + ", ".join(got) + ".", 5, "good")
        if len(self.refugees) < MAX_REFUGEES and self.free_house():
            self.spawn_elite_refugee()
        else:
            self.say("Một người tị nạn đặc biệt muốn gia nhập nhưng hết chỗ ở - hãy xây thêm nhà!", 5, "warn")

    def cleanup(self, dt):
        self.bullets = [b for b in self.bullets if b.alive]
        for z in self.zombies:
            if z.hp <= 0 and z.kind == "boss":
                self.on_boss_killed()
        self.zombies = [z for z in self.zombies if z.hp > 0]
        for e in self.effects:
            e["life"] -= dt
        self.effects = [e for e in self.effects if e["life"] > 0]
        for e in self.log:
            e["life"] -= dt
        self.log = [e for e in self.log if e["life"] > 0]
        for a in [a for a in self.animals if not a.alive]:      # bò bị hạ -> thịt
            got = self.add_res("food", a.info["food"])
            if got:
                self.popup(f"+{got} {RESOURCES['food']['name']}", a.x, a.y - 14, RESOURCES["food"]["color"])
            else:
                self.say("Kho lương thực đã đầy - thịt bị bỏ phí! Hãy xây thêm kho.", 3, "warn")
        self.animals = [a for a in self.animals if a.alive]
        # Unit phe chết
        dead_fu = [u for u in self.faction_units if not u.alive or u.hp <= 0]
        for u in dead_fu:
            u.alive = False
        self.faction_units = [u for u in self.faction_units if u.alive and u.hp > 0]
        # Quái / thú / tộc vùng
        for m in self.region_monsters:
            if m.hp <= 0:
                m.alive = False
        self.region_monsters = [m for m in self.region_monsters if m.alive]
        for sm in self.sea_monsters:
            if sm.hp <= 0:
                sm.alive = False
        self.sea_monsters = [sm for sm in self.sea_monsters if sm.alive]
        for boss in self.region_bosses:
            if boss.hp <= 0 and boss.alive:
                boss.alive = False
                boss.on_death(self)
        self.region_bosses = [b for b in self.region_bosses if b.alive]
        for a in [a for a in self.region_animals if not a.alive]:
            food = a.info.get("food", 2)
            got = self.add_res("food", food)
            if got:
                self.popup(f"+{got} lương thực", a.x, a.y - 14, (235, 170, 80))
        self.region_animals = [a for a in self.region_animals if a.alive]
        self.tribe_units = [u for u in self.tribe_units if u.alive and u.hp > 0]
        for r in [r for r in self.refugees if not r.alive]:
            if r.left:
                self.say(f"{r.name} ({r.info['name']}) đã bỏ đi vì quá chán nản...", 5, "warn")
            else:
                self.say(f"{r.name} ({r.info['name']}) đã hy sinh...", 4, "warn")
                self.change_morale(-MORALE_DEATH)
        self.refugees = [r for r in self.refugees if r.alive]
        for p in self.popups:
            p["y"] -= 22 * dt
            p["life"] -= dt
        self.popups = [p for p in self.popups if p["life"] > 0]

    def update_phase(self, dt):
        if self.phase == "day":
            self.timer -= dt
            self.day_t += dt
            while self.arrivals and self.day_t >= self.arrivals[0]:   # tới đúng mốc đã hẹn
                self.arrivals.pop(0)
                if len(self.refugees) < MAX_REFUGEES:
                    self.spawn_refugee()
            if self.timer <= 0:
                self.start_night()
        else:
            if self.to_spawn > 0:
                self.spawn_t -= dt
                if self.spawn_t <= 0:
                    self.spawn_zombie()
                    self.to_spawn -= 1
                    self.spawn_t = max(0.3, 1.2 - self.day * 0.06)
            # Spawn zombie từng vùng
            if getattr(self, "region_spawn_queue", None):
                self.region_spawn_t -= dt
                if self.region_spawn_t <= 0:
                    biome = self.region_spawn_queue.pop()
                    self.spawn_zombie(region=biome)
                    self.region_spawn_t = max(0.25, 0.9 - self.day * 0.04)
            if self.to_spawn <= 0 and not getattr(self, "region_spawn_queue", None) and not self.zombies:
                self.day += 1
                self.phase, self.timer = "day", DAY_LEN
                self.plan_arrivals()
                self.core.hp = min(self.core.max, self.core.hp + 60)
                self.player.hp = min(self.player.max_hp, self.player.hp + 40)
                for k in ("wood", "stone"):
                    self.add_res(k, 5)
                fed = self.feed_refugees()
                self.say(f"Sống sót qua đêm! Ngày {self.day} bắt đầu (+5 gỗ/đá). {fed}", 5, "good")
                self.dawn_morale()
                self.advance_season()

    def plan_arrivals(self):
        """Chia đều các lượt người tị nạn của ngày thành những mốc cách nhau một khoảng (có xê dịch nhẹ)."""
        n = min(5, REFUGEES_PER_DAY + (self.day - 1) // 4)
        slot = max(1, DAY_LEN - ARRIVAL_LEAD) / n
        self.arrivals = [(i + 0.5) * slot + random.uniform(-0.25, 0.25) * slot for i in range(n)]
        self.day_t = 0.0

    def next_arrival_in(self):
        """Số giây tới người tị nạn kế tiếp, hoặc None nếu hôm nay hết lượt."""
        if self.phase != "day" or not self.arrivals:
            return None
        return max(0.0, self.arrivals[0] - self.day_t)

    def feed_refugees(self):
        """Mỗi sáng mỗi người tị nạn ăn lương thực; thiếu thì mất máu. Trả về câu thông báo."""
        need = len(self.refugees) * FOOD_PER_REFUGEE
        self.hungry = 0
        if need <= 0:
            return ""
        eaten = min(self.res["food"], need)
        self.res["food"] -= eaten
        hungry = min(len(self.refugees), -(-(need - eaten) // FOOD_PER_REFUGEE))
        self.hungry = hungry
        if hungry <= 0:
            return f"Dân cư đã ăn (-{eaten} lương thực)."
        for r in random.sample(self.refugees, hungry):
            r.hp -= STARVE_DMG
        return f"THIẾU LƯƠNG THỰC! {hungry} người bị đói."

    def count_spawned(self, key, rule):
        if rule["type"] == "node":
            return sum(1 for n in self.nodes.values() if n.kind == key)
        return sum(1 for a in self.animals if a.kind == key)

    def update_spawns(self, dt):
        """Cây/đá/bò mọc lại: dưới giới hạn thì cứ mỗi `interval` giây mọc thêm (tối đa `batch`),
        đủ giới hạn thì dừng."""
        for key, rule in SPAWN_RULES.items():
            missing = rule["limit"] - self.count_spawned(key, rule)
            if missing <= 0:
                self.respawn_t[key] = rule["interval"]
                continue
            self.respawn_t[key] -= dt
            if self.respawn_t[key] <= 0:
                self.respawn_t[key] = rule["interval"]
                for _ in range(min(missing, rule["batch"])):
                    self.spawn_entity(key, rule)

    def start_night(self):
        self.phase = "night"
        self.arrivals = []
        # Zombie tấn công lõi (Trung địa)
        self.to_spawn = 6 + self.day * 4
        self.boss_due = self.day % BOSS_EVERY == 0
        if self.boss_due:
            self.to_spawn += 1
        self.spawn_t = 0
        # Zombie từng vùng đặc biệt (hàng đợi)
        per_region = 2 + self.day // 2
        self.region_spawn_queue = []
        for biome in ("wizard", "volcano", "arctic", "spirit"):
            for _ in range(per_region):
                self.region_spawn_queue.append(biome)
        random.shuffle(self.region_spawn_queue)
        self.region_spawn_t = 0.0
        # Thêm quái vật đặc trưng từng vùng ban đêm
        for region in REGION_MONSTERS:
            n = 1 + self.day // 3
            for _ in range(n):
                self.spawn_region_monster(region)
        total = self.to_spawn + len(self.region_spawn_queue)
        self.say(f"ĐÊM {self.day}: {total} zombie + quái vùng! Lõi & 4 vùng bị tấn công!" +
                 (" CÓ BOSS!" if self.boss_due else ""), 4, "warn")

    # ----- sinh đối tượng -----
    def pick_zombie(self):
        """Chọn loại zombie theo trọng số; loại mạnh/lạ xuất hiện dần theo ngày."""
        d = self.day
        weights = {"normal": 10.0}
        if d >= 2:
            weights["big"] = min(0.5 + d * 0.35, 3.5)
            weights["runner"] = min(1.0 + d * 0.4, 4.0)
        if d >= 3:
            weights["bomber"] = min(0.4 * (d - 1), 2.5)
        if d >= 4 and any(r.alive for r in self.refugees):
            weights["biter"] = min(0.5 * (d - 2), 3.0)
        return random.choices(list(weights), weights.values())[0]

    def spawn_zombie(self, region=None):
        """region=None: spawn từ rìa map tấn công lõi; có region: spawn trong vùng đó."""
        kind = "boss" if (self.boss_due and region is None) else self.pick_zombie()
        if region is None:
            self.boss_due = False
            s = random.randrange(4)
            x, y = [(random.uniform(0, W), -20), (W + 20, random.uniform(0, H)),
                    (random.uniform(0, W), H + 20), (-20, random.uniform(0, H))][s]
        else:
            # Spawn ở ô thuộc biome, tránh block
            pos = None
            for _ in range(40):
                c, r = random.randrange(COLS), random.randrange(ROWS)
                if self.get_biome(c, r) != region:
                    continue
                if TERRAIN.get(self.get_terrain(c, r), {}).get("block"):
                    continue
                pos = (c, r)
                break
            if pos is None:
                # fallback: tâm vùng
                cx, cy = self.biome_centers.get(region, (W / 2, H / 2))
                x, y = cx + random.uniform(-80, 80), cy + random.uniform(-80, 80)
            else:
                x, y = tile_center(*pos)
                x += random.uniform(-10, 10)
                y += random.uniform(-10, 10)
        self.zombies.append(Zombie(kind, x, y, self.day, region=region))

    def spawn_entity(self, key, rule):
        return self.spawn_node(key) if rule["type"] == "node" else self.spawn_animal(key)

    def spawn_node(self, kind):
        """Mọc một node ở ô trống, ưu tiên đúng biome của tài nguyên đó.
        Không mọc trên đường / cầu / cảng / hầm / red_line."""
        preferred = NODE_BIOME.get(kind, "middle")
        no_grow = ("road", "bridge", "port", "tunnel", "red_line")
        for attempt in range(2):
            tries = 80 if attempt == 0 else 40
            for _ in range(tries):
                c, r = random.randrange(COLS), random.randrange(ROWS)
                if (c, r) in self.nodes or (c, r) in self.buildings:
                    continue
                t = self.get_terrain(c, r)
                if TERRAIN.get(t, {}).get("block") or t in no_grow:
                    continue
                if abs(c - self.core.c) + abs(r - self.core.r) < 5 or self.unit_in_tile(c, r):
                    continue
                if attempt == 0 and self.get_biome(c, r) != preferred:
                    continue
                tx, ty = tile_center(c, r)
                if abs(self.player.x - tx) < TILE * 1.5 and abs(self.player.y - ty) < TILE * 1.5:
                    continue
                self.nodes[(c, r)] = ResourceNode(kind, c, r)
                return True
        return False

    def spawn_animal(self, kind="cow"):
        """Đặt một con vật ở chỗ trống, ưu tiên Trung địa, cách lõi một đoạn."""
        for _ in range(50):
            x, y = random.uniform(30, W - 30), random.uniform(30, H - 30)
            if abs(x - self.core.x) + abs(y - self.core.y) < 150 or self.blocked(x, y, 12):
                continue
            # Động vật thường chỉ sống ở Trung địa
            if self.biome_at_world(x, y) != "middle":
                continue
            self.animals.append(Animal(kind, x, y))
            return True
        return False

    def spawn_refugee(self):
        home = self.free_house()
        if home is None:
            self.say("Có người tị nạn muốn vào nhưng hết chỗ ở — hãy xây thêm nhà!", 5, "warn")
            return
        # Xuất hiện gần nhà được gán (hoặc lõi) để chạy vào nhà được, không kẹt mép map
        if home is not None:
            ang = random.uniform(0, 6.283)
            dist_off = random.uniform(TILE * 1.5, TILE * 3.5)
            x = home.x + math.cos(ang) * dist_off
            y = home.y + math.sin(ang) * dist_off
        else:
            x = self.core.x + random.uniform(-80, 80)
            y = self.core.y + random.uniform(-80, 80)
        x = max(TILE, min(W - TILE, x))
        y = max(TILE, min(H - TILE, y))
        # Nếu ô bị chặn, thử vài vị trí quanh nhà
        for _ in range(12):
            if not self.blocked(x, y, 12, True):
                break
            ang = random.uniform(0, 6.283)
            x = home.x + math.cos(ang) * random.uniform(TILE * 1.2, TILE * 4)
            y = home.y + math.sin(ang) * random.uniform(TILE * 1.2, TILE * 4)
            x = max(TILE, min(W - TILE, x))
            y = max(TILE, min(H - TILE, y))
        used = {r.name for r in self.refugees}
        name = random.choice([n for n in NAMES if n not in used] or NAMES)
        refugee = Refugee(x, y, name=name)
        refugee.home = home
        # Đã gần nhà → settled luôn, tránh kẹt trạng thái arriving từ xa
        refugee.state = "settled"
        self.refugees.append(refugee)
        self.say(f"{name} đã đến gần nhà và gia nhập căn cứ!", 3, "good")

    def spawn_elite_refugee(self):
        """Người tị nạn đặc biệt (thưởng boss): xuất hiện ngay cạnh lõi, khỏe, xuất phát cấp 4."""
        home = self.free_house()
        used = {r.name for r in self.refugees}
        name = random.choice([n for n in NAMES if n not in used] or NAMES)
        skill = random.choice(["gunner", "medic", "builder", "miner", "farmer", "hunter"])
        ref = Refugee(self.core.x + 40, self.core.y + 40, skill=skill, name=name, elite=True)
        ref.state, ref.home = "settled", home
        self.refugees.append(ref)
        self.say(f"{name} ({ref.info['name']}, cấp {ref.level}) - người tị nạn đặc biệt - đã gia nhập!", 6, "good")

    # ----- camera -----
    def update_camera(self):
        """Camera theo người chơi, kẹp trong biên thế giới."""
        cx = int(self.player.x - VIEW_W / 2)
        cy = int(self.player.y - VIEW_H / 2)
        cx = max(0, min(max(0, W - VIEW_W), cx))
        cy = max(0, min(max(0, H - VIEW_H), cy))
        self.cam = (cx, cy)

    def screen_to_world(self, pos):
        return (pos[0] + self.cam[0], pos[1] + self.cam[1])

    def world_to_screen(self, x, y):
        return (x - self.cam[0], y - self.cam[1])

    # ----- hạt (tuyết / lá) -----
    def update_particles(self, dt):
        info = self.season_info()
        # sinh hạt
        if info.get("snow"):
            for _ in range(3):
                self.particles.append(dict(
                    x=random.uniform(0, W), y=random.uniform(-20, 0),
                    vx=random.uniform(-15, 15), vy=random.uniform(40, 90),
                    life=random.uniform(3, 7), kind="snow", r=random.randint(2, 4)))
        if info.get("leaf_fall"):
            for _ in range(1):
                self.particles.append(dict(
                    x=random.uniform(0, W), y=random.uniform(-10, H * 0.3),
                    vx=random.uniform(-30, 30), vy=random.uniform(20, 50),
                    life=random.uniform(4, 8), kind="leaf", r=random.randint(3, 5)))
        # Hạt bọt nước gần biển (hiệu ứng nước)
        if random.random() < 0.35:
            for _ in range(2):
                side = random.choice(SEA_SIDES)
                if side == "north":
                    x, y = random.uniform(TILE * 10, W - TILE * 10), random.uniform(0, TILE * 4)
                elif side == "south":
                    x, y = random.uniform(TILE * 10, W - TILE * 10), random.uniform(H - TILE * 4, H)
                elif side == "west":
                    x, y = random.uniform(0, TILE * 4), random.uniform(TILE * 10, H - TILE * 10)
                else:
                    x, y = random.uniform(W - TILE * 4, W), random.uniform(TILE * 10, H - TILE * 10)
                self.particles.append(dict(
                    x=x, y=y,
                    vx=random.uniform(-25, 25), vy=random.uniform(-15, 15),
                    life=random.uniform(0.8, 2.0), kind="splash", r=random.randint(1, 3)))
        alive = []
        for p in self.particles:
            p["life"] -= dt
            if p["life"] <= 0:
                continue
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            if p["y"] < H + 20:
                alive.append(p)
        self.particles = alive[-180:]  # keep particle count low for performance

    # ----- lưu / nạp -----
    def save_game(self, path=None):
        path = path or SAVE_FILE
        data = {
            "day": self.day, "phase": self.phase, "timer": self.timer,
            "season_idx": self.season_idx, "season": self.season,
            "res": self.res, "morale": self.morale,
            "researched": list(self.researched),
            "player": {
                "x": self.player.x, "y": self.player.y, "hp": self.player.hp,
                "max_hp": self.player.max_hp, "weapon": self.player.weapon,
                "owned": dict(self.player.owned),
            },
            "buildings": [
                {"kind": b.kind, "c": b.c, "r": b.r, "hp": b.hp,
                 "cows": getattr(b, "cows", 0), "horses": getattr(b, "horses", 0),
                 "dogs": getattr(b, "dogs", 0), "progress": getattr(b, "progress", 0),
                 "spent": b.spent}
                for b in self.buildings.values()
            ],
            "nodes": [{"kind": n.kind, "c": n.c, "r": n.r, "amount": n.amount}
                      for n in self.nodes.values()],
            "refugees": [
                {"name": r.name, "skill": r.skill, "x": r.x, "y": r.y,
                 "hp": r.hp, "xp": r.xp, "elite": r.elite, "state": r.state,
                 "home": (r.home.c, r.home.r) if r.home else None}
                for r in self.refugees if r.alive
            ],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        self.say(f"Đã lưu game vào {path}", 3, "good")
        return True

    def load_game(self, path=None):
        path = path or SAVE_FILE
        if not os.path.isfile(path):
            self.say(f"Không tìm thấy file {path}", 3, "warn")
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.say(f"Lỗi đọc save: {e}", 3, "warn")
            return False
        self.reset()
        self.day = data.get("day", 1)
        self.phase = data.get("phase", "day")
        self.timer = data.get("timer", DAY_LEN)
        self.season_idx = data.get("season_idx", 0)
        self.season = data.get("season", SEASONS[0])
        self.res = {k: data.get("res", {}).get(k, info["start"]) for k, info in RESOURCES.items()}
        self.morale = float(data.get("morale", MORALE_START))
        self.researched = set(data.get("researched", []))
        p = data.get("player", {})
        self.player.x = p.get("x", W / 2)
        self.player.y = p.get("y", H / 2 + 60)
        self.player.hp = p.get("hp", 100)
        self.player.max_hp = p.get("max_hp", 100)
        self.player.weapon = p.get("weapon", "pistol")
        owned = p.get("owned", {"pistol": 1})
        # tương thích save cũ (set)
        if isinstance(owned, list):
            owned = {k: 1 for k in owned}
        self.player.owned = dict(owned)
        self.buildings.clear()
        self.nodes.clear()
        for bd in data.get("buildings", []):
            b = Building(bd["kind"], bd["c"], bd["r"])
            b.hp = bd.get("hp", b.max)
            b.spent = bd.get("spent", dict(b.info.get("cost", {})))
            if "cows" in bd:
                b.cows = bd["cows"]
            if "horses" in bd:
                b.horses = bd["horses"]
            if "dogs" in bd:
                b.dogs = bd["dogs"]
            if "progress" in bd:
                b.progress = bd["progress"]
            self.buildings[(b.c, b.r)] = b
            if b.kind == "core":
                self.core = b
        for nd in data.get("nodes", []):
            n = ResourceNode(nd["kind"], nd["c"], nd["r"], nd.get("amount", 5))
            self.nodes[(n.c, n.r)] = n
        from entities.refugee import Refugee
        self.refugees.clear()
        for rd in data.get("refugees", []):
            r = Refugee(rd["x"], rd["y"], skill=rd.get("skill"), name=rd.get("name"),
                        elite=rd.get("elite", False))
            r.hp = rd.get("hp", r.hp)
            r.xp = rd.get("xp", 0)
            r.state = rd.get("state", "settled")
            home = rd.get("home")
            if home:
                r.home = self.buildings.get(tuple(home))
            self.refugees.append(r)
        self.plan_arrivals()
        self.say(f"Đã nạp game từ {path} (Ngày {self.day})", 4, "good")
        return True

    def invalidate_terrain_cache(self):
        self._terrain_dirty = True

    def _build_terrain_cache(self):
        """Bake static terrain+biome into a surface (expensive, rare)."""
        if not hasattr(self, "_terrain_cache") or self._terrain_cache.get_size() != (W, H):
            self._terrain_cache = pygame.Surface((W, H))
        tc = self._terrain_cache
        info = self.season_info()
        snow = info.get("snow")
        autumn = info.get("leaf_fall")
        self._water_tiles = []  # (c,r,kind) for cheap animation in view
        self._lava_tiles = []
        for r in range(ROWS):
            for c in range(COLS):
                terr = self.terrain_map[r][c]
                tinfo = TERRAIN.get(terr, TERRAIN["none"])
                rect = (c * TILE, r * TILE, TILE, TILE)
                if tinfo.get("color"):
                    col = tinfo["color"]
                    if terr in ("sea", "river", "lake", "pond"):
                        self._water_tiles.append((c, r, terr))
                    if terr == "lava":
                        self._lava_tiles.append((c, r))
                    tc.fill(col, rect)
                    if terr == "bridge":
                        pygame.draw.rect(tc, (160, 130, 80), (c * TILE + 4, r * TILE + TILE // 2 - 3, TILE - 8, 6))
                        pygame.draw.rect(tc, (100, 80, 50), (c * TILE + 6, r * TILE + 6, 4, TILE - 12))
                        pygame.draw.rect(tc, (100, 80, 50), (c * TILE + TILE - 10, r * TILE + 6, 4, TILE - 12))
                    elif terr == "port":
                        pygame.draw.rect(tc, (120, 110, 90), (c * TILE + 2, r * TILE + 2, TILE - 4, TILE - 4))
                        pygame.draw.rect(tc, (70, 90, 130), (c * TILE + 6, r * TILE + TILE // 2 - 2, TILE - 12, 5))
                        pygame.draw.circle(tc, (200, 180, 100), (c * TILE + TILE // 2, r * TILE + 8), 3)
                        is_base = any(abs(c - bc) < 3 and abs(r - br) < 3
                                      for bc, br, _ in getattr(self, "naval_bases", []))
                        if is_base:
                            pygame.draw.line(tc, (180, 180, 180),
                                             (c * TILE + TILE // 2, r * TILE + 4),
                                             (c * TILE + TILE // 2, r * TILE + 14), 1)
                            pygame.draw.polygon(tc, (220, 50, 40),
                                                [(c * TILE + TILE // 2, r * TILE + 4),
                                                 (c * TILE + TILE // 2 + 8, r * TILE + 7),
                                                 (c * TILE + TILE // 2, r * TILE + 10)])
                    elif terr == "road":
                        pygame.draw.rect(tc, (130, 120, 100), (c * TILE + 10, r * TILE + 10, TILE - 20, TILE - 20))
                    elif terr == "rail":
                        pygame.draw.line(tc, (40, 40, 40), (c * TILE + 4, r * TILE + 10), (c * TILE + TILE - 4, r * TILE + 10), 2)
                        pygame.draw.line(tc, (40, 40, 40), (c * TILE + 4, r * TILE + 22), (c * TILE + TILE - 4, r * TILE + 22), 2)
                        for i in range(4):
                            pygame.draw.line(tc, (90, 70, 40),
                                             (c * TILE + 6 + i * 7, r * TILE + 8),
                                             (c * TILE + 6 + i * 7, r * TILE + 24), 2)
                    elif terr == "tunnel":
                        pygame.draw.rect(tc, (45, 40, 38), rect)
                        pygame.draw.rect(tc, (90, 85, 70), (c * TILE + 8, r * TILE + 10, TILE - 16, TILE - 14))
                        pygame.draw.arc(tc, (60, 55, 50),
                                        (c * TILE + 4, r * TILE + 2, TILE - 8, TILE - 6), 0, 3.14, 2)
                    elif terr == "red_line":
                        pygame.draw.rect(tc, (140, 30, 30), rect)
                        pygame.draw.line(tc, (255, 80, 70),
                                         (c * TILE + 2, r * TILE + TILE // 2),
                                         (c * TILE + TILE - 2, r * TILE + TILE // 2), 2)
                    elif terr == "mountain":
                        pts = [(c * TILE + TILE // 2, r * TILE + 4),
                               (c * TILE + 4, r * TILE + TILE - 4),
                               (c * TILE + TILE - 4, r * TILE + TILE - 4)]
                        pygame.draw.polygon(tc, (70, 65, 60), pts)
                        pygame.draw.polygon(tc, (110, 105, 95), pts, 1)
                else:
                    bid = self.biome_map[r][c]
                    binfo = BIOMES[bid]
                    if snow:
                        col = binfo.get("color_winter", binfo["color"])
                        gcol = binfo.get("grid_winter", binfo["grid"])
                    elif autumn:
                        col = binfo.get("color_autumn", binfo["color"])
                        gcol = binfo.get("grid_autumn", binfo["grid"])
                    else:
                        col = binfo["color"]
                        gcol = binfo["grid"]
                    tc.fill(col, rect)
                    if (c + r) % 2 == 0:
                        pygame.draw.rect(tc, gcol, rect, 1)
        self._terrain_dirty = False
        self._terrain_season = self.season

    # ----- draw -----
    def draw(self, mouse_pos):
        self.update_camera()
        s = self.screen
        if not hasattr(self, "_world") or self._world.get_size() != (W, H):
            self._world = pygame.Surface((W, H))
        ws = self._world
        info = self.season_info()
        if getattr(self, "_terrain_dirty", True) or getattr(self, "_terrain_season", None) != self.season:
            self._build_terrain_cache()
        ws.blit(self._terrain_cache, (0, 0))
        # Animate only water/lava in camera view
        cx, cy = self.cam
        c0, r0 = max(0, int(cx // TILE) - 1), max(0, int(cy // TILE) - 1)
        c1 = min(COLS, int((cx + VIEW_W) // TILE) + 2)
        r1 = min(ROWS, int((cy + VIEW_H) // TILE) + 2)
        ticks = pygame.time.get_ticks()
        for c, r, terr in getattr(self, "_water_tiles", []):
            if not (c0 <= c < c1 and r0 <= r < r1):
                continue
            wave = math.sin(ticks * 0.004 + c * 0.35 + r * 0.28) * 10
            col = TERRAIN[terr]["color"]
            if terr == "sea":
                side = self.sea_side_map[r][c]
                base = {"north": (30, 70, 130), "east": (40, 50, 140),
                        "south": (50, 60, 100), "west": (25, 45, 100)}.get(side, (25, 55, 110))
                col = (max(10, min(255, int(base[0] + wave))),
                       max(20, min(255, int(base[1] + wave * 0.6))),
                       max(80, min(255, int(base[2] + wave * 0.4))))
            else:
                col = (max(15, min(255, int(col[0] + wave * 0.5))),
                       max(30, min(255, int(col[1] + wave * 0.4))),
                       max(80, min(255, int(col[2] + wave * 0.3))))
            rect = (c * TILE, r * TILE, TILE, TILE)
            ws.fill(col, rect)
            wy = r * TILE + TILE // 2 + int(math.sin(ticks * 0.005 + c * 0.5) * 3)
            pygame.draw.line(ws, (180, 210, 240), (c * TILE + 2, wy), (c * TILE + TILE - 2, wy), 1)
        if self.erupting:
            pulse = 40 + int(30 * abs(math.sin(ticks * 0.008)))
            for c, r in getattr(self, "_lava_tiles", []):
                if not (c0 <= c < c1 and r0 <= r < r1):
                    continue
                col = (min(255, 180 + pulse), 40 + pulse // 3, 10)
                ws.fill(col, (c * TILE, r * TILE, TILE, TILE))
        # Volcano eruption rings
        if self.erupting:
            for vc, vr in self.volcano_peaks:
                for dr in range(-VOLCANO_ERUPT_RADIUS, VOLCANO_ERUPT_RADIUS + 1):
                    for dc in range(-VOLCANO_ERUPT_RADIUS, VOLCANO_ERUPT_RADIUS + 1):
                        if dc * dc + dr * dr <= VOLCANO_ERUPT_RADIUS * VOLCANO_ERUPT_RADIUS:
                            nc, nr = vc + dc, vr + dr
                            if 0 <= nc < COLS and 0 <= nr < ROWS:
                                alpha_col = (255, 100, 30)
                                pygame.draw.rect(ws, alpha_col, (nc * TILE + 2, nr * TILE + 2, TILE - 4, TILE - 4), 1)
        # floor trước
        for b in self.buildings.values():
            if b.info.get("floor"):
                b.draw(ws)
        for n in self.nodes.values():
            n.draw(ws, info)
        for b in self.buildings.values():
            if not b.info.get("floor"):
                b.draw(ws)
        for group in (self.animals, self.region_animals, self.refugees, self.zombies,
                      self.region_monsters, self.sea_monsters, self.region_bosses,
                      self.bullets, self.faction_units, self.tribe_units):
            for o in group:
                o.draw(ws)
        for leader in self.region_leaders.values():
            leader.draw(ws)
        for v in self.vehicles:
            v.draw(ws)
        # Nhãn căn cứ hải quân (gần camera)
        cx, cy = self.cam
        for bc, br, side in getattr(self, "naval_bases", []):
            bx, by = bc * TILE + TILE, br * TILE - 6
            if cx - 40 < bx < cx + VIEW_W + 40 and cy - 20 < by < cy + VIEW_H + 20:
                label = f"⚓ {SEA_NAMES.get(side, side)}"
                try:
                    font = pygame.font.SysFont("segoeui", 12, bold=True)
                except Exception:
                    font = pygame.font.Font(None, 16)
                txt = font.render(label, True, (255, 220, 180))
                ws.blit(txt, (bx - txt.get_width() // 2, by))
        for f in self.factions.values():
            f.draw_base_marker(ws)
        for t in self.tribes.values():
            t.draw_marker(ws)
        if self.show_routes:
            self.draw_routes(ws)
        for e in self.effects:
            k = 1 - e["life"] / e["max"]
            pygame.draw.circle(ws, (255, 190, 80), (int(e["x"]), int(e["y"])),
                               int(e["r"] * (0.4 + 0.6 * k)), 0 if k < 0.35 else 4)
        # hạt
        for p in self.particles:
            if p["kind"] == "snow":
                pygame.draw.circle(ws, (240, 245, 255), (int(p["x"]), int(p["y"])), p["r"])
            elif p["kind"] == "ember":
                pygame.draw.circle(ws, (255, 120 + random.randint(0, 80), 30), (int(p["x"]), int(p["y"])), p["r"])
            elif p["kind"] == "splash":
                alpha = max(40, min(200, int(180 * p["life"])))
                pygame.draw.circle(ws, (200, 230, 255), (int(p["x"]), int(p["y"])), p["r"])
            else:
                pygame.draw.ellipse(ws, (200, 140, 40), (int(p["x"]), int(p["y"]), p["r"] + 1, p["r"]))
        # player trên world, mouse world
        wmx, wmy = self.screen_to_world(mouse_pos)
        self.player.draw(ws, (wmx, wmy))
        cx, cy = self.cam
        s.blit(ws, (0, 0), (cx, cy, VIEW_W, VIEW_H))
        if self.phase == "night":
            if self.night_overlay.get_size() != (VIEW_W, VIEW_H):
                self.night_overlay = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            self.night_overlay.fill((5, 8, 30, 110))
            s.blit(self.night_overlay, (0, 0))
        # Overlay hiệu ứng biome (nóng / lạnh / sợ...)
        bid = self.biome_at_world(self.player.x, self.player.y)
        fx = BIOME_EFFECTS.get(bid, {})
        ov = fx.get("overlay")
        if ov:
            if not hasattr(self, "_biome_overlay") or self._biome_overlay.get_size() != (VIEW_W, VIEW_H):
                self._biome_overlay = pygame.Surface((VIEW_W, VIEW_H), pygame.SRCALPHA)
            self._biome_overlay.fill(ov)
            s.blit(self._biome_overlay, (0, 0))
        # Rung nhẹ camera khi spirit/volcano
        shake = fx.get("shake", 0)
        if shake and random.random() < shake * 0.15:
            pass  # visual already via overlay; optional offset skipped to keep stable
        self.hud.draw(self, mouse_pos)

    def draw_routes(self, s):
        """Phím Z: vẽ đường zombie sẽ đi từ các điểm quanh rìa bản đồ."""
        field = self.get_field()
        starts = [(W * f, 4) for f in (0.15, 0.5, 0.85)] + [(W * f, H - 4) for f in (0.15, 0.5, 0.85)] \
            + [(4, H * f) for f in (0.3, 0.7)] + [(W - 4, H * f) for f in (0.3, 0.7)]
        for x, y in starts:
            pts = trace_route(self, field, x, y)
            if len(pts) > 1:
                pygame.draw.lines(s, (255, 90, 90), False, pts, 2)
