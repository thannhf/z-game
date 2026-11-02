"""Công trình. Thêm công trình mới = thêm một mục vào BUILDINGS.

Khóa tùy chọn:
  behavior   tên hành vi trong BEHAVIORS (turret, producer, ...)
  on_node    chỉ xây được trên ô tài nguyên loại này (ví dụ mỏ đá xây trên ô đá)
  store / store_amount   kho: tăng sức chứa của tài nguyên `store` thêm `store_amount`
  upgrades   danh sách công trình có thể nâng cấp lên (công cụ Nâng cấp; mục thứ 2 = Shift+Click)
  upgrade_only   chỉ có được bằng nâng cấp (cost là giá nâng cấp)
  gate   người chơi và người tị nạn đi xuyên qua được, zombie thì không
  interact   "shop" / "trainer" / "market": đứng gần bấm E để mở bảng giao dịch tương ứng
  pen_cap, start_cows, breed_time, meat_time   chuồng bò (xem pen_behavior)
  KHÔNG dùng khóa "capacity" cho thứ khác nhà ở: housing_capacity() cộng mọi `capacity`.
"""
import math
import random

import pygame

from settings import TILE, RESOURCES
from utils import tile_center, dist, nearest
from entities.bullet import Bullet

BUILDINGS = {
    "core":   dict(name="Lõi căn cứ", cost={}, hp=400, color=(230, 200, 80)),
    "wall":   dict(name="Hàng rào gỗ", cost={"wood": 4}, hp=120, color=(150, 110, 70),
                   upgrades=["stone_wall"]),
    "stone_wall": dict(name="Hàng rào đá", cost={"stone": 6}, hp=320, color=(140, 140, 152),
                       upgrade_only=True, upgrades=["iron_wall"]),
    "iron_wall": dict(name="Hàng rào sắt", cost={"iron": 8, "stone": 4}, hp=550, color=(100, 110, 125),
                      upgrade_only=True),
    "gate":   dict(name="Cổng gỗ", cost={"wood": 10}, hp=150, color=(185, 140, 80), gate=True,
                   upgrades=["iron_gate"]),
    "iron_gate": dict(name="Cổng sắt", cost={"iron": 10, "stone": 6}, hp=400, color=(110, 120, 135),
                      gate=True, upgrade_only=True),
    "turret": dict(name="Tháp súng", cost={"wood": 8, "stone": 6}, hp=80, color=(90, 140, 200),
                   behavior="turret", range=200, rate=0.55, dmg=1,
                   upgrades=["turret_rapid", "turret_long"]),
    "turret_rapid": dict(name="Tháp bắn nhanh", cost={"wood": 6, "stone": 8}, hp=100, color=(90, 190, 210),
                         behavior="turret", range=200, rate=0.26, dmg=1, upgrade_only=True,
                         upgrades=["turret_minigun"]),
    "turret_long":  dict(name="Tháp tầm xa", cost={"wood": 6, "stone": 10}, hp=100, color=(130, 110, 210),
                         behavior="turret", range=330, rate=0.5, dmg=1, upgrade_only=True,
                         upgrades=["turret_sniper"]),
    "turret_minigun": dict(name="Tháp minigun", cost={"iron": 10, "copper": 8}, hp=130, color=(70, 160, 180),
                           behavior="turret", range=210, rate=0.12, dmg=1, upgrade_only=True),
    "turret_sniper": dict(name="Tháp bắn tỉa", cost={"iron": 8, "copper": 6, "silver": 2}, hp=120,
                          color=(150, 100, 200), behavior="turret", range=420, rate=0.7, dmg=3, upgrade_only=True),
    "turret_flame": dict(name="Tháp lửa", cost={"wood": 10, "stone": 8, "copper": 4}, hp=110, color=(220, 100, 50),
                         behavior="turret", range=160, rate=0.35, dmg=2),
    "turret_shock": dict(name="Tháp điện", cost={"iron": 6, "copper": 10, "stone": 6}, hp=100, color=(80, 180, 255),
                         behavior="turret", range=180, rate=0.45, dmg=2),
    "quarry": dict(name="Mỏ đá", cost={"wood": 12, "stone": 4}, hp=100, color=(120, 120, 135),
                   behavior="producer", on_node="stone", produces="stone",
                   interval=10.0, worked_interval=3.0),
    "sawmill": dict(name="Nhà máy gỗ", cost={"wood": 10, "stone": 4}, hp=100, color=(110, 140, 85),
                    behavior="producer", on_node="wood", produces="wood",
                    interval=10.0, worked_interval=3.0),
    "house":  dict(name="Nhà cấp 1", cost={"wood": 10}, hp=80, color=(190, 120, 90),
                   behavior="house", capacity=2, upgrades=["house_2"]),
    "house_2": dict(name="Nhà cấp 2", cost={"wood": 12, "stone": 6}, hp=110, color=(185, 125, 95),
                    behavior="house", capacity=3, upgrade_only=True, upgrades=["house_3"]),
    "house_3": dict(name="Nhà cấp 3", cost={"wood": 14, "stone": 10, "copper": 2}, hp=140, color=(180, 130, 100),
                    behavior="house", capacity=4, upgrade_only=True, upgrades=["house_4"]),
    "house_4": dict(name="Nhà cấp 4", cost={"wood": 16, "stone": 12, "iron": 4}, hp=180, color=(175, 135, 105),
                    behavior="house", capacity=5, upgrade_only=True, upgrades=["house_5"]),
    "house_5": dict(name="Nhà cấp 5", cost={"wood": 20, "stone": 15, "iron": 6, "silver": 2}, hp=230,
                    color=(170, 140, 110), behavior="house", capacity=6, upgrade_only=True),
    # Nông trại: khoai tây tự lớn; chín rồi thì nông dân (hoặc bạn, dùng công cụ Khai thác) thu hoạch.
    "farm":   dict(name="farm", cost={"wood": 12}, hp=60, color=(120, 90, 55),
                   behavior="farm", produces="food", yield_=4,
                   grow_time=26.0, worked_grow_time=10.0),
    "wood_store":  dict(name="wood", cost={"wood": 14}, hp=120, color=(150, 105, 60),
                        behavior="storage", store="wood", store_amount=60),
    "stone_store": dict(name="storage stone", cost={"wood": 12, "stone": 6}, hp=140, color=(135, 135, 150),
                        behavior="storage", store="stone", store_amount=60),
    "food_store":  dict(name="storage food", cost={"wood": 14}, hp=100, color=(205, 150, 70),
                        behavior="storage", store="food", store_amount=50),
    "armory":  dict(name="Xưởng vũ khí", cost={"wood": 15, "stone": 10}, hp=120, color=(110, 100, 95),
                    interact="shop"),
    "trainer": dict(name="Nhà huấn luyện", cost={"wood": 15, "stone": 12}, hp=120, color=(125, 95, 150),
                    interact="trainer"),
    "market":  dict(name="Chợ", cost={"wood": 20, "stone": 8}, hp=100, color=(205, 165, 70),
                    interact="market"),
    # Chuồng bò: bò giống tự sinh sản, cho thịt đều (không cần săn). Cost có 6 lương thực mua bò giống.
    "pen":     dict(name="Chuồng bò", cost={"wood": 16, "food": 6}, hp=90, color=(165, 135, 95),
                    behavior="pen", pen_cap=4, start_cows=2, breed_time=45.0, meat_time=30.0),
    # Mỏ kim loại: xây trên ô quặng tương ứng
    "copper_mine": dict(name="Mỏ đồng", cost={"wood": 14, "stone": 8}, hp=110, color=(180, 120, 60),
                        behavior="producer", on_node="copper", produces="copper",
                        interval=14.0, worked_interval=4.5),
    "iron_mine": dict(name="Mỏ sắt", cost={"wood": 16, "stone": 10, "copper": 2}, hp=120, color=(140, 145, 155),
                      behavior="producer", on_node="iron", produces="iron",
                      interval=16.0, worked_interval=5.0),
    "silver_mine": dict(name="Mỏ bạc", cost={"wood": 18, "stone": 12, "iron": 3}, hp=130, color=(190, 200, 215),
                        behavior="producer", on_node="silver", produces="silver",
                        interval=20.0, worked_interval=6.0),
    "gold_mine": dict(name="Mỏ vàng", cost={"wood": 20, "stone": 14, "silver": 2}, hp=140, color=(220, 180, 50),
                      behavior="producer", on_node="gold", produces="gold",
                      interval=24.0, worked_interval=7.0),
    # Kho kim loại
    "copper_store": dict(name="Kho đồng", cost={"wood": 12, "stone": 6}, hp=110, color=(170, 110, 55),
                         behavior="storage", store="copper", store_amount=40),
    "iron_store": dict(name="Kho sắt", cost={"wood": 14, "stone": 8}, hp=120, color=(130, 135, 145),
                       behavior="storage", store="iron", store_amount=35),
    "silver_store": dict(name="Kho bạc", cost={"wood": 16, "stone": 8, "copper": 2}, hp=120, color=(180, 190, 205),
                         behavior="storage", store="silver", store_amount=25),
    "gold_store": dict(name="Kho vàng", cost={"wood": 18, "stone": 10, "iron": 2}, hp=130, color=(210, 170, 45),
                       behavior="storage", store="gold", store_amount=20),
    # Nhà nghiên cứu: nghiên cứu kỹ năng / sinh học / giáp
    "research": dict(name="Nhà nghiên cứu", cost={"wood": 20, "stone": 16, "copper": 4}, hp=140, color=(90, 130, 160),
                     interact="research"),
    # Chuồng ngựa: ngựa tăng tốc độ di chuyển căn cứ (bonus tốc độ cho người chơi gần)
    "stable": dict(name="Chuồng ngựa", cost={"wood": 18, "food": 8, "copper": 2}, hp=100, color=(150, 120, 80),
                   behavior="stable", pen_cap=3, start_horses=1, breed_time=60.0),
    # Chuồng chó: chó cảnh báo / hỗ trợ chiến đấu nhẹ
    "kennel": dict(name="Chuồng chó", cost={"wood": 14, "food": 6}, hp=90, color=(140, 110, 90),
                   behavior="kennel", pen_cap=4, start_dogs=2, breed_time=40.0, bark_time=8.0),
    # Đá lát sàn: đi xuyên qua được, ngăn cây/quặng mọc
    "floor":  dict(name="Đá lát sàn", cost={"stone": 2}, hp=40, color=(130, 130, 140), floor=True),
    # Nhà máy phương tiện
    "factory_motor": dict(name="Xưởng xe máy", cost={"wood": 20, "iron": 8, "copper": 4}, hp=160,
                          color=(90, 95, 100), behavior="vehicle_factory", vehicle="motorcycle"),
    "factory_car": dict(name="Nhà máy ô tô", cost={"wood": 24, "iron": 12, "copper": 6}, hp=180,
                        color=(50, 90, 140), behavior="vehicle_factory", vehicle="car"),
    "factory_apc": dict(name="Xưởng bọc thép", cost={"stone": 20, "iron": 18, "copper": 8}, hp=200,
                        color=(70, 85, 50), behavior="vehicle_factory", vehicle="apc"),
    "factory_tank": dict(name="Nhà máy tăng", cost={"stone": 28, "iron": 30, "copper": 12, "gold": 2}, hp=240,
                         color=(55, 70, 40), behavior="vehicle_factory", vehicle="tank"),
    "factory_heli": dict(name="Xưởng trực thăng", cost={"wood": 16, "iron": 20, "copper": 12, "silver": 3}, hp=200,
                         color=(85, 95, 105), behavior="vehicle_factory", vehicle="heli"),
    "factory_plane": dict(name="Nhà máy máy bay", cost={"iron": 24, "copper": 14, "gold": 4, "silver": 4}, hp=220,
                          color=(160, 170, 180), behavior="vehicle_factory", vehicle="plane"),
    # Ga tàu
    "station": dict(name="Ga tàu", cost={"wood": 20, "stone": 24, "iron": 10}, hp=200,
                    color=(120, 90, 60), behavior="station", interact="station"),
    # Ray tàu (lát sàn dạng đường sắt)
    "rail": dict(name="Ray tàu", cost={"iron": 2, "stone": 1}, hp=50, color=(70, 65, 60), floor=True),
}


