from entities.faction import FACTIONS
"""Viên đạn (của người chơi, tháp súng, xạ thủ, thợ săn)."""
import math

import pygame

from settings import W, H


class Bullet:
    def __init__(self, x, y, angle, dmg, speed=620, color=(255, 226, 122), hits_animals=False,
                 life=1.0, pierce=0):
        self.x, self.y, self.dmg, self.life, self.color = x, y, dmg, life, color
        self.angle = angle
        self.hits_animals = hits_animals   # chỉ đạn của người chơi / thợ săn mới trúng động vật
        self.pierce = pierce               # số zombie có thể xuyên qua thêm (súng trường)
        self.hit = set()                   # zombie đã bị xuyên (không trúng lại)
        self.vx, self.vy = math.cos(angle) * speed, math.sin(angle) * speed

    @property
    def alive(self):
        return self.life > 0 and 0 <= self.x <= W and 0 <= self.y <= H

    def update(self, game, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        for z in game.zombies:
            if z.hp > 0 and id(z) not in self.hit and math.hypot(self.x - z.x, self.y - z.y) < z.r + 3:
                z.hp -= self.dmg
                if self.pierce > 0:
                    self.pierce -= 1
                    self.hit.add(id(z))
                else:
                    self.life = 0
                break
        if self.life > 0 and self.hits_animals:
            for a in game.animals:
                if a.alive and math.hypot(self.x - a.x, self.y - a.y) < a.r + 3:
                    a.hurt(self.dmg, self.angle)
                    self.life = 0
                    break
        # Bắn unit phe (ảnh hưởng quan hệ)
        if self.life > 0 and self.hits_animals and hasattr(game, "faction_units"):
            for u in game.faction_units:
                if u.alive and u.hp > 0 and math.hypot(self.x - u.x, self.y - u.y) < u.r + 3:
                    u.hp -= self.dmg
                    game.change_player_relation(u.faction_id, -5)
                    if u.hp <= 0:
                        u.alive = False
                        game.say(f"Bạn đã hạ 1 {u.info['name']} ({FACTIONS[u.faction_id]['name']})!", 2, "warn")
                    self.life = 0
                    break
        # Quái vùng
        if self.life > 0 and hasattr(game, "region_monsters"):
            for m in game.region_monsters:
                if m.alive and m.hp > 0 and math.hypot(self.x - m.x, self.y - m.y) < m.r + 3:
                    m.hp -= self.dmg
                    if m.hp <= 0:
                        m.alive = False
                    self.life = 0
                    break
        # Thủy quái
        if self.life > 0 and hasattr(game, "sea_monsters"):
            for m in game.sea_monsters:
                if m.alive and m.hp > 0 and math.hypot(self.x - m.x, self.y - m.y) < m.r + 3:
                    m.hp -= self.dmg
                    if m.hp <= 0:
                        m.alive = False
                        game.popup(f"+{m.info.get('name', 'Thủy quái')}", m.x, m.y - 16, (80, 180, 255))
                    self.life = 0
                    break
        # Boss vùng
        if self.life > 0 and hasattr(game, "region_bosses"):
            for b in game.region_bosses:
                if b.alive and b.hp > 0 and math.hypot(self.x - b.x, self.y - b.y) < b.r + 4:
                    b.take_hit(self.dmg)
                    self.life = 0
                    break
        # Thú vùng
        if self.life > 0 and self.hits_animals and hasattr(game, "region_animals"):
            for a in game.region_animals:
                if a.alive and math.hypot(self.x - a.x, self.y - a.y) < a.r + 3:
                    a.hurt(self.dmg, self.angle)
                    self.life = 0
                    break
        # Tộc vùng (trung lập — bắn sẽ làm họ thù, đơn giản chỉ damage)
        if self.life > 0 and self.hits_animals and hasattr(game, "tribe_units"):
            for u in game.tribe_units:
                if u.alive and u.hp > 0 and math.hypot(self.x - u.x, self.y - u.y) < u.r + 3:
                    u.hp -= self.dmg
                    if u.hp <= 0:
                        u.alive = False
                    self.life = 0
                    break

    def draw(self, surf):
        pygame.draw.circle(surf, self.color, (self.x, self.y), 3)
