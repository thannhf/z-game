"""Zombie. Thêm loại mới = thêm mục vào ZOMBIES rồi cho nó vào bảng trọng số trong Game.pick_zombie.

Khóa tùy chọn:
  explode        (radius, dmg): tự nổ khi chạm công trình/người -> phá tường cả cụm
  hunts_refugees tầm (pixel) tự đuổi người tị nạn đang thức; refugee_mult = nhân sát thương lên họ
  boss           True: thanh máu lớn, triệu hồi đàn zombie chạy khi còn nửa máu
  hp_scale       máu cộng thêm mỗi ngày (mặc định 1/3)
Đường đi: zombie đi theo bản đồ chi phí của pathfinding.zombie_field (ưu tiên lối hở / cổng),
chỉ đâm thẳng vào mục tiêu khi người chơi / người tị nạn ở gần.
"""
import math
import random

import pygame

from settings import TILE
from pathfinding import zombie_step
from utils import tile_of, dist, nearest

ZOMBIES = {
    "normal": dict(name="Zombie", r=11, hp=2, speed=45, dmg=8, color=(106, 154, 42)),
    "big":    dict(name="Zombie to", r=17, hp=7, speed=32, dmg=18, color=(74, 110, 26)),
    # chạy nhanh nhưng mỏng máu
    "runner": dict(name="Zombie chạy", r=9, hp=1, speed=92, dmg=6, color=(196, 206, 70)),
    # tự nổ: chạm tường là nổ, phá cả cụm công trình xung quanh
    "bomber": dict(name="Zombie bom", r=12, hp=2, speed=52, dmg=0, color=(224, 128, 40),
                   explode=dict(radius=TILE * 2.0, dmg=130, fuse=0.7)),
    # cắn người tị nạn: ưu tiên dân đang thức, cắn đau gấp đôi
    "biter":  dict(name="Zombie cắn", r=10, hp=3, speed=64, dmg=9, color=(156, 70, 140),
                   hunts_refugees=320, refugee_mult=2.0),
    # boss (mỗi 5 đêm)
    "boss":   dict(name="BOSS", r=26, hp=40, speed=26, dmg=30, color=(120, 28, 28),
                   boss=True, hp_scale=3.0),
}


