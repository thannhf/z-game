"""Hàm tiện ích nhỏ dùng chung."""
import math

from settings import TILE


def tile_of(x, y):
    return int(x // TILE), int(y // TILE)


def tile_center(c, r):
    return c * TILE + TILE / 2, r * TILE + TILE / 2


def dist(ax, ay, bx, by):
    return math.hypot(ax - bx, ay - by)


def nearest(items, x, y):
    """Đối tượng (có .x .y) gần điểm (x, y) nhất, hoặc None."""
    return min(items, key=lambda o: (o.x - x) ** 2 + (o.y - y) ** 2, default=None)
