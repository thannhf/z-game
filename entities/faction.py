"""Hệ thống 3 phe AI: Chính phủ, Phiến quân, Du mục (chợ đen).

Mỗi phe có:
- Căn cứ cố định (base_c, base_r) + vài công trình tường/tháp đơn giản
- Unit (lính) tuần tra / tấn công
- Quan hệ với người chơi và với các phe khác
- AI đơn giản → thông minh dần (giai đoạn 2 + 3)
"""
import math
import random

import pygame

from settings import TILE, COLS, ROWS, W, H
from utils import tile_center, dist, nearest, tile_of

# ---------------------------------------------------------------------------
# Dữ liệu phe
# ---------------------------------------------------------------------------
FACTIONS = {
    "gov": dict(
        name="Chính phủ",
        color=(70, 120, 200),
        unit_color=(90, 140, 220),
        desc="Quân đội chính quy, thiết quân luật, tài nguyên thắt chặt.",
        # Vị trí căn cứ (góc / cạnh Trung địa)
        base_c=22, base_r=22,
        max_units=8,
        unit_kinds=("soldier", "officer"),
        aggression=0.35,          # thấp hơn → thiên phòng thủ
        trade_willing=0.6,
    ),
    "rebel": dict(
        name="Phiến quân",
        color=(200, 70, 60),
        unit_color=(220, 90, 70),
        desc="Nổi loạn, tàn bạo, sống nhờ chợ đen.",
        base_c=COLS - 23, base_r=ROWS - 23,
        max_units=10,
        unit_kinds=("raider", "brute"),
        aggression=0.75,
        trade_willing=0.4,
    ),
    "nomad": dict(
        name="Du mục (Chợ đen)",
        color=(180, 140, 60),
        unit_color=(210, 170, 80),
        desc="Trung lập thực dụng, có mọi thứ, nguy hiểm.",
        base_c=COLS - 23, base_r=22,
        max_units=6,
        unit_kinds=("guard", "trader"),
        aggression=0.25,
        trade_willing=0.95,
    ),
}

# Unit types
FACTION_UNITS = {
    "soldier": dict(name="Lính CP", r=10, hp=18, speed=70, dmg=7, range=90, color=(90, 140, 220), cooldown=0.9),
    "officer": dict(name="Sĩ quan", r=11, hp=22, speed=65, dmg=9, range=100, color=(60, 100, 180), cooldown=0.8),
    "raider":  dict(name="Phiến quân", r=10, hp=14, speed=85, dmg=8, range=80, color=(220, 90, 70), cooldown=0.75),
    "brute":   dict(name="Côn đồ", r=13, hp=28, speed=55, dmg=12, range=55, color=(180, 50, 40), cooldown=1.1),
    "guard":   dict(name="Bảo vệ chợ", r=11, hp=20, speed=60, dmg=6, range=85, color=(210, 170, 80), cooldown=1.0),
    "trader":  dict(name="Thương nhân", r=9, hp=12, speed=75, dmg=4, range=50, color=(200, 160, 70), cooldown=1.2),
}

# Quan hệ: -100 .. +100
REL_HOSTILE = -40
REL_FRIENDLY = 40
REL_ALLY = 70

# Chợ đen: danh sách giao dịch (đưa, số lượng, nhận, số lượng)
BLACK_MARKET_TRADES = [
    ("wood", 6, "food", 2),
    ("stone", 5, "food", 2),
    ("food", 3, "wood", 4),
    ("copper", 4, "iron", 2),
    ("iron", 3, "copper", 4),
    ("silver", 2, "gold", 1),
    ("mana", 2, "iron", 3),
    ("obsidian", 2, "stone", 8),
    ("ice_crystal", 2, "food", 4),
    ("soul_essence", 1, "silver", 2),
    ("wood", 10, "copper", 2),
    ("stone", 8, "iron", 2),
]


