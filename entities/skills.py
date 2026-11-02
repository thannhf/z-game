"""Kỹ năng của người tị nạn. Thêm kỹ năng = viết một hàm act(r, game, dt) + một mục trong SKILLS.

Hàm kỹ năng chạy mỗi khung hình cho người tị nạn đã gia nhập căn cứ.
Có thể dùng các phương thức của Refugee: move_to(), wander(), thuộc tính cool, job.
"""
import math
import random

from settings import TILE, RESOURCES, HUNT_RANGE
from utils import dist, nearest
from entities.bullet import Bullet


def claim_workplace(r, game, kinds):
    """Giữ (hoặc nhận) một công trình thuộc `kinds` (tên hoặc tuple tên) chưa có người làm."""
    kinds = (kinds,) if isinstance(kinds, str) else kinds
    job = r.job
    if job is not None and (game.buildings.get((job.c, job.r)) is not job or job.worker is not r):
        r.job = job = None
    if job is None:
        free = [b for b in game.buildings.values()
                if b.kind in kinds and (b.worker is None or not b.worker.alive)]
        b = nearest(free, r.x, r.y)
        if b:
            b.worker = r
            r.job = job = b
    return job


def miner(r, game, dt):
    """Nhận một mỏ đá / nhà máy gỗ chưa có thợ, ra đó làm việc -> sản xuất nhanh hơn."""
    job = claim_workplace(r, game, ("quarry", "sawmill", "copper_mine", "iron_mine", "silver_mine", "gold_mine"))
    if job:
        r.move_to(game, job.x, job.y, dt, stop=TILE * 1.2)
    else:
        r.wander(game, dt, game.core.x, game.core.y, 130)


def farmer(r, game, dt):
    """Nhận một nông trại chưa có người, ra đó chăm cây -> cây lớn nhanh và tự thu hoạch khi chín."""
    job = claim_workplace(r, game, "farm")
    if job:
        r.move_to(game, job.x, job.y, dt, stop=TILE * 1.2)
    else:
        r.wander(game, dt, game.core.x, game.core.y, 130)


def hunter(r, game, dt):
    """Đi săn bò: lại gần, bắn hạ, thịt cộng vào lương thực. Kho lương thực đầy thì nghỉ."""
    cow = nearest([a for a in game.animals if a.alive], r.x, r.y)
    if cow is None or game.is_full("food"):
        return r.wander(game, dt, game.core.x, game.core.y, 130)
    d = dist(cow.x, cow.y, r.x, r.y)
    if d > HUNT_RANGE - 40:
        r.move_to(game, cow.x, cow.y, dt, stop=HUNT_RANGE - 40)
    if d <= HUNT_RANGE and r.cool <= 0:
        ang = math.atan2(cow.y - r.y, cow.x - r.x) + random.uniform(-0.05, 0.05)
        game.bullets.append(Bullet(r.x, r.y, ang, 1, color=(255, 190, 120), hits_animals=True))
        r.cool = 0.9
        r.add_xp(game, 1.5)


def gatherer(r, game, dt):
    """Ban ngày tự đi hái gỗ/đá (bỏ qua loại đã đầy kho), ban đêm về căn cứ."""
    if game.phase == "night":
        r.job = None
        return r.wander(game, dt, game.core.x, game.core.y, 100)
    n = r.job
    if n is not None and (game.nodes.get((n.c, n.r)) is not n or game.is_full(n.kind)):
        r.job = n = None
    if n is None:
        open_nodes = [x for x in game.nodes.values() if not game.is_full(x.kind)]
        r.job = n = nearest(open_nodes, r.x, r.y)
    if n is None:
        return r.wander(game, dt, game.core.x, game.core.y, 130)
    if r.move_to(game, n.x, n.y, dt, stop=TILE * 1.2) and r.cool <= 0:
        kind = n.harvest()
        game.add_res(kind, 1)
        game.popup(f"+1 {RESOURCES[kind]['name']}", r.x, r.y - 12, RESOURCES[kind]["color"])
        r.cool = 2.0
        r.add_xp(game, 2.0)
        if n.depleted:
            game.nodes.pop((n.c, n.r), None)
            r.job = None


def builder(r, game, dt):
    """Đi sửa công trình hư hại."""
    hurt = [b for b in game.buildings.values() if b.hp < b.max]
    b = nearest(hurt, r.x, r.y)
    if b is None:
        return r.wander(game, dt, game.core.x, game.core.y, 130)
    if r.move_to(game, b.x, b.y, dt, stop=TILE * 1.3):
        b.hp = min(b.max, b.hp + 18 * dt)
        r.add_xp(game, dt * 0.8)


def medic(r, game, dt):
    """Đi theo bạn khi bị thương, hồi máu cho bạn và công trình gần đó."""
    p = game.player
    if p.hp < p.max_hp:
        r.move_to(game, p.x, p.y, dt, stop=45)
    else:
        r.wander(game, dt, game.core.x, game.core.y, 130)
    healed = False
    if dist(p.x, p.y, r.x, r.y) < 150 and p.hp < p.max_hp:
        p.hp = min(p.max_hp, p.hp + 3 * dt)
        healed = True
    for b in game.buildings.values():
        if b.hp < b.max and dist(b.x, b.y, r.x, r.y) < 150:
            b.hp = min(b.max, b.hp + 4 * dt)
            healed = True
    if healed:
        r.add_xp(game, dt * 0.8)


def gunner(r, game, dt):
    """Ở gần căn cứ và bắn zombie trong tầm."""
    r.wander(game, dt, game.core.x, game.core.y, 100)
    if r.cool <= 0:
        z = nearest(game.zombies, r.x, r.y)
        if z and dist(z.x, z.y, r.x, r.y) <= 230:
            ang = math.atan2(z.y - r.y, z.x - r.x)
            dmg = 2 if r.level >= 4 else 1          # xạ thủ cấp 4+ bắn đau gấp đôi
            game.bullets.append(Bullet(r.x, r.y, ang, dmg, color=(150, 200, 255)))
            r.cool = 0.8
            r.add_xp(game, 1.0)


SKILLS = {
    "miner":    dict(name="Thợ mỏ", color=(190, 190, 215), act=miner,
                     desc="Làm việc ở mỏ đá/kim loại / nhà máy gỗ, tăng tốc"),
    "gatherer": dict(name="Người hái lượm", color=(120, 210, 120), act=gatherer,
                     desc="Ban ngày tự thu thập gỗ và đá"),
    "builder":  dict(name="Thợ xây", color=(235, 170, 90), act=builder,
                     desc="Sửa công trình hư hại"),
    "medic":    dict(name="Y tá", color=(240, 120, 150), act=medic,
                     desc="Hồi máu cho bạn và công trình"),
    "gunner":   dict(name="Xạ thủ", color=(110, 170, 240), act=gunner,
                     desc="Bắn zombie gần căn cứ"),
    "farmer":   dict(name="Nông dân", color=(225, 205, 90), act=farmer,
                     desc="Chăm nông trại, thu hoạch khoai tây"),
    "hunter":   dict(name="Thợ săn", color=(200, 130, 80), act=hunter,
                     desc="Săn bò lấy thịt (lương thực)"),
}