# ----- hành vi (mỗi hàm nhận: công trình, game, dt) -----
def turret_behavior(b, game, dt):
    b.cool -= dt
    if b.cool > 0 or not game.zombies:
        return
    t = nearest(game.zombies, b.x, b.y)
    if dist(t.x, t.y, b.x, b.y) <= b.info["range"]:
        ang = math.atan2(t.y - b.y, t.x - b.x)
        game.bullets.append(Bullet(b.x, b.y, ang, b.info["dmg"]))
        b.cool = b.info["rate"]


def worker_near(b):
    """Người làm việc của công trình có đang đứng cạnh nó (và thức) không?"""
    w = b.worker
    return (w is not None and w.alive and not w.sleeping
            and dist(w.x, w.y, b.x, b.y) < TILE * 1.7)


def producer_behavior(b, game, dt):
    """Tự sản xuất tài nguyên; có thợ mỏ làm việc thì nhanh hơn. Kho đầy thì dừng chờ.
    Áp dụng hệ số mùa (produce_mult) và nghiên cứu mine_eff cho mỏ kim loại."""
    b.working = worker_near(b)
    mult = game.season_produce_mult()
    metals = ("copper", "iron", "silver", "gold")
    if b.info.get("produces") in metals and "mine_eff" in getattr(game, "researched", set()):
        mult *= 1.25
    if b.working:
        b.worker.add_xp(game, dt * 0.8)
        b.timer += dt * b.worker.work_mult(game) * mult
    else:
        b.timer += dt * mult
    interval = b.info["worked_interval"] if b.working else b.info["interval"]
    if b.timer >= interval:
        kind = b.info["produces"]
        if game.add_res(kind, 1):
            b.timer = 0.0
            game.popup(f"+1 {RESOURCES[kind]['name']}", b.x, b.y - 18, RESOURCES[kind]["color"])
        else:
            b.timer = interval   # kho đầy: giữ nguyên, có chỗ là ra ngay


