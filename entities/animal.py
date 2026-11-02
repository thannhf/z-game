"""Động vật hiền lành (bò). Thêm loài mới = thêm mục vào ANIMALS.

Khi bị hạ, động vật cho `food` lương thực (xem Game.cleanup). Zombie không quan tâm tới chúng.
"""
import math
import random

import pygame


ANIMALS = {
    "cow":   dict(name="Bò",   r=11, hp=4, speed=26, flee_speed=85, food=4),
    "horse": dict(name="Ngựa", r=12, hp=6, speed=55, flee_speed=120, food=3),
    "dog":   dict(name="Chó",  r=8,  hp=3, speed=48, flee_speed=100, food=2),
}


class Animal:
    def __init__(self, kind, x, y):
        self.kind, self.x, self.y = kind, x, y
        self.info = ANIMALS[kind]
        self.r = self.info["r"]
        self.hp = self.max_hp = float(self.info["hp"])
        self.angle = random.uniform(0, 6.283)
        self.face = 1 if math.cos(self.angle) >= 0 else -1
        self.idle = random.uniform(0, 3)     # đang đứng gặm cỏ
        self.walk_t = 0.0                    # thời gian còn lại của chặng đi hiện tại
        self.flee_t = 0.0                    # đang hoảng sợ chạy

    @property
    def alive(self):
        return self.hp > 0

    def hurt(self, dmg, angle):
        """Trúng đạn bay theo hướng `angle`: bỏ chạy theo hướng đó (xa người bắn)."""
        self.hp -= dmg
        self.flee_t = 2.5
        self.angle = angle + random.uniform(-0.6, 0.6)

    def update(self, game, dt):
        fleeing = self.flee_t > 0
        if fleeing:
            self.flee_t -= dt
        else:
            if self.idle > 0:
                self.idle -= dt
                return
            if self.walk_t <= 0:             # bắt đầu một chặng đi mới
                self.angle = random.uniform(0, 6.283)
                self.walk_t = random.uniform(1.5, 4.0)
            self.walk_t -= dt
            if self.walk_t <= 0:
                self.idle = random.uniform(1.5, 5.0)
                return
        base = self.info["flee_speed"] if fleeing else self.info["speed"]
        speed = base * game.season_animal_speed()
        nx = self.x + math.cos(self.angle) * speed * dt
        ny = self.y + math.sin(self.angle) * speed * dt
        moved = False
        if not game.blocked(nx, self.y, self.r):
            self.x, moved = nx, True
        if not game.blocked(self.x, ny, self.r):
            self.y, moved = ny, True
        if math.cos(self.angle) > 0.1:
            self.face = 1
        elif math.cos(self.angle) < -0.1:
            self.face = -1
        if not moved:                        # vướng vật cản -> đổi hướng
            if fleeing:
                self.angle += random.choice((-1.57, 1.57))
            else:
                self.walk_t = 0.0

    def draw(self, surf):
        x, y, d = int(self.x), int(self.y), self.face
        if self.kind == "horse":
            body = pygame.Rect(0, 0, 30, 16)
            body.center = (x, y)
            pygame.draw.ellipse(surf, (50, 35, 25), body.inflate(3, 3))
            pygame.draw.ellipse(surf, (160, 110, 70), body)
            for lx in (-10, -3, 5, 12):
                pygame.draw.line(surf, (40, 30, 20), (x + lx, y + 7), (x + lx, y + 13), 2)
            hx = x + d * 16
            pygame.draw.circle(surf, (140, 95, 60), (hx, y - 3), 7)
            pygame.draw.circle(surf, (20, 20, 20), (hx + d, y - 5), 1)
            pygame.draw.line(surf, (50, 35, 20), (hx - d * 4, y - 8), (hx - d * 6, y - 14), 2)  # bờm
        elif self.kind == "dog":
            body = pygame.Rect(0, 0, 20, 12)
            body.center = (x, y)
            pygame.draw.ellipse(surf, (40, 30, 25), body.inflate(2, 2))
            pygame.draw.ellipse(surf, (180, 140, 90), body)
            for lx in (-6, -1, 4, 8):
                pygame.draw.line(surf, (50, 40, 30), (x + lx, y + 5), (x + lx, y + 9), 2)
            hx = x + d * 11
            pygame.draw.circle(surf, (170, 130, 85), (hx, y - 1), 5)
            pygame.draw.circle(surf, (20, 20, 20), (hx + d, y - 2), 1)
            # tai
            pygame.draw.polygon(surf, (140, 100, 60), [(hx - 2, y - 4), (hx - 5, y - 9), (hx + 1, y - 5)])
        else:  # cow
            body = pygame.Rect(0, 0, 26, 17)
            body.center = (x, y)
            pygame.draw.ellipse(surf, (40, 30, 30), body.inflate(3, 3))
            pygame.draw.ellipse(surf, (242, 242, 236), body)
            pygame.draw.circle(surf, (70, 56, 52), (x - 5 * d, y - 2), 4)
            pygame.draw.circle(surf, (70, 56, 52), (x + 2 * d, y + 3), 3)
            for lx in (-8, -3, 4, 9):
                pygame.draw.line(surf, (40, 30, 30), (x + lx, y + 8), (x + lx, y + 12), 2)
            hx = x + d * 14
            pygame.draw.circle(surf, (40, 30, 30), (hx, y - 2), 7)
            pygame.draw.circle(surf, (235, 210, 200), (hx, y - 2), 6)
            pygame.draw.circle(surf, (230, 150, 150), (hx + d * 3, y), 3)
            pygame.draw.circle(surf, (20, 20, 20), (hx + d, y - 4), 1)
            pygame.draw.line(surf, (200, 190, 150), (hx - d * 2, y - 8), (hx - d * 3, y - 11), 2)
        if self.hp < self.max_hp:
            pygame.draw.rect(surf, (60, 0, 0), (x - 12, y - 18, 24, 3))
            pygame.draw.rect(surf, (80, 220, 80), (x - 12, y - 18, 24 * max(0, self.hp) / self.max_hp, 3))