class Zombie:
    def __init__(self, kind, x, y, day, region=None):
        d = ZOMBIES[kind]
        self.kind, self.x, self.y = kind, x, y
        self.info = d
        self.r = d["r"]
        self.hp = self.max_hp = d["hp"] + int(day * d.get("hp_scale", 1 / 3))
        self.speed = min(d["speed"] * 1.8, d["speed"] + day * 2 + random.uniform(0, 15))
        self.dmg, self.atk, self.angle = d["dmg"], 0.0, 0.0
        self.slow_t = 0.0
        self.color = d["color"]
        self.fuse = None          # zombie bom: đếm ngược trước khi nổ
        self.summoned = False     # boss: đã triệu hồi chưa
        self.region = region      # None = tấn công lõi; "wizard"/... = zombie vùng

    # ----- chọn hướng -----
    def pick_target(self, game):
        """Trả về (x, y) mục tiêu đâm thẳng tới, hoặc None = đi theo bản đồ đường tới lõi."""
        p = game.player
        # Zombie vùng: ưu tiên player/unit/phe trong vùng, rồi điểm trung tâm vùng
        if self.region:
            if dist(p.x, p.y, self.x, self.y) < 280:
                return p.x, p.y
            # Unit phe gần
            if hasattr(game, "faction_units"):
                fu = nearest([u for u in game.faction_units if u.alive], self.x, self.y)
                if fu and dist(fu.x, fu.y, self.x, self.y) < 260:
                    return fu.x, fu.y
            awake = [r for r in game.refugees if r.alive and not r.sleeping]
            ref = nearest(awake, self.x, self.y)
            if ref and dist(ref.x, ref.y, self.x, self.y) < 220:
                return ref.x, ref.y
            # Điểm trung tâm vùng
            center = getattr(game, "biome_centers", {}).get(self.region)
            if center:
                return center
            return None
        # Zombie lõi (cũ)
        if dist(p.x, p.y, self.x, self.y) < 150:
            return p.x, p.y
        awake = [r for r in game.refugees if r.alive and not r.sleeping]
        ref = nearest(awake, self.x, self.y)
        reach = self.info.get("hunts_refugees", 110)
        if ref and dist(ref.x, ref.y, self.x, self.y) < reach:
            return ref.x, ref.y
        return None

    def update(self, game, dt):
        self.atk -= dt
        if self.info.get("boss"):
            self.boss_logic(game)
        target = self.pick_target(game)
        if target is None:
            if self.region:
                # Không có mục tiêu: lang thang nhẹ trong vùng
                tx = self.x + math.cos(self.angle + 0.3) * 40
                ty = self.y + math.sin(self.angle + 0.3) * 40
            else:
                tx, ty = zombie_step(game, game.get_field(), self.x, self.y)
        else:
            tx, ty = target
        self.angle = math.atan2(ty - self.y, tx - self.x)
        self.slow_t = max(0.0, self.slow_t - dt)
        spd = self.speed * game.season_zombie_speed()
        if self.slow_t > 0:
            spd *= 0.45
        nx = self.x + math.cos(self.angle) * spd * dt
        ny = self.y + math.sin(self.angle) * spd * dt
        b = game.buildings.get(tile_of(nx, ny))
        if b:  # bị công trình chặn -> phá nó (zombie bom thì châm ngòi)
            if self.info.get("explode"):
                if self.fuse is None:
                    self.fuse = self.info["explode"]["fuse"]
            elif self.atk <= 0:
                b.hp -= self.dmg * (2 if self.info.get("boss") else 1)
                self.atk = 0.8
                if b.hp <= 0 and b.kind != "core":
                    game.buildings.pop((b.c, b.r), None)
        else:
            self.x, self.y = nx, ny

        p = game.player
        if dist(p.x, p.y, self.x, self.y) < self.r + p.R:
            if self.info.get("explode"):
                if self.fuse is None:
                    self.fuse = self.info["explode"]["fuse"]
            else:
                p.take_damage(self.dmg, game.player_armor_reduction())
        if self.fuse is not None:
            self.fuse -= dt
            if self.fuse <= 0:
                self.explode(game)
                return
        for r in game.refugees:
            if r.alive and not r.sleeping and dist(r.x, r.y, self.x, self.y) < self.r + r.R:
                if self.info.get("explode"):
                    if self.fuse is None:
                        self.fuse = self.info["explode"]["fuse"]
                elif self.atk <= 0:
                    r.hp -= self.dmg * self.info.get("refugee_mult", 1.0)
                    self.atk = 0.8
                break
        # Tấn công unit phe
        if hasattr(game, "faction_units") and self.atk <= 0:
            for u in game.faction_units:
                if u.alive and u.hp > 0 and dist(u.x, u.y, self.x, self.y) < self.r + u.r + 4:
                    if self.info.get("explode"):
                        if self.fuse is None:
                            self.fuse = self.info["explode"]["fuse"]
                    else:
                        u.hp -= self.dmg
                        self.atk = 0.8
                    break

    # ----- kỹ năng đặc biệt -----
    def explode(self, game):
        """Nổ: gây sát thương lên mọi công trình, người chơi và dân trong bán kính."""
        e = self.info["explode"]
        self.hp = 0
        game.effects.append(dict(x=self.x, y=self.y, r=e["radius"], life=0.45, max=0.45))
        for b in list(game.buildings.values()):
            if dist(b.x, b.y, self.x, self.y) <= e["radius"] + TILE * 0.5:
                b.hp -= e["dmg"] * (0.5 if b.kind == "core" else 1.0)
                if b.hp <= 0 and b.kind != "core":
                    game.buildings.pop((b.c, b.r), None)
        p = game.player
        if dist(p.x, p.y, self.x, self.y) <= e["radius"]:
            p.hp -= 25
        for r in game.refugees:
            if r.alive and dist(r.x, r.y, self.x, self.y) <= e["radius"]:
                r.hp -= 20

    def boss_logic(self, game):
        if not self.summoned and self.hp <= self.max_hp / 2:
            self.summoned = True
            game.say("BOSS gầm lên - đàn zombie chạy lao tới!", 4, "warn")
            for i in range(5):
                a = i * 6.283 / 5
                game.zombies.append(Zombie("runner", self.x + math.cos(a) * 40,
                                           self.y + math.sin(a) * 40, game.day))

    # ----- vẽ -----
    def draw(self, surf):
        col = self.color
        if self.fuse is not None and int(self.fuse * 10) % 2 == 0:
            col = (255, 240, 200)           # nhấp nháy sắp nổ
        pygame.draw.circle(surf, col, (self.x, self.y), self.r)
        ex = self.x + math.cos(self.angle) * self.r * 0.5
        ey = self.y + math.sin(self.angle) * self.r * 0.5
        pygame.draw.circle(surf, (224, 58, 42), (ex, ey), 3)
        if self.kind == "bomber":           # bình thuốc nổ trên lưng
            pygame.draw.circle(surf, (60, 40, 30), (self.x, self.y - 3), 5)
            pygame.draw.line(surf, (255, 220, 120), (self.x, self.y - 8), (self.x + 3, self.y - 12), 2)
        elif self.kind == "biter":          # răng
            for k in (-3, 0, 3):
                pygame.draw.line(surf, (245, 245, 235), (self.x + k, self.y + self.r - 5),
                                 (self.x + k, self.y + self.r - 1), 2)
        elif self.kind == "boss":
            pygame.draw.circle(surf, (40, 8, 8), (self.x, self.y), self.r, 3)
            for k in (-10, 0, 10):          # vương miện
                pygame.draw.line(surf, (240, 200, 70), (self.x + k, self.y - self.r - 6),
                                 (self.x + k, self.y - self.r + 2), 4)
        if self.kind != "boss" and self.hp < self.max_hp and self.r >= 12:
            w = self.r * 2
            pygame.draw.rect(surf, (60, 0, 0), (self.x - self.r, self.y - self.r - 7, w, 3))
            pygame.draw.rect(surf, (220, 80, 60),
                             (self.x - self.r, self.y - self.r - 7, w * max(0, self.hp) / self.max_hp, 3))