class FactionUnit:
    """Lính của phe AI."""
    def __init__(self, faction_id, kind, x, y):
        d = FACTION_UNITS[kind]
        self.faction_id = faction_id
        self.kind = kind
        self.info = d
        self.x, self.y = x, y
        self.r = d["r"]
        self.hp = self.max_hp = float(d["hp"])
        self.speed = d["speed"]
        self.dmg = d["dmg"]
        self.range = d["range"]
        self.color = d["color"]
        self.cool = 0.0
        self.cooldown = d["cooldown"]
        self.state = "patrol"          # patrol | attack | return | idle
        self.target = None            # entity hoặc (x,y)
        self.patrol_angle = random.uniform(0, math.tau)
        self.alive = True
        self.home_x, self.home_y = x, y

    def update(self, game, dt):
        if not self.alive or self.hp <= 0:
            self.alive = False
            return
        self.cool = max(0.0, self.cool - dt)
        fac = game.factions[self.faction_id]

        # 1. Tìm mục tiêu thù địch gần
        enemy = self._find_enemy(game)
        if enemy is not None:
            self.state = "attack"
            self.target = enemy
        elif self.state == "attack":
            self.state = "patrol"
            self.target = None

        # 2. Hành vi theo state
        if self.state == "attack" and self.target is not None:
            self._do_attack(game, dt)
        else:
            self._do_patrol(game, dt, fac)

    def _find_enemy(self, game):
        """Ưu tiên: unit phe thù địch → zombie gần → player nếu quan hệ xấu."""
        best, best_d = None, 220
        # Unit phe khác
        for u in game.faction_units:
            if not u.alive or u.faction_id == self.faction_id:
                continue
            rel = game.get_relation(self.faction_id, u.faction_id)
            if rel > REL_HOSTILE:
                continue
            d = dist(self.x, self.y, u.x, u.y)
            if d < best_d:
                best, best_d = u, d
        # Zombie
        for z in game.zombies:
            if z.hp <= 0:
                continue
            d = dist(self.x, self.y, z.x, z.y)
            if d < best_d:
                best, best_d = z, d
        # Player (nếu quan hệ xấu)
        rel_p = game.player_relation.get(self.faction_id, 0)
        if rel_p <= REL_HOSTILE:
            d = dist(self.x, self.y, game.player.x, game.player.y)
            if d < best_d:
                best, best_d = game.player, d
        # Công trình player nếu quan hệ rất xấu và gần căn cứ player
        return best

    def _do_attack(self, game, dt):
        t = self.target
        if t is None:
            self.state = "patrol"
            return
        # Lấy vị trí mục tiêu
        if hasattr(t, "x"):
            tx, ty = t.x, t.y
            if getattr(t, "hp", 1) <= 0 or not getattr(t, "alive", True):
                self.target = None
                self.state = "patrol"
                return
        else:
            tx, ty = t
        d = dist(self.x, self.y, tx, ty)
        if d <= self.range:
            # Bắn / đánh
            if self.cool <= 0:
                self.cool = self.cooldown
                self._deal_damage(game, t)
        else:
            # Tiến lại gần
            ang = math.atan2(ty - self.y, tx - self.x)
            nx = self.x + math.cos(ang) * self.speed * dt
            ny = self.y + math.sin(ang) * self.speed * dt
            if not game.blocked(nx, ny, self.r, pass_gates=True):
                self.x, self.y = nx, ny

    def _deal_damage(self, game, target):
        if hasattr(target, "hp"):
            target.hp -= self.dmg
            if hasattr(target, "hit_t"):
                target.hit_t = 0.4
            if target.hp <= 0:
                # Giết unit phe khác → quan hệ xấu đi
                if isinstance(target, FactionUnit) and target.faction_id != self.faction_id:
                    game.change_relation(self.faction_id, target.faction_id, -8)
                    game.change_player_relation(target.faction_id, -3)  # player thấy xung đột
                self.target = None
                self.state = "patrol"

    def _do_patrol(self, game, dt, fac):
        """Tuần tra quanh căn cứ."""
        bx, by = fac.base_x, fac.base_y
        # Giữ trong bán kính tuần tra
        d_home = dist(self.x, self.y, bx, by)
        if d_home > 280:
            ang = math.atan2(by - self.y, bx - self.x)
        else:
            self.patrol_angle += random.uniform(-1.2, 1.2) * dt
            ang = self.patrol_angle
        nx = self.x + math.cos(ang) * self.speed * 0.55 * dt
        ny = self.y + math.sin(ang) * self.speed * 0.55 * dt
        if not game.blocked(nx, ny, self.r, pass_gates=True):
            self.x, self.y = nx, ny
        else:
            self.patrol_angle += random.uniform(1.5, 3.0)

    def draw(self, surf):
        if not self.alive:
            return
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(surf, (20, 20, 25), (int(self.x), int(self.y)), self.r, 1)
        # Thanh máu nhỏ
        if self.hp < self.max_hp:
            w = self.r * 2
            pygame.draw.rect(surf, (60, 0, 0), (self.x - self.r, self.y - self.r - 6, w, 3))
            pygame.draw.rect(surf, (200, 60, 50), (self.x - self.r, self.y - self.r - 6,
                                                   w * max(0, self.hp) / self.max_hp, 3))


