"""Cây / mỏ đá trên bản đồ để khai thác."""
import pygame

from settings import TILE, RESOURCES
from utils import tile_center


class ResourceNode:
    def __init__(self, kind, c, r, amount=5):
        self.kind, self.c, self.r, self.amount = kind, c, r, amount
        self.x, self.y = tile_center(c, r)

    @property
    def depleted(self):
        return self.amount <= 0

    def harvest(self):
        self.amount -= 1
        return self.kind

    def draw(self, surf, season_info=None):
        rect = pygame.Rect(self.c * TILE + 4, self.r * TILE + 4, TILE - 8, TILE - 8)
        col = getattr(self, "plant_color", None) or RESOURCES[self.kind]["node_color"]
        # mùa thu: cây vàng; mùa đông: cây xám
        if self.kind == "wood" and season_info and not getattr(self, "plant_color", None):
            if season_info.get("leaf_fall"):
                col = season_info.get("tree_tint", (180, 140, 40))
            elif season_info.get("snow"):
                col = (90, 100, 95)
        pygame.draw.ellipse(surf, col, rect)
