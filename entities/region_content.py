"""Nội dung riêng từng vùng: quái, động vật, thực vật, tộc người, thủy quái."""
import math
import random

import pygame

from settings import TILE, COLS, ROWS, TERRAIN
from utils import tile_center, dist, nearest, tile_of

# ---------------------------------------------------------------------------
# Thủy quái theo từng vùng biển (north/east/south/west)
# ---------------------------------------------------------------------------
SEA_MONSTERS = {
    "north": {
        "ice_serpent": dict(name="Rắn biển băng", r=14, hp=14, speed=55, dmg=12, color=(160, 210, 240)),
        "frost_kraken": dict(name="Kraken băng",  r=18, hp=22, speed=35, dmg=16, color=(100, 170, 220)),
    },
    "east": {
        "mana_eel":   dict(name="Lươn phép",   r=12, hp=10, speed=70, dmg=9,  color=(180, 140, 255)),
        "arcane_ray": dict(name="Cá đuối ảo",  r=15, hp=16, speed=48, dmg=13, color=(140, 100, 220)),
    },
    "south": {
        "magma_shark": dict(name="Cá mập magma", r=14, hp=15, speed=60, dmg=14, color=(240, 90, 30)),
        "lava_hydra":  dict(name="Hydra dung nham", r=17, hp=20, speed=40, dmg=15, color=(220, 60, 20)),
    },
    "west": {
        "soul_whale":  dict(name="Cá voi hồn",  r=16, hp=18, speed=42, dmg=13, color=(120, 70, 180)),
        "shadow_ray":  dict(name="Cá đuối bóng", r=13, hp=11, speed=65, dmg=10, color=(70, 40, 100)),
    },
}