class Faction:
    """Một phe AI."""
    def __init__(self, fid):
        d = FACTIONS[fid]
        self.id = fid
        self.info = d
        self.name = d["name"]
        self.color = d["color"]
        self.base_c = d["base_c"]
        self.base_r = d["base_r"]
        self.base_x, self.base_y = tile_center(self.base_c, self.base_r)
        self.max_units = d["max_units"]
        self.aggression = d["aggression"]
        self.trade_willing = d["trade_willing"]
        self.units = []               # list FactionUnit (tham chiếu)
        self.state = "defend"          # defend | attack | trade | raid
        self.state_timer = 0.0
        self.war_target = None        # faction_id đang đánh
        self.strength = 1.0           # ước lượng lực lượng

    def spawn_initial_units(self, game):
        """Sinh unit ban đầu quanh căn cứ."""
        kinds = self.info["unit_kinds"]
        n = min(4, self.max_units)
        for i in range(n):
            kind = kinds[i % len(kinds)]
            ang = i * math.tau / n
            x = self.base_x + math.cos(ang) * 50
            y = self.base_y + math.sin(ang) * 50
            u = FactionUnit(self.id, kind, x, y)
            u.home_x, u.home_y = self.base_x, self.base_y
            self.units.append(u)
            game.faction_units.append(u)

    def build_base(self, game):
        """Xây vài tường + tháp quanh căn cứ (dùng building có sẵn)."""
        from entities.building import Building
        c, r = self.base_c, self.base_r
        # Dọn địa hình block quanh căn cứ để có chỗ xây
        for dr in range(-4, 5):
            for dc in range(-4, 5):
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if game.terrain_map[nr][nc] in ("mountain", "river", "lake", "pond", "sea", "lava"):
                        game.terrain_map[nr][nc] = "none"

        # Lõi giả (không phải core player)
        offsets_wall = [
            (-2, -2), (-1, -2), (0, -2), (1, -2), (2, -2),
            (-2, 2), (-1, 2), (0, 2), (1, 2), (2, 2),
            (-2, -1), (-2, 0), (-2, 1),
            (2, -1), (2, 0), (2, 1),
        ]
        for dc, dr in offsets_wall:
            pos = (c + dc, r + dr)
            if pos not in game.buildings and pos not in game.nodes:
                if 0 <= pos[0] < COLS and 0 <= pos[1] < ROWS:
                    try:
                        b = Building("wall", pos[0], pos[1])
                        game.buildings[pos] = b
                    except Exception:
                        pass
        # 2 tháp
        for dc, dr in ((-3, 0), (3, 0)):
            pos = (c + dc, r + dr)
            if pos not in game.buildings and 0 <= pos[0] < COLS and 0 <= pos[1] < ROWS:
                try:
                    b = Building("turret", pos[0], pos[1])
                    game.buildings[pos] = b
                except Exception:
                    pass

    def recount_units(self, game):
        self.units = [u for u in game.faction_units if u.alive and u.faction_id == self.id]
        self.strength = len(self.units) / max(1, self.max_units)

    def update_ai(self, game, dt):
        """Giai đoạn 3: ra quyết định."""
        self.state_timer -= dt
        self.recount_units(game)

        # Hồi unit nếu thiếu
        if len(self.units) < self.max_units and random.random() < 0.015 * dt * 60:
            self._spawn_one(game)

        if self.state_timer > 0:
            return

        # Quyết định mới mỗi 8–15 giây
        self.state_timer = random.uniform(8, 15)

        if self.id == "nomad":
            self.state = "trade"
            self.war_target = None
            return

        # Chính phủ & Phiến quân
        other = "rebel" if self.id == "gov" else "gov"
        rel = game.get_relation(self.id, other)
        my_str = self.strength
        their_str = game.factions[other].strength

        # Chiến tranh định kỳ / theo lực lượng
        if rel < REL_HOSTILE or (my_str > their_str * 0.9 and random.random() < self.aggression):
            self.state = "attack"
            self.war_target = other
            # Ra lệnh unit tiến về căn cứ địch
            enemy_base = game.factions[other]
            for u in self.units:
                if random.random() < 0.55:
                    u.state = "attack"
                    u.target = (enemy_base.base_x, enemy_base.base_y)
        else:
            self.state = "defend"
            self.war_target = None
            for u in self.units:
                u.state = "patrol"
                u.target = None

    def _spawn_one(self, game):
        kinds = self.info["unit_kinds"]
        kind = random.choice(kinds)
        ang = random.uniform(0, math.tau)
        x = self.base_x + math.cos(ang) * 40
        y = self.base_y + math.sin(ang) * 40
        u = FactionUnit(self.id, kind, x, y)
        self.units.append(u)
        game.faction_units.append(u)

    def draw_base_marker(self, surf):
        """Vẽ cờ / vòng tròn đánh dấu căn cứ."""
        pygame.draw.circle(surf, self.color, (int(self.base_x), int(self.base_y)), 18, 2)
        pygame.draw.circle(surf, self.color, (int(self.base_x), int(self.base_y)), 6)