def harvest_farm(b, game):
    """Thu hoạch nếu cây đã chín và kho còn chỗ. Trả về True nếu thu được.
    Mùa có thể cộng/trừ yield."""
    if b.progress < 1.0:
        return False
    kind = b.info["produces"]
    amount = max(1, b.info["yield_"] + game.season_food_yield())
    got = game.add_res(kind, amount)
    if not got:
        return False
    b.progress = 0.0
    game.popup(f"+{got} {RESOURCES[kind]['name']}", b.x, b.y - 18, RESOURCES[kind]["color"])
    return True


def farm_behavior(b, game, dt):
    """Cây lớn dần; có nông dân đứng cạnh thì lớn nhanh hơn và được thu hoạch ngay khi chín.
    Hệ số mùa (grow_mult) ảnh hưởng tốc độ lớn."""
    b.working = worker_near(b)
    if b.working:
        b.worker.add_xp(game, dt * 0.8)
    if b.progress < 1.0:
        t = b.info["worked_grow_time"] if b.working else b.info["grow_time"]
        mult = (b.worker.work_mult(game) if b.working else 1.0) * game.season_grow_mult()
        b.progress = min(1.0, b.progress + dt * mult / t)
    elif b.working:
        harvest_farm(b, game)


def storage_behavior(b, game, dt):
    """Kho: chỉ ghi lại độ đầy của tài nguyên tương ứng để vẽ. Sức chứa tính ở Game.cap()."""
    kind = b.info["store"]
    b.fill = game.res[kind] / max(1, game.cap(kind))


