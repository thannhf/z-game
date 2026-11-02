"""Người tị nạn: đến từ rìa bản đồ, gia nhập căn cứ và làm việc theo kỹ năng ngẫu nhiên."""
import math
import random

import pygame

from settings import TILE, LEVEL_XP, LEVEL_BONUS
from pathfinding import find_path
from utils import tile_of
from entities.skills import SKILLS

NAMES = ["Lan", "Minh", "Hùng", "Mai", "Tuấn", "Hà", "Nam", "Linh", "Bình", "Thảo",
         "Dũng", "Hoa", "Sơn", "Trang", "Khoa", "Yến"]


class Refugee:
    R = 7

    def __init__(self, x, y, skill=None, name=None, elite=False):
        self.x, self.y = x, y
        self.skill = skill or random.choice(list(SKILLS))
        self.info = SKILLS[self.skill]
        self.name = name or random.choice(NAMES)
        self.hp = self.max_hp = 50.0 if elite else 30.0
        self.elite = elite           # người tị nạn đặc biệt (thưởng từ boss): khỏe hơn, xuất phát cấp 4
        self.xp = LEVEL_XP[3] if elite else 0.0
        self.left = False            # đã bỏ đi vì tinh thần quá thấp
        self.speed = 70
        self.state = "arriving"      # arriving -> settled
        self.age = 0.0
        self.cool = 0.0              # thời gian chờ cho kỹ năng
        self.job = None              # mục tiêu công việc hiện tại
        self.target, self.target_t, self.idle = None, 0.0, 0.0
        self.path, self.path_goal, self.repath_t = [], None, 0.0
        self.home = None             # nhà ở (Building)
        self.sleeping = False

    @property
    def alive(self):
        return self.hp > 0 and not self.left

    # ----- cấp kỹ năng -----
    @property
    def level(self):
        return sum(1 for need in LEVEL_XP if self.xp >= need)

    def add_xp(self, game, n):
        before = self.level
        if "skill_xp" in getattr(game, "researched", set()):
            n *= 1.3
        self.xp += n
        if self.level > before:
            game.say(f"{self.name} ({self.info['name']}) lên cấp {self.level}!", 3, "good")
            game.popup(f"Lv{self.level}", self.x, self.y - 20, (255, 230, 120))

    def work_mult(self, game):
        """Hệ số tốc độ làm việc = cấp kỹ năng x tinh thần dân cư."""
        return min(2.2, (1 + LEVEL_BONUS * (self.level - 1)) * game.morale_mult())

    def retrain(self, skill):
        """Đổi nghề (ở nhà huấn luyện): mất một nửa kinh nghiệm, bỏ chỗ làm cũ."""
        if self.job is not None and self.job.worker is self:
            self.job.worker = None
        self.job = None
        self.skill = skill
        self.info = SKILLS[skill]
        self.xp *= 0.5

    # ----- di chuyển -----
    def move_to(self, game, tx, ty, dt, stop=4):
        """Đi về (tx, ty) theo đường tìm được. Trả về True nếu đã tới trong phạm vi `stop`."""
        if math.hypot(tx - self.x, ty - self.y) <= stop:
            return True
        goal = tile_of(tx, ty)
        self.repath_t -= dt
        if goal != self.path_goal or self.repath_t <= 0:
            self.path = find_path(game, tile_of(self.x, self.y), goal) or []
            self.path_goal, self.repath_t = goal, 1.0
        while self.path and math.hypot(self.path[0][0] - self.x, self.path[0][1] - self.y) < 5:
            self.path.pop(0)
        wx, wy = self.path[0] if self.path else (tx, ty)
        d = math.hypot(wx - self.x, wy - self.y) or 1.0
        spd = self.speed * (1.15 if "bio_speed" in getattr(game, "researched", set()) else 1.0)
        nx = self.x + (wx - self.x) / d * spd * dt
        ny = self.y + (wy - self.y) / d * spd * dt
        if not game.blocked(nx, self.y, self.R, True):
            self.x = nx
        if not game.blocked(self.x, ny, self.R, True):
            self.y = ny
        return False

    def wander(self, game, dt, cx, cy, radius):
        """Đi lang thang quanh (cx, cy), nghỉ vài giây giữa các lần đi."""
        if self.idle > 0:
            self.idle -= dt
            return
        self.target_t -= dt
        if self.target is None or self.target_t <= 0:
            a, d = random.uniform(0, 6.283), random.uniform(40, radius)
            self.target = (cx + math.cos(a) * d, cy + math.sin(a) * d)
            self.target_t = 4.0
        if self.move_to(game, *self.target, dt, stop=6):
            self.target, self.idle = None, random.uniform(1, 3)

    # ----- vòng đời -----
    def check_home(self, game):
        """Nhà bị phá thì tìm nhà khác còn chỗ (hoặc không có nhà)."""
        if self.home is None or game.buildings.get((self.home.c, self.home.r)) is not self.home:
            self.home = game.free_house()

    def go_sleep(self, game, dt):
        if self.home is None:     # vô gia cư: lang thang gần căn cứ, dễ bị zombie tấn công
            self.sleeping = False
            return self.wander(game, dt, game.core.x, game.core.y, 80)
        if self.move_to(game, self.home.x, self.home.y, dt, stop=TILE * 1.2):
            self.sleeping = True

    def update(self, game, dt):
        self.age += dt
        self.check_home(game)
        wm = self.work_mult(game)
        self.cool -= dt * wm
        if game.phase == "night" and self.skill != "gunner":
            return self.go_sleep(game, dt)
        self.sleeping = False
        if self.state == "arriving":
            # Ưu tiên chạy về nhà được gán; nếu không có thì về lõi
            tx, ty = (self.home.x, self.home.y) if self.home else (game.core.x, game.core.y)
            if self.move_to(game, tx, ty, dt, stop=TILE * 1.5) or self.age > 40:
                self.state = "settled"
                game.say(f"{self.name} ({self.info['name']}) đã gia nhập căn cứ!", 4, "good")
            return
        self.info["act"](self, game, dt * wm)

    def draw(self, surf):
        if self.sleeping:         # đang ngủ trong nhà
            return
        pygame.draw.circle(surf, (25, 25, 25), (self.x, self.y), self.R + 2)
        pygame.draw.circle(surf, self.info["color"], (self.x, self.y), self.R)
        pygame.draw.circle(surf, (245, 215, 180), (self.x, self.y - 2), 3)
        if self.elite:
            pygame.draw.circle(surf, (255, 215, 80), (self.x, self.y), self.R + 3, 2)
        for i in range(self.level - 1):          # chấm vàng = cấp kỹ năng
            pygame.draw.circle(surf, (255, 225, 90), (self.x - 6 + i * 4, self.y + self.R + 5), 1)
        if self.hp < self.max_hp:
            pygame.draw.rect(surf, (60, 0, 0), (self.x - 9, self.y - 16, 18, 3))
            pygame.draw.rect(surf, (80, 220, 80), (self.x - 9, self.y - 16, 18 * max(0, self.hp) / self.max_hp, 3))