class SeaMonster:
    """Thủy quái sống trên ô biển của một hướng; tấn công khi player/unit gần bờ."""
    def __init__(self, side, kind, x, y, day=1):
        d = SEA_MONSTERS[side][kind]
        self.side, self.kind = side, kind
        self.info = d
        self.x, self.y = x, y
        self.r = d["r"]
        self.hp = self.max_hp = float(d["hp"] + day * 0.35)
        self.speed = d["speed"]
        self.dmg = d["dmg"]
        self.color = d["color"]
        self.atk = 0.0
        self.angle = random.uniform(0, math.tau)
        self.alive = True
        self.bob = random.uniform(0, math.tau)

    def _on_sea_or_shore(self, game, nx, ny):
        """Cho phép di chuyển trên biển / port / gần bờ."""
        c, r = int(nx // TILE), int(ny // TILE)
        if not (0 <= c < COLS and 0 <= r < ROWS):
            return False
        t = game.get_terrain(c, r)
        if t in ("sea", "port", "bridge"):
            return True
        # Gần bờ biển
        for dc, dr in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)):
            nc, nr = c + dc, r + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS and game.get_terrain(nc, nr) == "sea":
                return True
        return False

    def update(self, game, dt):
        if not self.alive or self.hp <= 0:
            self.alive = False
            return
        self.atk = max(0.0, self.atk - dt)
        self.bob += dt * 2.2
        target = None
        best = 260
        for obj in [game.player] + list(game.refugees) + list(getattr(game, "faction_units", [])) + list(getattr(game, "tribe_units", [])):
            if getattr(obj, "hp", 0) <= 0:
                continue
            if hasattr(obj, "alive") and not obj.alive:
                continue
            d = dist(self.x, self.y, obj.x, obj.y)
            if d < best:
                best, target = d, obj
        if target is None:
            self.angle += random.uniform(-1.2, 1.2) * dt
            nx = self.x + math.cos(self.angle) * self.speed * 0.35 * dt
            ny = self.y + math.sin(self.angle) * self.speed * 0.35 * dt
            if self._on_sea_or_shore(game, nx, ny):
                self.x, self.y = nx, ny
            return
        ang = math.atan2(target.y - self.y, target.x - self.x)
        self.angle = ang
        d = dist(self.x, self.y, target.x, target.y)
        if d < self.r + getattr(target, "r", getattr(target, "R", 12)) + 6:
            if self.atk <= 0:
                self.atk = 0.9
                if target is game.player and hasattr(target, "take_damage"):
                    target.take_damage(self.dmg, game.player_armor_reduction())
                else:
                    target.hp -= self.dmg
                    if hasattr(target, "hit_t"):
                        target.hit_t = 0.3
        else:
            nx = self.x + math.cos(ang) * self.speed * dt
            ny = self.y + math.sin(ang) * self.speed * dt
            if self._on_sea_or_shore(game, nx, ny):
                self.x, self.y = nx, ny

    def draw(self, surf):
        if not self.alive:
            return
        by = int(self.y + math.sin(self.bob) * 2.5)
        # thân
        pygame.draw.ellipse(surf, self.color, (int(self.x - self.r), by - self.r // 2, self.r * 2, self.r))
        # mắt
        pygame.draw.circle(surf, (255, 240, 200), (int(self.x + math.cos(self.angle) * self.r * 0.4),
                                                   by + int(math.sin(self.angle) * 2)), 3)
        # viền
        pygame.draw.ellipse(surf, (15, 20, 40), (int(self.x - self.r), by - self.r // 2, self.r * 2, self.r), 1)
        # sóng nhỏ quanh
        wave = 2 + int(2 * abs(math.sin(self.bob)))
        pygame.draw.arc(surf, (180, 220, 255), (int(self.x - self.r - 4), by + self.r // 3,
                                                self.r * 2 + 8, 10), 0.2, 2.8, 1)
        if self.hp < self.max_hp:
            w = self.r * 2
            pygame.draw.rect(surf, (40, 0, 0), (self.x - self.r, by - self.r - 7, w, 3))
            pygame.draw.rect(surf, (60, 160, 220), (self.x - self.r, by - self.r - 7,
                                                    w * max(0, self.hp) / self.max_hp, 3))


# ---------------------------------------------------------------------------
# Quái vật vùng (ban đêm + lang thang)
# ---------------------------------------------------------------------------
REGION_MONSTERS = {
    "wizard": {
        "golem":   dict(name="Golem đá", r=14, hp=12, speed=28, dmg=14, color=(140, 130, 160)),
        "wisp":    dict(name="Hồn phép", r=8,  hp=4,  speed=70, dmg=6,  color=(180, 140, 255)),
        "mage":    dict(name="Pháp sư",  r=11, hp=8,  speed=45, dmg=10, color=(120, 90, 200)),
    },
    "volcano": {
        "magma":   dict(name="Quái magma", r=13, hp=10, speed=40, dmg=12, color=(240, 90, 30)),
        "ember":   dict(name="Than sống",  r=9,  hp=5,  speed=75, dmg=7,  color=(255, 160, 40)),
        "drake":   dict(name="Rồng magma", r=16, hp=18, speed=35, dmg=16, color=(200, 50, 20)),
    },
    "arctic": {
        "ice_wolf": dict(name="Sói tuyết", r=11, hp=7,  speed=80, dmg=9,  color=(200, 220, 240)),
        "frost":    dict(name="Quái băng", r=13, hp=11, speed=32, dmg=13, color=(140, 190, 230)),
        "ice_drake":dict(name="Rồng băng", r=16, hp=16, speed=38, dmg=15, color=(100, 170, 220)),
    },
    "spirit": {
        "specter": dict(name="Bóng ma",   r=10, hp=6,  speed=65, dmg=8,  color=(160, 80, 200)),
        "wraith":  dict(name="Oán linh",  r=12, hp=9,  speed=50, dmg=11, color=(90, 50, 130)),
        "reaper":  dict(name="Tử thần",   r=14, hp=14, speed=42, dmg=15, color=(60, 30, 80)),
    },
    "tropical": {
        "jaguar":  dict(name="Báo đốm",   r=12, hp=9,  speed=85, dmg=11, color=(200, 150, 40)),
        "anaconda":dict(name="Trăn khổng", r=14, hp=12, speed=40, dmg=13, color=(60, 120, 50)),
        "hornet":  dict(name="Ong khổng",  r=9,  hp=5,  speed=95, dmg=7,  color=(240, 200, 40)),
    },
    "rainforest": {
        "frog_tox": dict(name="Ếch độc",  r=10, hp=6,  speed=55, dmg=9,  color=(40, 180, 100)),
        "spider":   dict(name="Nhện rừng", r=13, hp=10, speed=50, dmg=12, color=(80, 50, 30)),
        "vine_beast": dict(name="Thú dây leo", r=15, hp=14, speed=35, dmg=14, color=(50, 100, 60)),
    },
}

# ---------------------------------------------------------------------------
# Động vật vùng
# ---------------------------------------------------------------------------
REGION_ANIMALS = {
    "wizard": {
        "fox_spirit": dict(name="Hồ ly",     r=9,  hp=4, speed=70, flee_speed=130, food=2, color=(200, 160, 220)),
        "deer_magic": dict(name="Nai phát sáng", r=11, hp=5, speed=50, flee_speed=110, food=3, color=(170, 200, 255)),
    },
    "volcano": {
        "lizard": dict(name="Thằn lằn lửa", r=10, hp=5, speed=55, flee_speed=100, food=3, color=(220, 100, 40)),
        "ash_bird": dict(name="Chim tro",  r=8,  hp=3, speed=90, flee_speed=140, food=2, color=(180, 120, 80)),
    },
    "arctic": {
        "seal": dict(name="Hải cẩu", r=12, hp=6, speed=30, flee_speed=70, food=4, color=(160, 180, 200)),
        "penguin": dict(name="Cánh cụt", r=8, hp=3, speed=25, flee_speed=55, food=2, color=(40, 40, 50)),
    },
    "spirit": {
        "ghost_cat": dict(name="Mèo hồn", r=8, hp=3, speed=60, flee_speed=120, food=1, color=(180, 160, 220)),
        "bone_deer": dict(name="Nai xương", r=11, hp=5, speed=40, flee_speed=90, food=2, color=(210, 200, 190)),
    },
    "tropical": {
        "parrot": dict(name="Vẹt", r=8, hp=3, speed=100, flee_speed=150, food=2, color=(255, 80, 80)),
        "monkey": dict(name="Khỉ", r=10, hp=5, speed=70, flee_speed=120, food=3, color=(160, 110, 60)),
    },
    "rainforest": {
        "tapir": dict(name="Heo vòi", r=12, hp=7, speed=35, flee_speed=70, food=4, color=(80, 70, 50)),
        "toucan": dict(name="Toucan", r=8, hp=3, speed=90, flee_speed=140, food=2, color=(30, 30, 30)),
    },
}

# ---------------------------------------------------------------------------
# Thực vật / node riêng (visual + tên)
# ---------------------------------------------------------------------------
REGION_PLANTS = {
    "wizard": {
        "glow_tree": dict(name="Cây phát sáng", node_color=(120, 100, 200), resource="mana", amount=4),
        "rune_bush": dict(name="Bụi rune",      node_color=(160, 150, 210), resource="runestone", amount=3),
    },
    "volcano": {
        "ash_tree":  dict(name="Cây tro",   node_color=(100, 60, 40), resource="sulfur", amount=4),
        "obs_rock":  dict(name="Đá obsidian", node_color=(40, 30, 45), resource="obsidian", amount=3),
    },
    "arctic": {
        "frost_tree": dict(name="Cây băng", node_color=(140, 180, 210), resource="ice_crystal", amount=4),
        "ice_shrub":  dict(name="Bụi tuyết", node_color=(180, 210, 230), resource="frozen_meat", amount=3),
    },
    "spirit": {
        "dead_tree": dict(name="Cây chết", node_color=(70, 60, 80), resource="bone", amount=4),
        "soul_flower": dict(name="Hoa hồn", node_color=(140, 70, 180), resource="soul_essence", amount=3),
    },
    "tropical": {
        "palm": dict(name="Cọ nhiệt đới", node_color=(40, 120, 50), resource="fruit", amount=5),
        "banana": dict(name="Chuối rừng", node_color=(200, 180, 40), resource="fruit", amount=4),
    },
    "rainforest": {
        "giant_tree": dict(name="Cây khổng lồ", node_color=(30, 90, 55), resource="wood", amount=8),
        "herb_bush": dict(name="Bụi thảo dược", node_color=(60, 160, 80), resource="herb", amount=4),
    },
}

# ---------------------------------------------------------------------------
# Tộc người từng vùng
# ---------------------------------------------------------------------------
REGION_TRIBES = {
    "wizard": dict(
        name="Tộc Pháp sư",
        color=(160, 130, 230),
        unit_kinds=("adept", "guardian"),
        max_units=5,
        desc="Cư dân vùng phép thuật, trung lập nhưng bảo vệ lãnh thổ.",
    ),
    "volcano": dict(
        name="Tộc Núi lửa",
        color=(230, 100, 50),
        unit_kinds=("ash_warrior", "flame_guard"),
        max_units=5,
        desc="Người sống gần dung nham, cứng rắn và nóng nảy.",
    ),
    "arctic": dict(
        name="Tộc Bắc cực",
        color=(150, 200, 240),
        unit_kinds=("hunter", "ice_guard"),
        max_units=5,
        desc="Thợ săn tuyết, quen chịu lạnh.",
    ),
    "spirit": dict(
        name="Tộc Linh hồn",
        color=(140, 90, 180),
        unit_kinds=("shade", "keeper"),
        max_units=5,
        desc="Những người gần với cõi chết, bí ẩn.",
    ),
    "tropical": dict(
        name="Tộc Rừng Nhiệt đới",
        color=(50, 160, 60),
        unit_kinds=("jungle_scout", "vine_guard"),
        max_units=5,
        desc="Thợ săn rừng rậm, nhanh nhẹn và khéo léo.",
    ),
    "rainforest": dict(
        name="Tộc Rừng Mưa",
        color=(40, 120, 90),
        unit_kinds=("rain_hunter", "moss_warden"),
        max_units=5,
        desc="Người sống dưới tán lá ẩm ướt, giỏi dùng độc và bẫy.",
    ),
}

TRIBE_UNITS = {
    "adept":       dict(name="Học việc",   r=10, hp=14, speed=60, dmg=6, range=85, color=(160, 130, 230), cooldown=1.0),
    "guardian":    dict(name="Hộ pháp",    r=12, hp=20, speed=50, dmg=9, range=70, color=(120, 90, 200), cooldown=1.1),
    "ash_warrior": dict(name="Chiến binh tro", r=11, hp=16, speed=55, dmg=8, range=60, color=(230, 100, 50), cooldown=0.9),
    "flame_guard": dict(name="Vệ binh lửa", r=12, hp=18, speed=48, dmg=10, range=75, color=(200, 70, 30), cooldown=1.0),
    "hunter":      dict(name="Thợ săn tuyết", r=10, hp=15, speed=70, dmg=7, range=95, color=(150, 200, 240), cooldown=0.85),
    "ice_guard":   dict(name="Vệ binh băng", r=12, hp=19, speed=45, dmg=9, range=70, color=(120, 180, 230), cooldown=1.05),
    "shade":       dict(name="Bóng người", r=10, hp=13, speed=65, dmg=7, range=80, color=(140, 90, 180), cooldown=0.95),
    "keeper":      dict(name="Người giữ mộ", r=12, hp=17, speed=48, dmg=8, range=65, color=(100, 60, 140), cooldown=1.1),
    "jungle_scout": dict(name="Trinh sát rừng", r=10, hp=14, speed=75, dmg=7, range=90, color=(50, 160, 60), cooldown=0.8),
    "vine_guard":  dict(name="Vệ binh dây leo", r=12, hp=18, speed=48, dmg=9, range=70, color=(40, 120, 50), cooldown=1.0),
    "rain_hunter": dict(name="Thợ săn mưa", r=10, hp=15, speed=68, dmg=8, range=95, color=(40, 120, 90), cooldown=0.85),
    "moss_warden": dict(name="Người rêu", r=12, hp=17, speed=45, dmg=9, range=65, color=(30, 90, 70), cooldown=1.05),
}


class RegionMonster:
    """Quái vật thuộc một vùng — tấn công player / unit gần."""
    def __init__(self, region, kind, x, y, day=1):
        d = REGION_MONSTERS[region][kind]
        self.region, self.kind = region, kind
        self.info = d
        self.x, self.y = x, y
        self.r = d["r"]
        self.hp = self.max_hp = float(d["hp"] + day * 0.4)
        self.speed = d["speed"]
        self.dmg = d["dmg"]
        self.color = d["color"]
        self.atk = 0.0
        self.angle = random.uniform(0, math.tau)
        self.alive = True

    def update(self, game, dt):
        if not self.alive or self.hp <= 0:
            self.alive = False
            return
        self.atk = max(0.0, self.atk - dt)
        # Mục tiêu: player > refugee > faction/tribe unit
        target = None
        best = 220
        for obj in [game.player] + list(game.refugees) + list(getattr(game, "faction_units", [])) + list(getattr(game, "tribe_units", [])):
            if getattr(obj, "hp", 0) <= 0:
                continue
            if hasattr(obj, "alive") and not obj.alive:
                continue
            d = dist(self.x, self.y, obj.x, obj.y)
            if d < best:
                best, target = d, obj
        if target is None:
            # Lang thang
            self.angle += random.uniform(-1, 1) * dt
            nx = self.x + math.cos(self.angle) * self.speed * 0.4 * dt
            ny = self.y + math.sin(self.angle) * self.speed * 0.4 * dt
            if not game.blocked(nx, ny, self.r):
                self.x, self.y = nx, ny
            return
        ang = math.atan2(target.y - self.y, target.x - self.x)
        self.angle = ang
        d = dist(self.x, self.y, target.x, target.y)
        if d < self.r + getattr(target, "r", getattr(target, "R", 12)) + 4:
            if self.atk <= 0:
                self.atk = 0.85
                if target is game.player and hasattr(target, "take_damage"):
                    target.take_damage(self.dmg, game.player_armor_reduction())
                else:
                    target.hp -= self.dmg
                    if hasattr(target, "hit_t"):
                        target.hit_t = 0.3
        else:
            nx = self.x + math.cos(ang) * self.speed * dt
            ny = self.y + math.sin(ang) * self.speed * dt
            b = game.buildings.get(tile_of(nx, ny))
            if b and not b.info.get("floor") and not b.info.get("gate"):
                if self.atk <= 0:
                    b.hp -= self.dmg
                    self.atk = 0.8
                    if b.hp <= 0 and b.kind != "core":
                        game.buildings.pop((b.c, b.r), None)
            elif not game.blocked(nx, ny, self.r):
                self.x, self.y = nx, ny

    def draw(self, surf):
        if not self.alive:
            return
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(surf, (20, 15, 25), (int(self.x), int(self.y)), self.r, 1)
        if self.hp < self.max_hp:
            w = self.r * 2
            pygame.draw.rect(surf, (50, 0, 0), (self.x - self.r, self.y - self.r - 6, w, 3))
            pygame.draw.rect(surf, (200, 50, 50), (self.x - self.r, self.y - self.r - 6,
                                                   w * max(0, self.hp) / self.max_hp, 3))


# Động vật hung dữ (tấn công player khi lại gần)
AGGRESSIVE_ANIMALS = {"lizard", "ash_bird", "ghost_cat", "monkey", "jaguar"}  # jaguar is monster

class RegionAnimal:
    """Động vật vùng — một số loài hung dữ có thể giết player."""
    def __init__(self, region, kind, x, y):
        d = REGION_ANIMALS[region][kind]
        self.region, self.kind = region, kind
        self.info = d
        self.x, self.y = x, y
        self.r = d["r"]
        self.hp = self.max_hp = float(d["hp"])
        self.color = d.get("color", (180, 160, 120))
        self.angle = random.uniform(0, math.tau)
        self.idle = random.uniform(0, 3)
        self.walk_t = 0.0
        self.flee_t = 0.0
        self.alive = True
        self.aggressive = kind in AGGRESSIVE_ANIMALS or d.get("aggressive", False)
        self.atk = 0.0
        self.dmg = d.get("dmg", 6 if self.aggressive else 0)

    def hurt(self, dmg, angle):
        self.hp -= dmg
        self.flee_t = 2.5 if not self.aggressive else 0.5
        self.angle = angle + random.uniform(-0.6, 0.6)
        if self.hp <= 0:
            self.alive = False

    def update(self, game, dt):
        if not self.alive:
            return
        self.atk = max(0.0, self.atk - dt)
        # Hung dữ: đuổi và cắn player
        if self.aggressive and game.player.hp > 0:
            d = dist(self.x, self.y, game.player.x, game.player.y)
            if d < 160:
                ang = math.atan2(game.player.y - self.y, game.player.x - self.x)
                self.angle = ang
                if d < self.r + game.player.R + 4:
                    if self.atk <= 0:
                        self.atk = 0.9
                        if hasattr(game.player, "take_damage"):
                            game.player.take_damage(self.dmg, game.player_armor_reduction())
                else:
                    sp = self.info["speed"] * 1.2 * game.season_animal_speed()
                    nx = self.x + math.cos(ang) * sp * dt
                    ny = self.y + math.sin(ang) * sp * dt
                    if not game.blocked(nx, self.y, self.r):
                        self.x = nx
                    if not game.blocked(self.x, ny, self.r):
                        self.y = ny
                return
        fleeing = self.flee_t > 0
        if fleeing:
            self.flee_t -= dt
        else:
            if self.idle > 0:
                self.idle -= dt
                return
            if self.walk_t <= 0:
                self.angle = random.uniform(0, math.tau)
                self.walk_t = random.uniform(1.5, 4.0)
            self.walk_t -= dt
            if self.walk_t <= 0:
                self.idle = random.uniform(1.5, 5.0)
                return
        base = self.info["flee_speed"] if fleeing else self.info["speed"]
        speed = base * game.season_animal_speed()
        nx = self.x + math.cos(self.angle) * speed * dt
        ny = self.y + math.sin(self.angle) * speed * dt
        if not game.blocked(nx, self.y, self.r):
            self.x = nx
        if not game.blocked(self.x, ny, self.r):
            self.y = ny

    def draw(self, surf):
        if not self.alive:
            return
        pygame.draw.ellipse(surf, self.color,
                            (int(self.x - self.r), int(self.y - self.r * 0.7),
                             self.r * 2, int(self.r * 1.4)))
        pygame.draw.circle(surf, (30, 25, 20), (int(self.x), int(self.y)), self.r, 1)


class TribeUnit:
    """Lính tộc người vùng — có kỹ năng tộc."""
    def __init__(self, region, kind, x, y):
        d = TRIBE_UNITS[kind]
        self.region, self.kind = region, kind
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
        self.angle = 0.0
        self.alive = True
        self.home_x, self.home_y = x, y
        self.patrol_angle = random.uniform(0, math.tau)
        # Áp kỹ năng tộc
        skills = TRIBE_SKILLS.get(region, {})
        self.skills = skills
        self.skill_armor = 0.0
        self.lifesteal = 0
        for sk in skills.values():
            self.dmg += sk.get("dmg_bonus", 0)
            self.speed *= sk.get("speed_mult", 1.0)
            self.hp += sk.get("hp_bonus", 0)
            self.max_hp += sk.get("hp_bonus", 0)
            self.skill_armor += sk.get("armor", 0)
            self.lifesteal += sk.get("lifesteal", 0)
            self.range = max(30, self.range - sk.get("evade_range", 0) * 0)  # keep range

    def update(self, game, dt):
        if not self.alive or self.hp <= 0:
            self.alive = False
            return
        self.cool = max(0.0, self.cool - dt)
        # Đánh quái / zombie gần
        enemy = None
        best = 200
        for z in list(game.zombies) + list(getattr(game, "region_monsters", [])):
            if getattr(z, "hp", 0) <= 0:
                continue
            d = dist(self.x, self.y, z.x, z.y)
            if d < best:
                best, enemy = d, z
        if enemy:
            ang = math.atan2(enemy.y - self.y, enemy.x - self.x)
            if best <= self.range:
                if self.cool <= 0:
                    self.cool = self.cooldown
                    dmg = self.dmg
                    # Chí mạng khi HP đầy (tropical ambush)
                    for sk in self.skills.values():
                        if sk.get("crit") and self.hp >= self.max_hp * 0.95:
                            dmg = int(dmg * (1 + sk["crit"]))
                    enemy.hp -= dmg
                    if self.lifesteal:
                        self.hp = min(self.max_hp, self.hp + self.lifesteal)
            else:
                nx = self.x + math.cos(ang) * self.speed * dt
                ny = self.y + math.sin(ang) * self.speed * dt
                if not game.blocked(nx, ny, self.r, pass_gates=True):
                    self.x, self.y = nx, ny
            return
        # Tuần tra quanh nhà
        d_home = dist(self.x, self.y, self.home_x, self.home_y)
        if d_home > 200:
            ang = math.atan2(self.home_y - self.y, self.home_x - self.x)
        else:
            self.patrol_angle += random.uniform(-1, 1) * dt
            ang = self.patrol_angle
        nx = self.x + math.cos(ang) * self.speed * 0.5 * dt
        ny = self.y + math.sin(ang) * self.speed * 0.5 * dt
        if not game.blocked(nx, ny, self.r, pass_gates=True):
            self.x, self.y = nx, ny

    def draw(self, surf):
        if not self.alive:
            return
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(surf, (255, 255, 255), (int(self.x), int(self.y)), self.r, 1)
        if self.hp < self.max_hp:
            w = self.r * 2
            pygame.draw.rect(surf, (40, 0, 0), (self.x - self.r, self.y - self.r - 6, w, 3))
            pygame.draw.rect(surf, (80, 200, 80), (self.x - self.r, self.y - self.r - 6,
                                                   w * max(0, self.hp) / self.max_hp, 3))


class RegionTribe:
    def __init__(self, region, base_c, base_r):
        d = REGION_TRIBES[region]
        self.region = region
        self.info = d
        self.name = d["name"]
        self.color = d["color"]
        self.base_c, self.base_r = base_c, base_r
        self.base_x, self.base_y = tile_center(base_c, base_r)
        self.max_units = d["max_units"]
        self.units = []

    def setup(self, game):
        # Dọn terrain quanh base
        for dr in range(-3, 4):
            for dc in range(-3, 4):
                nc, nr = self.base_c + dc, self.base_r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if game.terrain_map[nr][nc] in ("mountain", "river", "lake", "pond", "sea", "lava"):
                        game.terrain_map[nr][nc] = "none"
        # Vài tường
        from entities.building import Building
        for dc, dr in [(-2, -2), (0, -2), (2, -2), (-2, 2), (2, 2), (-2, 0), (2, 0)]:
            pos = (self.base_c + dc, self.base_r + dr)
            if pos not in game.buildings and 0 <= pos[0] < COLS and 0 <= pos[1] < ROWS:
                try:
                    game.buildings[pos] = Building("wall", pos[0], pos[1])
                except Exception:
                    pass
        # Unit
        kinds = self.info["unit_kinds"]
        for i in range(min(3, self.max_units)):
            kind = kinds[i % len(kinds)]
            ang = i * math.tau / 3
            x = self.base_x + math.cos(ang) * 40
            y = self.base_y + math.sin(ang) * 40
            u = TribeUnit(self.region, kind, x, y)
            u.home_x, u.home_y = self.base_x, self.base_y
            self.units.append(u)
            game.tribe_units.append(u)

    def update(self, game, dt):
        self.units = [u for u in self.units if u.alive and u.hp > 0]
        if len(self.units) < self.max_units and random.random() < 0.01 * dt * 60:
            kind = random.choice(self.info["unit_kinds"])
            ang = random.uniform(0, math.tau)
            u = TribeUnit(self.region, kind,
                          self.base_x + math.cos(ang) * 35,
                          self.base_y + math.sin(ang) * 35)
            u.home_x, u.home_y = self.base_x, self.base_y
            self.units.append(u)
            game.tribe_units.append(u)

    def draw_marker(self, surf):
        pygame.draw.circle(surf, self.color, (int(self.base_x), int(self.base_y)), 14, 2)
        pygame.draw.circle(surf, self.color, (int(self.base_x), int(self.base_y)), 5)


class RegionBoss:
    """Boss vùng với cơ chế phòng thủ riêng (lá chắn, giáp, đóng băng, phase, hồi máu, độc)."""
    def __init__(self, region, x, y, day=1):
        from settings import REGION_BOSSES
        d = REGION_BOSSES[region]
        self.region = region
        self.info = d
        self.name = d["name"]
        self.x, self.y = x, y
        self.r = d["r"]
        scale = 1.0 + day * 0.08
        self.hp = self.max_hp = float(d["hp"] * scale)
        self.speed = d["speed"]
        self.dmg = d["dmg"] * (1.0 + day * 0.03)
        self.color = d["color"]
        self.defense = d.get("defense", "armor")
        self.atk = 0.0
        self.angle = random.uniform(0, math.tau)
        self.alive = True
        self.spawn_cd = 0.0
        self.special_cd = 0.0
        self.phased = False
        self.phase_left = 0.0
        self.shield_hp = float(d.get("shield_hp", 0))
        self.max_shield = self.shield_hp
        self.armor = float(d.get("armor", 0))
        self.regen = float(d.get("regen", 0))
        self.freeze_chance = float(d.get("freeze_chance", 0))
        self.poison_dps = float(d.get("poison_dps", 0))
        self.add_count = int(d.get("spawn_adds", 2))
        self.reward = dict(d.get("reward", {}))
        self.pulse = 0.0

    def take_hit(self, dmg):
        if self.phased:
            return 0  # phase: miễn nhiễm
        if self.shield_hp > 0:
            absorbed = min(self.shield_hp, dmg)
            self.shield_hp -= absorbed
            dmg -= absorbed
            if dmg <= 0:
                return absorbed
        if self.armor > 0:
            dmg *= (1.0 - self.armor)
        self.hp -= dmg
        if self.hp <= 0:
            self.alive = False
        return dmg

    def update(self, game, dt):
        if not self.alive or self.hp <= 0:
            self.alive = False
            return
        self.atk = max(0.0, self.atk - dt)
        self.spawn_cd = max(0.0, self.spawn_cd - dt)
        self.special_cd = max(0.0, self.special_cd - dt)
        self.pulse += dt * 3
        if self.phased:
            self.phase_left -= dt
            if self.phase_left <= 0:
                self.phased = False
        # Hồi máu (regen)
        if self.regen > 0 and self.hp < self.max_hp:
            self.hp = min(self.max_hp, self.hp + self.regen * dt)
        # Hồi shield chậm
        if self.max_shield > 0 and self.shield_hp < self.max_shield:
            self.shield_hp = min(self.max_shield, self.shield_hp + 2.0 * dt)

        target = None
        best = 320
        for obj in [game.player] + list(game.refugees) + list(getattr(game, "faction_units", [])):
            if getattr(obj, "hp", 0) <= 0:
                continue
            if hasattr(obj, "alive") and not obj.alive:
                continue
            d = dist(self.x, self.y, obj.x, obj.y)
            if d < best:
                best, target = d, obj

        # Spawn adds khi máu thấp hoặc theo cd
        if self.spawn_cd <= 0 and (self.hp < self.max_hp * 0.6 or random.random() < 0.02):
            self.spawn_cd = 8.0
            self._spawn_adds(game)

        # Phase defense
        if self.defense == "phase" and self.special_cd <= 0 and self.hp < self.max_hp * 0.5:
            self.phased = True
            self.phase_left = 2.5
            self.special_cd = 6.0

        if target is None:
            self.angle += random.uniform(-0.8, 0.8) * dt
            nx = self.x + math.cos(self.angle) * self.speed * 0.3 * dt
            ny = self.y + math.sin(self.angle) * self.speed * 0.3 * dt
            if not game.blocked(nx, ny, self.r * 0.6):
                self.x, self.y = nx, ny
            return

        ang = math.atan2(target.y - self.y, target.x - self.x)
        self.angle = ang
        d = dist(self.x, self.y, target.x, target.y)
        if d < self.r + getattr(target, "r", getattr(target, "R", 12)) + 8:
            if self.atk <= 0:
                self.atk = 1.0
                dmg = self.dmg
                if target is game.player and hasattr(target, "take_damage"):
                    target.take_damage(dmg, game.player_armor_reduction())
                    # freeze
                    if self.freeze_chance > 0 and random.random() < self.freeze_chance:
                        target.hit_t = max(target.hit_t, 1.2)
                        game.say("Bạn bị đóng băng!", 1.5, "warn")
                    # poison
                    if self.poison_dps > 0:
                        if not hasattr(game, "player_poison"):
                            game.player_poison = 0.0
                        game.player_poison = max(game.player_poison, 3.5)
                        game.player_poison_dps = self.poison_dps
                else:
                    target.hp -= dmg
                    if hasattr(target, "hit_t"):
                        target.hit_t = 0.3
        else:
            nx = self.x + math.cos(ang) * self.speed * dt
            ny = self.y + math.sin(ang) * self.speed * dt
            b = game.buildings.get(tile_of(nx, ny))
            if b and not b.info.get("floor") and not b.info.get("gate"):
                if self.atk <= 0:
                    b.hp -= self.dmg * 1.5
                    self.atk = 0.7
                    if b.hp <= 0 and b.kind != "core":
                        game.buildings.pop((b.c, b.r), None)
            elif not game.blocked(nx, ny, self.r * 0.5):
                self.x, self.y = nx, ny

    def _spawn_adds(self, game):
        kinds = list(REGION_MONSTERS.get(self.region, {}).keys())
        if not kinds:
            return
        for _ in range(self.add_count):
            kind = random.choice(kinds)
            ang = random.uniform(0, math.tau)
            x = self.x + math.cos(ang) * (self.r + 30)
            y = self.y + math.sin(ang) * (self.r + 30)
            game.region_monsters.append(RegionMonster(self.region, kind, x, y, getattr(game, "day", 1)))
        game.say(f"{self.name} triệu hồi quái!", 2, "warn")

    def on_death(self, game):
        for k, v in self.reward.items():
            if k in game.res:
                got = game.add_res(k, v)
                if got:
                    game.popup(f"+{got} {k}", self.x, self.y - 20 - random.randint(0, 20), (255, 220, 100))
        game.say(f"Đã hạ {self.name}! Nhận thưởng vùng.", 5, "good")
        game.change_morale(8)

    def draw(self, surf):
        if not self.alive:
            return
        # Aura
        aura = 4 + int(3 * abs(math.sin(self.pulse)))
        col = self.color
        if self.phased:
            col = tuple(min(255, c + 80) for c in self.color)
            pygame.draw.circle(surf, (200, 200, 255), (int(self.x), int(self.y)), self.r + aura, 1)
        pygame.draw.circle(surf, col, (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(surf, (20, 10, 10), (int(self.x), int(self.y)), self.r, 2)
        # Crown
        pygame.draw.polygon(surf, (255, 215, 80), [
            (self.x - 8, self.y - self.r - 2),
            (self.x - 4, self.y - self.r - 12),
            (self.x, self.y - self.r - 4),
            (self.x + 4, self.y - self.r - 12),
            (self.x + 8, self.y - self.r - 2),
        ])
        # Shield bar
        if self.max_shield > 0 and self.shield_hp > 0:
            w = self.r * 2
            pygame.draw.rect(surf, (20, 40, 80), (self.x - self.r, self.y - self.r - 14, w, 3))
            pygame.draw.rect(surf, (80, 160, 255), (self.x - self.r, self.y - self.r - 14,
                                                    w * self.shield_hp / self.max_shield, 3))
        # HP
        w = self.r * 2
        pygame.draw.rect(surf, (50, 0, 0), (self.x - self.r, self.y - self.r - 8, w, 4))
        pygame.draw.rect(surf, (255, 60, 40), (self.x - self.r, self.y - self.r - 8,
                                               w * max(0, self.hp) / self.max_hp, 4))


# Tên lãnh đạo mẫu theo vùng
LEADER_NAMES = {
    "wizard": ("Archon Lyra", "Sage Voren"),
    "volcano": ("Thủ lĩnh Magra", "Lord Pyre"),
    "arctic": ("Jarl Frost", "Thủ lĩnh Băng"),
    "spirit": ("Hồn Chủ Nyx", "Keeper Umbra"),
    "tropical": ("Tù trưởng Kira", "Chúa rừng Tal"),
    "rainforest": ("Lãnh chúa Moss", "Elder Vine"),
}


class RegionLeader:
    """Lãnh đạo vùng: đàm phán, AI ưu tiên lợi ích vùng."""
    def __init__(self, region, x, y):
        self.region = region
        names = LEADER_NAMES.get(region, ("Lãnh đạo", "Thủ lĩnh"))
        self.name = random.choice(names)
        self.x, self.y = x, y
        self.home_x, self.home_y = x, y
        self.r = 14
        info = REGION_TRIBES.get(region, {})
        self.color = info.get("color", (180, 180, 100))
        self.hp = self.max_hp = 40.0
        self.alive = True
        # Quan hệ với player: -100..100
        self.relation = 0
        self.state = "neutral"  # neutral | peace | war
        # AI: kho tài nguyên vùng (ảo), ưu tiên
        self.stock = {"wood": 40, "stone": 30, "food": 35, "iron": 5, "fruit": 10, "herb": 8}
        self.ai_timer = random.uniform(20, 40)
        self.demand = None  # gì họ cần nhất
        self.angle = 0.0
        self.pulse = 0.0

    def update(self, game, dt):
        if not self.alive:
            return
        self.pulse += dt * 2
        self.ai_timer -= dt
        # Lang thang nhẹ quanh vị trí
        self.angle += random.uniform(-0.5, 0.5) * dt
        nx = self.x + math.cos(self.angle) * 12 * dt
        ny = self.y + math.sin(self.angle) * 12 * dt
        if not game.blocked(nx, ny, self.r * 0.5):
            # giữ gần điểm gốc
            cx, cy = self.home_x, self.home_y
            if dist(nx, ny, cx, cy) < 80:
                self.x, self.y = nx, ny
        if self.ai_timer <= 0:
            self.ai_timer = random.uniform(25, 50)
            self._ai_tick(game)

    def _ai_tick(self, game):
        """AI ưu tiên lợi ích vùng: cần tài nguyên thiếu, phản ứng quan hệ."""
        # Tìm tài nguyên thấp nhất trong kho
        low = min(self.stock, key=self.stock.get)
        self.demand = low
        # Nếu đang war: thỉnh thoảng gửi unit tấn công player nếu gần
        if self.state == "war":
            game.say(f"{self.name} ({BIOME_NAME(self.region)}): vùng ta sẽ không tha thứ!", 3, "warn")
            # Spawn 1-2 quái thù địch gần player nếu player trong vùng
            if game.biome_at_world(game.player.x, game.player.y) == self.region:
                for _ in range(2):
                    game.spawn_region_monster(self.region)
            self.relation = max(-100, self.relation - 5)
        elif self.state == "peace":
            # Tặng nhẹ nếu quan hệ tốt
            if self.relation > 40 and random.random() < 0.3:
                gift_key = max(self.stock, key=self.stock.get)
                if self.stock[gift_key] > 10:
                    amt = 3
                    self.stock[gift_key] -= amt
                    if gift_key in game.res:
                        game.add_res(gift_key, amt)
                        game.say(f"{self.name} tặng bạn {amt} {gift_key} (hòa bình).", 3, "good")
        else:
            # Neutral: nếu player cướp (giết quái/boss) trong vùng → giảm quan hệ nhẹ
            pass
        # Tự tích lũy kho
        for k in self.stock:
            self.stock[k] = min(80, self.stock[k] + random.randint(0, 3))

    def set_peace(self, game):
        self.state = "peace"
        self.relation = max(self.relation, 30)
        game.say(f"Hòa bình với {self.name} — {self._region_name()}!", 4, "good")

    def set_war(self, game):
        self.state = "war"
        self.relation = min(self.relation, -40)
        game.say(f"Chiến tranh với {self.name} — {self._region_name()}!", 4, "warn")

    def set_neutral(self, game):
        self.state = "neutral"
        game.say(f"Trung lập với {self.name}.", 3)

    def trade(self, game, offer):
        """Thực hiện trao đổi nếu player đủ give và quan hệ không quá thù."""
        if self.state == "war":
            game.say(f"{self.name}: Đang chiến tranh, không buôn bán!", 2, "warn")
            return False
        if self.relation < -50:
            game.say(f"{self.name}: Quan hệ quá xấu, từ chối!", 2, "warn")
            return False
        for k, v in offer["give"].items():
            if game.res.get(k, 0) < v:
                game.say("Bạn không đủ tài nguyên để trao đổi!", 2, "warn")
                return False
        # Lãnh đạo cần có get trong stock (hoặc cho phép nếu peace)
        for k, v in offer["get"].items():
            if self.stock.get(k, 0) < v and self.state != "peace":
                game.say(f"{self.name}: Vùng ta thiếu {k}, không đổi được.", 2, "warn")
                return False
        for k, v in offer["give"].items():
            game.res[k] -= v
            self.stock[k] = self.stock.get(k, 0) + v
        for k, v in offer["get"].items():
            self.stock[k] = max(0, self.stock.get(k, 0) - v)
            if k in game.res:
                game.add_res(k, v)
            else:
                game.res[k] = game.res.get(k, 0) + v
        self.relation = min(100, self.relation + 8)
        game.say(f"Đã trao đổi với {self.name}: {offer['label']}", 3, "good")
        return True

    def trade_refugee(self, game, direction):
        """direction='give' player đưa 1 refugee; 'get' nhận 1 nếu có chỗ."""
        if self.state == "war":
            game.say(f"{self.name}: Không trao đổi người khi đang chiến!", 2, "warn")
            return False
        if direction == "give":
            if not game.refugees:
                game.say("Không còn người tị nạn để đưa!", 2, "warn")
                return False
            r = game.refugees.pop()
            r.alive = False
            self.relation = min(100, self.relation + 12)
            game.say(f"Đã đưa {r.name} cho {self.name}. Quan hệ +12.", 3, "good")
            return True
        else:
            home = game.free_house()
            if home is None:
                game.say("Hết chỗ ở — xây thêm nhà!", 2, "warn")
                return False
            from entities.refugee import Refugee, NAMES
            name = random.choice(NAMES)
            x, y = game.player.x + random.uniform(-20, 20), game.player.y + random.uniform(-20, 20)
            ref = Refugee(x, y, name=name)
            ref.home = home
            ref.state = "settled"
            game.refugees.append(ref)
            self.relation = max(-100, self.relation - 5)
            game.say(f"{self.name} gửi {name} đến căn cứ bạn.", 3, "good")
            return True

    def _region_name(self):
        from settings import BIOMES
        return BIOMES.get(self.region, {}).get("name", self.region)

    def draw(self, surf):
        if not self.alive:
            return
        # Vầng sáng lãnh đạo
        pygame.draw.circle(surf, self.color, (int(self.x), int(self.y)), self.r + 3, 2)
        pygame.draw.circle(surf, (240, 220, 160), (int(self.x), int(self.y)), self.r)
        pygame.draw.circle(surf, (40, 30, 20), (int(self.x), int(self.y)), self.r, 2)
        # Vương miện nhỏ
        pygame.draw.polygon(surf, (255, 200, 50), [
            (self.x - 6, self.y - self.r - 1),
            (self.x - 3, self.y - self.r - 8),
            (self.x, self.y - self.r - 2),
            (self.x + 3, self.y - self.r - 8),
            (self.x + 6, self.y - self.r - 1),
        ])
        # Màu quan hệ
        if self.state == "war":
            ring = (220, 50, 50)
        elif self.state == "peace":
            ring = (80, 200, 100)
        else:
            ring = (200, 200, 120)
        pygame.draw.circle(surf, ring, (int(self.x), int(self.y)), self.r + 6, 1)


def BIOME_NAME(region):
    from settings import BIOMES
    return BIOMES.get(region, {}).get("name", region)


# Kỹ năng đặc trưng mỗi tộc (áp dụng cho TribeUnit khi update)
TRIBE_SKILLS = {
    "wizard": {
        "arcane_bolt": dict(name="Tên lửa phép", desc="Đạn phép thêm +4 sát thương", dmg_bonus=4),
        "mana_shield": dict(name="Khiên mana", desc="Giảm 20% sát thương nhận", armor=0.20),
    },
    "volcano": {
        "flame_strike": dict(name="Đòn lửa", desc="Sát thương +5, đốt nhẹ", dmg_bonus=5),
        "heat_resist": dict(name="Chịu nhiệt", desc="Miễn hiệu ứng nóng vùng", armor=0.15),
    },
    "arctic": {
        "frost_arrow": dict(name="Mũi tên băng", desc="Làm chậm mục tiêu", dmg_bonus=3, slow=0.3),
        "cold_blood": dict(name="Máu lạnh", desc="HP +8", hp_bonus=8),
    },
    "spirit": {
        "shadow_step": dict(name="Bước bóng", desc="Tốc độ +15%", speed_mult=1.15),
        "drain": dict(name="Hút hồn", desc="Hút 2 HP mỗi đòn", lifesteal=2),
    },
    "tropical": {
        "ambush": dict(name="Phục kích", desc="Sát thương chí mạng +25% khi HP đầy", crit=0.25),
        "swift": dict(name="Nhanh nhẹn", desc="Tốc độ +20%", speed_mult=1.20),
    },
    "rainforest": {
        "poison_tip": dict(name="Tẩm độc", desc="Độc 3 dmg/s trong 2s", poison=3),
        "camouflage": dict(name="Ngụy trang", desc="Khó bị nhắm hơn (tầm địch -20)", evade_range=20),
    },
}
