"""Phương tiện: xe máy, ô tô, xe bọc thép, xe tăng, trực thăng, máy bay + cưỡi ngựa."""
import math
import random

import pygame

from settings import TILE, W, H
from utils import dist, tile_of

VEHICLES = {
    "motorcycle": dict(name="Xe máy", r=10, hp=40, speed=320, armor=0.05, cost={"iron": 4, "copper": 2},
                       color=(80, 80, 90), air=False, build_time=18),
    "car":        dict(name="Ô tô", r=14, hp=70, speed=260, armor=0.12, cost={"iron": 8, "copper": 3, "wood": 6},
                       color=(40, 90, 160), air=False, build_time=28),
    "apc":        dict(name="Xe bọc thép", r=16, hp=140, speed=180, armor=0.35, cost={"iron": 16, "copper": 6, "stone": 8},
                       color=(70, 90, 50), air=False, build_time=40),
    "tank":       dict(name="Xe tăng", r=18, hp=220, speed=120, armor=0.55, cost={"iron": 28, "copper": 10, "gold": 2},
                       color=(60, 80, 40), air=False, build_time=55, dmg=25, range=160),
    "heli":       dict(name="Trực thăng", r=15, hp=100, speed=300, armor=0.15, cost={"iron": 14, "copper": 8, "silver": 2},
                       color=(90, 100, 110), air=True, build_time=48),
    "plane":      dict(name="Máy bay", r=16, hp=90, speed=380, armor=0.1, cost={"iron": 18, "copper": 10, "gold": 3},
                       color=(180, 190, 200), air=True, build_time=60, dmg=18, range=200),
}


class Vehicle:
    def __init__(self, kind, x, y):
        d = VEHICLES[kind]
        self.kind = kind
        self.info = d
        self.x, self.y = x, y
        self.r = d["r"]
        self.hp = self.max_hp = float(d["hp"])
        self.speed = d["speed"]
        self.armor = d["armor"]
        self.color = d["color"]
        self.air = d.get("air", False)
        self.angle = 0.0
        self.driver = None  # player reference when mounted
        self.alive = True
        self.cool = 0.0
        self.blade = 0.0  # heli rotor

    def mount(self, player):
        if self.driver is not None or not self.alive:
            return False
        self.driver = player
        player.mounted = self
        return True

    def dismount(self, player):
        if self.driver is player:
            self.driver = None
            player.mounted = None
            # đặt player cạnh xe
            player.x = self.x + 24
            player.y = self.y

    def update(self, game, dt):
        if not self.alive or self.hp <= 0:
            self.alive = False
            if self.driver:
                self.dismount(self.driver)
            return
        self.cool = max(0.0, self.cool - dt)
        self.blade += dt * 12
        if self.driver is game.player:
            # di chuyển theo input player (đã xử lý trong player.update khi mounted)
            pass
        # Tank/plane auto-fire nearest zombie
        if self.driver and self.info.get("dmg") and self.cool <= 0:
            targets = [z for z in game.zombies if z.hp > 0]
            targets += [m for m in getattr(game, "region_monsters", []) if m.alive]
            if targets:
                t = min(targets, key=lambda o: dist(self.x, self.y, o.x, o.y))
                if dist(self.x, self.y, t.x, t.y) <= self.info.get("range", 150):
                    from entities.bullet import Bullet
                    ang = math.atan2(t.y - self.y, t.x - self.x)
                    game.bullets.append(Bullet(self.x, self.y, ang, self.info["dmg"],
                                               speed=500, color=(255, 180, 60), hits_animals=True))
                    self.cool = 0.7

    def draw(self, surf):
        if not self.alive:
            return
        x, y = int(self.x), int(self.y)
        if self.kind == "motorcycle":
            pygame.draw.ellipse(surf, self.color, (x - 12, y - 6, 24, 12))
            pygame.draw.circle(surf, (30, 30, 30), (x - 8, y + 4), 4)
            pygame.draw.circle(surf, (30, 30, 30), (x + 8, y + 4), 4)
        elif self.kind == "car":
            pygame.draw.rect(surf, self.color, (x - 14, y - 8, 28, 16), border_radius=3)
            pygame.draw.rect(surf, (180, 210, 230), (x - 8, y - 6, 10, 6))
        elif self.kind == "apc":
            pygame.draw.rect(surf, self.color, (x - 16, y - 10, 32, 20), border_radius=2)
            pygame.draw.rect(surf, (40, 50, 30), (x - 6, y - 14, 12, 6))
        elif self.kind == "tank":
            pygame.draw.rect(surf, self.color, (x - 18, y - 10, 36, 20), border_radius=2)
            pygame.draw.rect(surf, (50, 60, 35), (x - 4, y - 8, 22, 5))  # nòng
            pygame.draw.circle(surf, (70, 85, 45), (x, y), 8)
        elif self.kind == "heli":
            pygame.draw.ellipse(surf, self.color, (x - 14, y - 6, 28, 14))
            # rotor
            a = self.blade
            pygame.draw.line(surf, (200, 200, 200),
                             (x + int(math.cos(a) * 18), y + int(math.sin(a) * 4)),
                             (x - int(math.cos(a) * 18), y - int(math.sin(a) * 4)), 2)
        elif self.kind == "plane":
            pygame.draw.polygon(surf, self.color, [(x + 18, y), (x - 14, y - 8), (x - 14, y + 8)])
            pygame.draw.line(surf, (150, 150, 160), (x - 4, y - 14), (x - 4, y + 14), 3)
        # driver indicator
        if self.driver:
            pygame.draw.circle(surf, (100, 220, 255), (x, y - self.r - 6), 3)
        if self.hp < self.max_hp:
            w = self.r * 2
            pygame.draw.rect(surf, (40, 0, 0), (x - self.r, y - self.r - 10, w, 3))
            pygame.draw.rect(surf, (80, 200, 80), (x - self.r, y - self.r - 10,
                                                   w * max(0, self.hp) / self.max_hp, 3))