def house_behavior(b, game, dt):
    """Đếm số cư dân đang ngủ trong nhà (để vẽ cửa sổ sáng đèn)."""
    b.sleepers = sum(1 for r in game.refugees if r.home is b and r.sleeping)


def pen_behavior(b, game, dt):
    """Chuồng bò: có từ 2 con trở lên thì bò sinh sản (tới sức chứa); mỗi con cho thịt đều đặn.
    Thịt cộng thẳng vào lương thực (kho đầy thì chờ)."""
    cap = b.info["pen_cap"]
    if b.cows >= 2 and b.cows < cap:
        b.breed += dt
        if b.breed >= b.info["breed_time"]:
            b.breed = 0.0
            b.cows += 1
            game.popup("Bê con!", b.x, b.y - 18, (255, 220, 220))
            game.say("Chuồng bò có bê con mới.", 2.5)
    if b.cows >= 1:
        b.timer += dt
        need = b.info["meat_time"] / b.cows          # càng đông bò thịt càng nhiều
        if b.timer >= need:
            if game.add_res("food", 1):
                b.timer = 0.0
                game.popup("+1 Lương thực", b.x, b.y - 18, RESOURCES["food"]["color"])
            else:
                b.timer = need                       # kho đầy: chờ chỗ trống


def stable_behavior(b, game, dt):
    """Chuồng ngựa: sinh sản ngựa (tới sức chứa). Ngựa trong chuồng tăng tốc độ người chơi gần."""
    cap = b.info["pen_cap"]
    if b.horses >= 1 and b.horses < cap:
        b.breed += dt
        if b.breed >= b.info["breed_time"]:
            b.breed = 0.0
            b.horses += 1
            game.popup("Ngựa con!", b.x, b.y - 18, (220, 200, 160))
            game.say("Chuồng ngựa có ngựa con mới.", 2.5)


