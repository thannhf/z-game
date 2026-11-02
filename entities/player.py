"""Người chơi: di chuyển, bắn súng, xây dựng, khai thác."""
import math
import random

import pygame

from settings import TILE, COLS, ROWS, W, H, RESOURCES, BUILD_RANGE, TERRAIN
from utils import tile_of, tile_center, dist
from entities.bullet import Bullet
from entities.building import Building, BUILDINGS, harvest_farm
from entities.weapons import WEAPONS, WEAPON_ORDER, WEAPON_BASE, weapon_stats, UPGRADE_COST


class Player:
    R = 12
    SPEED = 190

    def __init__(self):
        self.x, self.y = W / 2, H / 2 + 60
        self.hp = self.max_hp = 100.0
        self.hit_t = 0.0
        self.cool = 0.0
        self.tool = "gun"
        self.alt = False       # đang giữ Shift (chọn phương án nâng cấp thứ 2)
        self.weapon = "pistol"
        self.owned = {"pistol": 1}   # kind -> level (1..5)
        self.was_down, self.buf = False, 0.0   # súng bắn từng phát: nhớ cú bấm chuột
        self.mounted = None    # Vehicle đang lái, hoặc "horse" khi cưỡi ngựa
        self.mount_horse = None  # Animal horse reference

    # ----- cập nhật -----
    def update(self, game, dt, keys, mouse_pos, mouse_down):
        self.hit_t -= dt
        self.cool -= dt
        self.alt = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        if dx or dy:
            tmult = game.terrain_speed_mult(self.x, self.y) if hasattr(game, "terrain_speed_mult") else 1.0
            mount_mult = 1.0
            air = False
            if self.mounted == "horse":
                mount_mult = 1.85
            elif self.mounted is not None and hasattr(self.mounted, "speed"):
                mount_mult = max(0.5, self.mounted.speed / self.SPEED)
                air = bool(getattr(self.mounted, "air", False))
                if air:
                    tmult = 1.0
            sp = self.SPEED * game.player_speed_bonus() * tmult * mount_mult * dt / math.hypot(dx, dy)
            if air:
                self.x = max(self.R, min(W - self.R, self.x + dx * sp))
                self.y = max(self.R, min(H - self.R, self.y + dy * sp))
            else:
                if not game.blocked(self.x + dx * sp, self.y, self.R, True):
                    self.x += dx * sp
                if not game.blocked(self.x, self.y + dy * sp, self.R, True):
                    self.y += dy * sp
            if self.mounted not in (None, "horse") and hasattr(self.mounted, "x"):
                self.mounted.x, self.mounted.y = self.x, self.y
                self.mounted.angle = math.atan2(dy, dx)
            if self.mounted == "horse" and self.mount_horse:
                self.mount_horse.x, self.mount_horse.y = self.x, self.y
        if mouse_down and not self.was_down:
            self.buf = 0.18
        self.was_down = mouse_down
        self.buf -= dt
        if mouse_down and self.cool <= 0 and self.mounted in (None, "horse"):
            self.use_tool(game, *mouse_pos)
        elif mouse_down and self.cool <= 0 and self.mounted not in (None, "horse"):
            # Khi lái xe vẫn bắn được súng
            if self.tool == "gun":
                self.use_tool(game, *mouse_pos)

    def try_mount(self, game):
        """F: lên/xuống ngựa hoặc phương tiện gần."""
        if self.mounted == "horse":
            if self.mount_horse:
                self.mount_horse.x, self.mount_horse.y = self.x + 20, self.y
            self.mounted = None
            self.mount_horse = None
            game.say("Xuống ngựa.", 1.5)
            return
        if self.mounted is not None:
            self.mounted.dismount(self)
            game.say("Xuống xe.", 1.5)
            return
        # Tìm xe gần
        best_v, best_d = None, 40
        for v in getattr(game, "vehicles", []):
            if v.alive and v.driver is None:
                d = dist(self.x, self.y, v.x, v.y)
                if d < best_d:
                    best_v, best_d = v, d
        if best_v:
            best_v.mount(self)
            game.say(f"Lên {best_v.info['name']} (F để xuống).", 2, "good")
            return
        for a in game.animals:
            if a.kind == "horse" and a.alive and dist(self.x, self.y, a.x, a.y) < 36:
                self.mounted = "horse"
                self.mount_horse = a
                game.say("Cưỡi ngựa! (F để xuống)", 2, "good")
                return
        game.say("Không có ngựa/xe gần đây.", 1.5)

    # ----- vũ khí -----
    def cycle_weapon(self, game):
        """Đổi sang khẩu súng kế tiếp đang sở hữu (phím Q)."""
        have = [k for k in WEAPON_ORDER if k in self.owned]
        if not have:
            return
        self.weapon = have[(have.index(self.weapon) + 1) % len(have)] if self.weapon in have else have[0]
        self.tool = "gun"
        game.say(f"Đang dùng: {self.current_weapon()['name']}", 1.5)

    def buy_weapon(self, game, key):
        """Mua vũ khí mới hoặc nâng cấp cấp nếu đã có. Trả về True nếu thành công."""
        if key in self.owned:
            lvl = self.owned[key]
            if lvl >= 5:
                self.weapon, self.tool = key, "gun"
                game.say(f"{WEAPON_BASE[key]['name']} đã đạt cấp tối đa!", 1.5)
                return True
            cost = UPGRADE_COST.get(lvl, {})
            if not game.can_afford(cost):
                game.say("Không đủ vật liệu để nâng cấp súng!", 2, "warn")
                return False
            for k, v in cost.items():
                game.res[k] -= v
            self.owned[key] = lvl + 1
            self.weapon, self.tool = key, "gun"
            game.say(f"Nâng cấp {WEAPON_BASE[key]['name']} lên cấp {lvl + 1}!", 3, "good")
            return True
        w = WEAPON_BASE[key]
        if not game.can_afford(w["cost"]):
            game.say("Không đủ vật liệu để mua!", 2, "warn")
            return False
        for k, v in w["cost"].items():
            game.res[k] -= v
        self.owned[key] = 1
        self.weapon, self.tool = key, "gun"
        game.say(f"Đã mua {w['name']}!", 3, "good")
        return True

    def current_weapon(self):
        """Stats súng đang dùng (đã áp cấp)."""
        lvl = self.owned.get(self.weapon, 1)
        return weapon_stats(self.weapon, lvl)

    def take_damage(self, dmg, armor_reduction=0.0):
        if self.hit_t <= 0:
            self.hp -= dmg * (1.0 - armor_reduction)
            self.hit_t = 0.7

    # ----- công cụ -----
    def use_tool(self, game, mx, my):
        c, r = tile_of(mx, my)
        if self.tool == "gun":
            w = self.current_weapon()
            if not w["auto"]:                    # súng bắn từng phát: phải bấm mới ra đạn
                if self.buf <= 0:
                    return
                self.buf = 0
            base = math.atan2(my - self.y, mx - self.x)
            for _ in range(w["pellets"]):
                ang = base + random.uniform(-w["spread"], w["spread"])
                game.bullets.append(Bullet(self.x, self.y, ang, w["dmg"], speed=w["speed"], hits_animals=True,
                                           life=w["life"] * random.uniform(0.85, 1.0) if w["pellets"] > 1 else w["life"],
                                           pierce=w["pierce"]))
            self.cool = w["rate"]
        elif self.tool in BUILDINGS:
            err = self.build_error(game, self.tool, c, r, mx, my)
            if err is None:
                self.build(game, self.tool, c, r)
            elif err:
                game.say(err, 1)
        elif self.tool == "upgrade":
            b = game.buildings.get((c, r))
            opts = b.info.get("upgrades", []) if b else []
            if not opts:
                if b:
                    game.say("Công trình này không nâng cấp được.", 1)
                    self.cool = 0.3
                return
            idx = 1 if self.alt and len(opts) > 1 else 0
            err = self.upgrade_error(game, opts[idx], mx, my)
            if err is None:
                self.upgrade(game, b, opts[idx])
            else:
                game.say(err, 1)
                self.cool = 0.3
        elif self.tool == "gather":
            if dist(self.x, self.y, mx, my) > BUILD_RANGE:
                return
            node, b = game.nodes.get((c, r)), game.buildings.get((c, r))
            if node:
                if game.is_full(node.kind):
                    game.say(f"Kho {RESOURCES[node.kind]['name'].lower()} đã đầy - hãy xây thêm kho!", 1.5)
                    self.cool = 0.5
                else:
                    game.add_res(node.harvest(), 1)
                    if node.depleted:
                        del game.nodes[(c, r)]
                    self.cool = 0.18
            elif b and b.kind == "farm" and b.progress >= 1.0:
                if harvest_farm(b, game):
                    self.cool = 0.3
                else:
                    game.say("Kho lương thực đã đầy - hãy xây thêm kho!", 1.5)
                    self.cool = 0.5

    def build_error(self, game, tool, c, r, mx, my):
        """None = xây được; chuỗi rỗng = bỏ qua im lặng; chuỗi khác = thông báo lỗi."""
        info = BUILDINGS[tool]
        if not (0 <= c < COLS and 0 <= r < ROWS) or (c, r) in game.buildings:
            return ""
        terr = game.get_terrain(c, r) if hasattr(game, "get_terrain") else "none"
        tinfo = TERRAIN.get(terr, {})
        if tinfo.get("block") or not tinfo.get("buildable", True):
            return f"Không xây được trên {tinfo.get('name', 'địa hình này')}!"
        if dist(self.x, self.y, mx, my) > BUILD_RANGE:
            return "Quá xa!"
        node, need = game.nodes.get((c, r)), info.get("on_node")
        if need:
            if node is None or node.kind != need:
                return f"Phải xây trên ô {RESOURCES[need]['name'].lower()}!"
        elif node:
            return ""
        tx, ty = tile_center(c, r)
        if dist(self.x, self.y, tx, ty) < TILE:
            return "Bạn đang đứng ở ô này!"
        if game.unit_in_tile(c, r):
            return "Có người hoặc zombie ở ô này!"
        if not game.can_afford(info["cost"]):
            return "Không đủ vật liệu!"
        return None

    def upgrade_error(self, game, new_kind, mx, my):
        """None = nâng cấp được; chuỗi = lý do không được."""
        if dist(self.x, self.y, mx, my) > BUILD_RANGE:
            return "Quá xa!"
        if not game.can_afford(BUILDINGS[new_kind]["cost"]):
            return "Không đủ vật liệu!"
        return None

    def upgrade(self, game, old, new_kind):
        """Thay công trình tại chỗ bằng bản nâng cấp (giữ nguyên tỉ lệ máu)."""
        info = BUILDINGS[new_kind]
        for k, v in info["cost"].items():
            game.res[k] -= v
        nb = Building(new_kind, old.c, old.r)
        nb.hp = nb.max * old.hp / old.max
        nb.spent = dict(old.spent)
        for k, v in info["cost"].items():
            nb.spent[k] = nb.spent.get(k, 0) + v
        # giữ worker / cows / horses / dogs / progress
        nb.worker = old.worker
        if old.worker:
            old.worker.job = nb
        for attr in ("cows", "horses", "dogs", "progress", "breed", "timer"):
            if hasattr(old, attr):
                setattr(nb, attr, getattr(old, attr))
        game.buildings[(old.c, old.r)] = nb
        # cập nhật home của người tị nạn
        for r in game.refugees:
            if r.home is old:
                r.home = nb
        game.say(f"Đã nâng cấp thành {info['name']}!", 2)
        self.cool = 0.3

    def build(self, game, tool, c, r):
        for k, v in BUILDINGS[tool]["cost"].items():
            game.res[k] -= v
        game.nodes.pop((c, r), None)
        game.buildings[(c, r)] = Building(tool, c, r)
        if tool in ("rail", "floor") and hasattr(game, "invalidate_terrain_cache"):
            if tool == "rail":
                game.terrain_map[r][c] = "rail"
            game.invalidate_terrain_cache()
        self.cool = 0.12

    def demolish(self, game, mx, my):
        b = game.buildings.get(tile_of(mx, my))
        if b and b.kind != "core" and dist(self.x, self.y, mx, my) <= BUILD_RANGE:
            for k, v in b.spent.items():
                game.add_res(k, v // 2)
            del game.buildings[(b.c, b.r)]

    # ----- vẽ -----
    def draw(self, surf, mouse_pos):
        ang = math.atan2(mouse_pos[1] - self.y, mouse_pos[0] - self.x)
        pygame.draw.line(surf, (30, 30, 30), (self.x, self.y),
                         (self.x + math.cos(ang) * 22, self.y + math.sin(ang) * 22), 5)
        col = (74, 163, 224) if self.hit_t <= 0 else (230, 120, 110)
        pygame.draw.circle(surf, col, (self.x, self.y), self.R)