def kennel_behavior(b, game, dt):
    """Chuồng chó: sinh sản; thỉnh thoảng sủa làm chậm zombie gần."""
    cap = b.info["pen_cap"]
    if b.dogs >= 1 and b.dogs < cap:
        b.breed += dt
        if b.breed >= b.info["breed_time"]:
            b.breed = 0.0
            b.dogs += 1
            game.popup("Cún con!", b.x, b.y - 18, (200, 180, 150))
            game.say("Chuồng chó có cún mới.", 2.5)
    if b.dogs >= 1:
        b.timer += dt
        if b.timer >= b.info["bark_time"]:
            b.timer = 0.0
            for z in game.zombies:
                if dist(z.x, z.y, b.x, b.y) < TILE * 5:
                    z.slow_t = max(getattr(z, "slow_t", 0), 1.2)
            if "animal_bond" in getattr(game, "researched", set()) and game.zombies:
                game.popup("Gâu!", b.x, b.y - 20, (255, 220, 180))


def vehicle_factory_behavior(b, game, dt):
    """Sản xuất phương tiện theo chu kỳ khi đủ nguyên liệu."""
    from entities.vehicle import VEHICLES, Vehicle
    kind = b.info.get("vehicle")
    if not kind or kind not in VEHICLES:
        return
    info = VEHICLES[kind]
    if not hasattr(b, "progress"):
        b.progress = 0.0
    # Chỉ sản xuất nếu chưa có xe gần nhà máy
    near = [v for v in getattr(game, "vehicles", [])
            if v.alive and dist(v.x, v.y, b.x, b.y) < TILE * 3]
    if near:
        b.working = False
        return
    cost = info["cost"]
    if not game.can_afford(cost):
        b.working = False
        return
    b.working = True
    b.progress += dt
    need = info.get("build_time", 30)
    if b.progress >= need:
        b.progress = 0.0
        for k, v in cost.items():
            game.res[k] = max(0, game.res.get(k, 0) - v)
        # Spawn xe cạnh nhà máy
        ang = random.uniform(0, 6.28)
        vx = b.x + math.cos(ang) * TILE * 1.5
        vy = b.y + math.sin(ang) * TILE * 1.5
        game.vehicles.append(Vehicle(kind, vx, vy))
        game.say(f"{info['name']} đã xuất xưởng!", 3, "good")


def station_behavior(b, game, dt):
    """Ga tàu: mỗi 40s gửi 1 lô tài nguyên tới ga khác nếu có đường sắt nối."""
    if not hasattr(b, "ship_t"):
        b.ship_t = 15.0
    b.ship_t -= dt
    if b.ship_t > 0:
        return
    b.ship_t = 40.0
    # Tìm ga khác
    others = [o for o in game.buildings.values()
              if o.kind == "station" and o is not b and o.hp > 0]
    if not others:
        return
    target = random.choice(others)
    # Gửi một ít tài nguyên từ kho player (mô phỏng thương mại vùng)
    for res_key in ("wood", "stone", "food", "iron", "fruit", "herb"):
        have = game.res.get(res_key, 0)
        if have >= 8:
            send = min(5, have // 2)
            game.res[res_key] -= send
            # bonus nhận lại ở ga đích (thương mại)
            recv = send + 1
            game.add_res(res_key, recv)
            game.popup(f"Tàu +{recv} {res_key}", target.x, target.y - 20, (200, 180, 100))
            game.say(f"Tàu hàng: {send} {res_key} → ga khác (lãi +1).", 2)
            break


BEHAVIORS = {"turret": turret_behavior, "producer": producer_behavior, "house": house_behavior,
             "farm": farm_behavior, "storage": storage_behavior, "pen": pen_behavior,
             "stable": stable_behavior, "kennel": kennel_behavior,
             "vehicle_factory": vehicle_factory_behavior, "station": station_behavior}


class Building:
    def __init__(self, kind, c, r):
        self.kind, self.c, self.r = kind, c, r
        self.info = BUILDINGS[kind]
        self.hp = self.max = self.info["hp"]
        self.spent = dict(self.info["cost"])   # tổng vật liệu đã bỏ ra (để hoàn 50% khi phá)
        self.x, self.y = tile_center(c, r)
        self.cool = 0.0        # tháp súng
        self.timer = 0.0       # nhà máy
        self.worker = None     # người tị nạn đang làm việc ở đây
        self.working = False
        self.sleepers = 0      # nhà ở: số người đang ngủ
        self.progress = 0.0    # nông trại: độ lớn của cây (0..1, 1 = chín)
        self.fill = 0.0        # kho: độ đầy (0..1)
        self.cows = self.info.get("start_cows", 0)   # chuồng bò: số bò
        self.horses = self.info.get("start_horses", 0)
        self.dogs = self.info.get("start_dogs", 0)
        self.breed = 0.0       # chuồng bò/ngựa/chó: tiến độ sinh sản

    @property
    def center(self):
        return self.x, self.y

    def update(self, game, dt):
        fn = BEHAVIORS.get(self.info.get("behavior"))
        if fn:
            fn(self, game, dt)

    def draw(self, surf):
        rect = pygame.Rect(self.c * TILE + 2, self.r * TILE + 2, TILE - 4, TILE - 4)
        pygame.draw.rect(surf, self.info["color"], rect, border_radius=4)
        if self.info.get("behavior") == "turret":
            pygame.draw.circle(surf, (20, 30, 50), rect.center, 6)
            if self.kind == "turret_rapid":      # hai nòng
                pygame.draw.circle(surf, (230, 240, 255), (rect.centerx - 3, rect.centery), 2)
                pygame.draw.circle(surf, (230, 240, 255), (rect.centerx + 3, rect.centery), 2)
            elif self.kind == "turret_long":     # nòng dài
                pygame.draw.line(surf, (230, 230, 255), rect.center, (rect.centerx, rect.y - 3), 3)
        elif self.kind == "stone_wall":
            for y in (rect.y + 9, rect.y + 19):
                pygame.draw.line(surf, (95, 95, 108), (rect.x + 2, y), (rect.right - 2, y), 2)
            pygame.draw.line(surf, (95, 95, 108), (rect.centerx, rect.y + 2), (rect.centerx, rect.y + 9), 2)
        elif self.kind == "iron_wall":
            pygame.draw.rect(surf, (70, 75, 85), rect.inflate(-4, -4), 2)
            for y in (rect.y + 8, rect.y + 16, rect.y + 24):
                pygame.draw.line(surf, (160, 170, 185), (rect.x + 3, y), (rect.right - 3, y), 2)
        elif self.kind == "floor":
            pygame.draw.rect(surf, (120, 120, 130), rect)
            pygame.draw.rect(surf, (100, 100, 110), rect, 1)
            pygame.draw.line(surf, (140, 140, 150), (rect.x, rect.centery), (rect.right, rect.centery), 1)
            pygame.draw.line(surf, (140, 140, 150), (rect.centerx, rect.y), (rect.centerx, rect.bottom), 1)
        elif self.kind == "iron_gate":
            pygame.draw.rect(surf, (70, 75, 85), rect.inflate(-6, -2), 2, border_radius=2)
            pygame.draw.rect(surf, (140, 150, 165), (rect.x + 3, rect.y + 3, 4, rect.h - 6))
            pygame.draw.rect(surf, (140, 150, 165), (rect.right - 7, rect.y + 3, 4, rect.h - 6))
            pygame.draw.line(surf, (200, 210, 220), (rect.x + 8, rect.centery), (rect.right - 8, rect.centery), 2)
            pygame.draw.line(surf, (95, 95, 108), (rect.centerx - 5, rect.y + 9), (rect.centerx - 5, rect.y + 19), 2)
            pygame.draw.line(surf, (95, 95, 108), (rect.centerx + 5, rect.y + 19), (rect.centerx + 5, rect.bottom - 2), 2)
        elif self.kind == "gate":
            pygame.draw.rect(surf, (90, 65, 40), rect.inflate(-6, -2), 2, border_radius=2)
            pygame.draw.rect(surf, (120, 85, 50), (rect.x + 3, rect.y + 3, 4, rect.h - 6))
            pygame.draw.rect(surf, (120, 85, 50), (rect.right - 7, rect.y + 3, 4, rect.h - 6))
            pygame.draw.line(surf, (235, 215, 140), (rect.x + 8, rect.centery), (rect.right - 8, rect.centery), 2)
        elif self.kind == "core":
            pygame.draw.rect(surf, (255, 240, 150), rect.inflate(-12, -12), border_radius=3)
        elif self.info.get("behavior") == "producer":
            inner = tuple(int(v * 0.55) for v in RESOURCES[self.info["produces"]]["node_color"])
            pygame.draw.rect(surf, inner, rect.inflate(-10, -10), border_radius=3)
            interval = self.info["worked_interval"] if self.working else self.info["interval"]
            frac = min(1.0, self.timer / interval)
            col = (90, 200, 255) if self.working else (200, 200, 120)
            pygame.draw.rect(surf, col, (rect.x + 2, rect.bottom - 6, (rect.w - 4) * frac, 3))
        elif self.kind == "house":
            pygame.draw.polygon(surf, (170, 70, 60),
                                [(rect.x - 1, rect.y + 13), (rect.centerx, rect.y - 3), (rect.right + 1, rect.y + 13)])
            for i in range(self.info["capacity"]):  # cửa sổ sáng đèn = có người đang ngủ
                lit = i < self.sleepers
                pygame.draw.rect(surf, (255, 235, 140) if lit else (70, 50, 40),
                                 (rect.x + 7 + i * 10, rect.bottom - 11, 6, 6))
        elif self.kind == "armory":
            pygame.draw.line(surf, (40, 40, 45), (rect.x + 5, rect.centery + 3), (rect.right - 5, rect.centery - 3), 4)
            pygame.draw.line(surf, (40, 40, 45), (rect.x + 5, rect.centery - 3), (rect.right - 5, rect.centery + 3), 4)
            pygame.draw.circle(surf, (230, 200, 90), rect.center, 4)
        elif self.kind == "trainer":
            pygame.draw.rect(surf, (235, 225, 245), (rect.centerx - 7, rect.y + 6, 14, 10), border_radius=2)
            pygame.draw.polygon(surf, (60, 40, 80), [(rect.centerx - 11, rect.y + 8), (rect.centerx, rect.y + 2),
                                                     (rect.centerx + 11, rect.y + 8), (rect.centerx, rect.y + 13)])
            pygame.draw.line(surf, (235, 225, 245), (rect.centerx + 10, rect.y + 9), (rect.centerx + 10, rect.y + 18), 2)
            pygame.draw.rect(surf, (230, 210, 120), (rect.x + 6, rect.bottom - 9, rect.w - 12, 4))
        elif self.kind == "market":
            for i in range(4):                               # mái che sọc
                pygame.draw.rect(surf, (200, 60, 55) if i % 2 == 0 else (245, 240, 225),
                                 (rect.x + 2 + i * 7, rect.y + 3, 7, 9))
            pygame.draw.rect(surf, (90, 60, 35), (rect.x + 4, rect.y + 15, rect.w - 8, 9), border_radius=2)
            pygame.draw.circle(surf, (240, 200, 90), (rect.centerx, rect.y + 19), 3)
        elif self.kind == "pen":
            pygame.draw.rect(surf, (110, 85, 55), rect, 2, border_radius=3)
            for i in range(self.cows):                       # mỗi con bò một chấm trắng
                cx = rect.x + 8 + (i % 2) * 14
                cy = rect.y + 9 + (i // 2) * 12
                pygame.draw.ellipse(surf, (242, 242, 236), (cx - 5, cy - 3, 11, 7))
                pygame.draw.circle(surf, (70, 56, 52), (cx + 4, cy - 1), 2)
            if self.cows >= 2 and self.cows < self.info["pen_cap"]:
                frac = min(1.0, self.breed / self.info["breed_time"])
                pygame.draw.rect(surf, (255, 150, 170), (rect.x + 2, rect.bottom - 5, (rect.w - 4) * frac, 3))
        elif self.kind == "farm":
            pygame.draw.rect(surf, (92, 66, 40), rect.inflate(-4, -4), border_radius=3)
            h = 2 + int(6 * self.progress)
            for px in (rect.x + 7, rect.x + 16, rect.x + 25):
                for py in (rect.y + 11, rect.y + 20):
                    pygame.draw.line(surf, (70, 170, 70), (px, py + 3), (px, py + 3 - h), 2)
                    if self.progress >= 1.0:                      # khoai chín
                        pygame.draw.circle(surf, (226, 196, 125), (px, py + 5), 3)
            if self.progress < 1.0:
                col = (90, 200, 255) if self.working else (120, 210, 90)
                pygame.draw.rect(surf, col, (rect.x + 2, rect.bottom - 5, (rect.w - 4) * self.progress, 3))
            else:
                pygame.draw.rect(surf, (255, 220, 90), (rect.x + 2, rect.bottom - 5, rect.w - 4, 3))
        elif self.kind == "research":
            pygame.draw.rect(surf, (200, 220, 240), (rect.x + 6, rect.y + 5, rect.w - 12, 10), border_radius=2)
            pygame.draw.circle(surf, (255, 240, 150), (rect.centerx, rect.centery + 4), 5)
            pygame.draw.line(surf, (60, 80, 100), (rect.centerx - 6, rect.centery + 4), (rect.centerx + 6, rect.centery + 4), 2)
        elif self.kind == "stable":
            pygame.draw.rect(surf, (100, 75, 45), rect, 2, border_radius=3)
            for i in range(self.horses):
                cx = rect.x + 8 + (i % 2) * 14
                cy = rect.y + 9 + (i // 2) * 12
                pygame.draw.ellipse(surf, (160, 110, 70), (cx - 5, cy - 3, 12, 7))
            if self.horses >= 1 and self.horses < self.info["pen_cap"]:
                frac = min(1.0, self.breed / self.info["breed_time"])
                pygame.draw.rect(surf, (200, 170, 120), (rect.x + 2, rect.bottom - 5, (rect.w - 4) * frac, 3))
        elif self.kind == "kennel":
            pygame.draw.rect(surf, (90, 70, 50), rect, 2, border_radius=3)
            for i in range(self.dogs):
                cx = rect.x + 7 + (i % 2) * 13
                cy = rect.y + 8 + (i // 2) * 11
                pygame.draw.ellipse(surf, (180, 140, 90), (cx - 4, cy - 2, 9, 6))
            if self.dogs >= 1 and self.dogs < self.info["pen_cap"]:
                frac = min(1.0, self.breed / self.info["breed_time"])
                pygame.draw.rect(surf, (200, 160, 120), (rect.x + 2, rect.bottom - 5, (rect.w - 4) * frac, 3))
        elif self.kind in ("wood_store", "stone_store", "food_store", "copper_store", "iron_store", "silver_store", "gold_store"):
            inner = rect.inflate(-8, -10)
            inner.y -= 2
            pygame.draw.rect(surf, (60, 45, 35), inner, border_radius=3)
            if self.kind == "wood_store":
                for i in range(3):
                    pygame.draw.rect(surf, (170, 125, 75), (inner.x + 2, inner.y + 2 + i * 5, inner.w - 4, 4))
            elif self.kind == "stone_store":
                pygame.draw.circle(surf, (190, 190, 205), (inner.x + 6, inner.centery), 4)
                pygame.draw.circle(surf, (160, 160, 175), (inner.right - 6, inner.centery + 1), 4)
                pygame.draw.circle(surf, (205, 205, 220), (inner.centerx, inner.y + 5), 3)
            else:
                pygame.draw.circle(surf, (235, 190, 110), inner.center, 6)
                pygame.draw.rect(surf, (200, 150, 80), (inner.centerx - 2, inner.y + 1, 4, 4))
            col = RESOURCES[self.info["store"]]["color"]
            pygame.draw.rect(surf, (30, 30, 30), (rect.x + 2, rect.bottom - 5, rect.w - 4, 3))
            pygame.draw.rect(surf, col, (rect.x + 2, rect.bottom - 5, (rect.w - 4) * min(1.0, self.fill), 3))
        if self.hp < self.max:
            pygame.draw.rect(surf, (60, 0, 0), (rect.x, rect.y - 5, rect.w, 3))
            pygame.draw.rect(surf, (80, 220, 80), (rect.x, rect.y - 5, rect.w * max(0, self.hp) / self.max, 3))
