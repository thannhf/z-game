"""Giao diện: thanh trạng thái, công cụ, danh sách người tị nạn, nhật ký, các bảng (xưởng/huấn luyện/chợ),
menu tạm dừng. Các nút bấm được đăng ký vào self.hits mỗi khung hình; main.py gọi Hud.click() khi bấm chuột."""
import pygame

from settings import (W, H, VIEW_W, VIEW_H, RESOURCES, TOOL_ORDER, TOOL_LABELS, TOOL_KEYS, TILE, MARKET_TRADES, COLS, ROWS,
                      RETRAIN_COST, GAME_SPEEDS, BOSS_EVERY, SEASON_EFFECTS, RESEARCHES, BIOMES,
                      CHAR_TOOLS, BUILD_TOOLS, REGION_TRADE_OFFERS)
from entities.faction import FACTIONS, BLACK_MARKET_TRADES, REL_HOSTILE, REL_FRIENDLY
from settings import TERRAIN
from utils import tile_of, dist
from entities.building import BUILDINGS
from entities.weapons import WEAPONS, WEAPON_ORDER
from entities.skills import SKILLS


def make_font(size):
    # font hệ thống để hiển thị được tiếng Việt có dấu
    return pygame.font.SysFont("dejavusans,arial,segoeui,notosans,tahoma", size)


class Hud:
    def __init__(self, screen):
        self.screen = screen
        self.font, self.small, self.big = make_font(18), make_font(15), make_font(48)
        self.tools_h = 28   # chiều cao thanh công cụ ở đáy màn hình
        self.tools_collapsed = False  # True = thu gọn bảng hướng dẫn
        self.hits = []      # (rect, hành động) của các nút đang hiện
        self.panel_rect = None

    def text(self, t, x, y, color=(235, 240, 230), font=None):
        self.screen.blit((font or self.font).render(t, True, color), (x, y))

    def centered(self, t, y, color=(235, 240, 230), font=None):
        f = font or self.font
        self.text(t, (VIEW_W - f.size(t)[0]) / 2, y, color, f)

    # ----- nút bấm -----
    def button(self, rect, label, action, active=False, enabled=True, font=None):
        rect = pygame.Rect(rect)
        mouse = pygame.mouse.get_pos()
        hover = rect.collidepoint(mouse) and enabled
        bg = (90, 120, 70) if active else (70, 70, 80) if hover else (45, 48, 58)
        if not enabled:
            bg = (38, 38, 42)
        pygame.draw.rect(self.screen, bg, rect, border_radius=4)
        pygame.draw.rect(self.screen, (150, 155, 165) if enabled else (80, 80, 85), rect, 1, border_radius=4)
        f = font or self.small
        w, h = f.size(label)
        self.text(label, rect.centerx - w / 2, rect.centery - h / 2, (240, 240, 235) if enabled else (120, 120, 120), f)
        if enabled:
            self.hits.append((rect, action))

    def click(self, game, pos):
        """Xử lý bấm chuột vào giao diện. Trả về True nếu cú bấm đã bị giao diện nuốt."""
        for rect, act in reversed(self.hits):
            if rect.collidepoint(pos):
                self.run(game, act)
                return True
        if game.paused:
            return True
        if game.panel:
            if not (self.panel_rect and self.panel_rect.collidepoint(pos)):
                game.panel = None            # bấm ra ngoài bảng -> đóng
            return True
        return False

    def run(self, game, act):
        kind = act[0]
        if kind == "buy":
            game.player.buy_weapon(game, act[1])
        elif kind == "trade":
            game.trade(act[1])
        elif kind == "bm_trade":
            game.black_market_trade(act[1])
        elif kind == "pick":
            game.sel_ref = act[1]
        elif kind == "skill":
            if game.sel_ref is not None and game.sel_ref.alive:
                game.retrain(game.sel_ref, act[1])
        elif kind == "speed":
            game.set_speed(act[1])
        elif kind == "pause":
            game.paused = True
        elif kind == "resume":
            game.paused = False
        elif kind == "restart":
            game.reset()
        elif kind == "quit":
            game.want_quit = True
        elif kind == "research":
            game.do_research(act[1])
        elif kind == "close":
            game.panel = None
        elif kind == "toggle_tools":
            self.tools_collapsed = not self.tools_collapsed
        elif kind == "tool":
            game.player.tool = act[1]
            if act[1] == "gun":
                game.say(f"Đang dùng: {game.player.current_weapon()['name']}", 1.2)
            elif act[1] in BUILDINGS:
                game.say(f"Xây: {BUILDINGS[act[1]]['name']}", 1.2)
            else:
                game.say(f"Công cụ: {TOOL_LABELS.get(act[1], act[1])}", 1.2)
        elif kind == "diplomacy":
            # ("diplomacy", action, region_id, extra?)
            game.handle_diplomacy(act[1], act[2], act[3] if len(act) > 3 else None)
        elif kind == "open_diplomacy":
            game.open_diplomacy(act[1])

    # ----- vẽ tổng -----
    def draw(self, game, mouse_pos):
        self.hits = []
        self.panel_rect = None
        self.draw_preview(game, mouse_pos)
        for p in game.popups:
            self.text(p["text"], p["x"] - 20, p["y"], p["color"], self.small)
        self.draw_hints(game)
        self.draw_status(game)
        self.draw_minimap(game)
        self.draw_boss_bar(game)
        self.draw_tools(game)
        self.draw_refugees(game, mouse_pos)
        self.draw_log(game)
        if not game.paused:
            self.draw_speed_buttons(game)
            if game.panel:
                self.draw_panel(game)
        if game.over:
            self.draw_game_over(game)
        if game.paused:
            self.draw_pause(game)

    @staticmethod
    def cost_str(cost):
        return ",".join(f"{v}{RESOURCES[k]['name'][0]}" for k, v in cost.items())

    @staticmethod
    def cost_full(cost):
        return ", ".join(f"{v} {RESOURCES[k]['name'].lower()}" for k, v in cost.items()) or "miễn phí"

    def draw_preview(self, game, mouse_pos):
        p = game.player
        wx, wy = game.screen_to_world(mouse_pos)
        if p.tool == "upgrade":
            c, r = tile_of(wx, wy)
            b = game.buildings.get((c, r))
            opts = b.info.get("upgrades", []) if b else []
            if opts:
                idx = 1 if p.alt and len(opts) > 1 else 0
                ok = p.upgrade_error(game, opts[idx], wx, wy) is None
                sx, sy = game.world_to_screen(c * TILE, r * TILE)
                pygame.draw.rect(self.screen, (120, 255, 120) if ok else (255, 100, 100),
                                 (sx, sy, TILE, TILE), 2)
                for i, o in enumerate(opts):
                    tip = f"{'Click' if i == 0 else 'Shift+Click'}: {BUILDINGS[o]['name']} ({self.cost_str(BUILDINGS[o]['cost'])})"
                    self.text(tip, mouse_pos[0] + 14, mouse_pos[1] + 12 + i * 18,
                              (255, 255, 160) if i == idx else (200, 200, 190), self.small)
            return
        if p.tool in BUILDINGS:
            c, r = tile_of(wx, wy)
            ok = p.build_error(game, p.tool, c, r, wx, wy) is None
            col = (120, 255, 120) if ok else (255, 100, 100)
            sx, sy = game.world_to_screen(c * TILE, r * TILE)
            pygame.draw.rect(self.screen, col, (sx, sy, TILE, TILE), 2)

    def draw_hints(self, game):
        """Gợi ý [E] trên các công trình tương tác ở gần người chơi."""
        for b in game.buildings.values():
            if b.info.get("interact") and dist(b.x, b.y, game.player.x, game.player.y) <= 110:
                label = f"[E] {b.info['name']}"
                sx, sy = game.world_to_screen(b.x, b.y)
                self.text(label, sx - self.small.size(label)[0] / 2, sy - 34, (255, 240, 150), self.small)

    def draw_status(self, game):
        if game.phase == "day":
            phase = f"BAN NGÀY ({int(game.timer)}s)"
            if game.day % BOSS_EVERY == 0:
                phase += " - đêm nay có BOSS"
        else:
            phase = f"BAN ĐÊM (còn {game.to_spawn + len(game.zombies)} zombie)"
        extra = f"  [{game.speed}x]" if game.speed > 1 else ""
        si = game.season_info()
        self.text(f"Ngày {game.day} - {phase}{extra}  |  Mùa {si['name']}", 12, 8, si["color"])
        # dòng tài nguyên cơ bản
        x = 12
        for k in ("wood", "stone", "food"):
            info = RESOURCES[k]
            full = game.is_full(k)
            self.text(f"{info['name']}: {game.res[k]}/{game.cap(k)}", x, 28,
                      (255, 120, 100) if full else info["color"])
            x += 130
        # kim loại
        for k in ("copper", "iron", "silver", "gold"):
            info = RESOURCES[k]
            full = game.is_full(k)
            self.text(f"{info['name']}: {game.res[k]}/{game.cap(k)}", x, 28,
                      (255, 120, 100) if full else info["color"])
            x += 110
        self.text(f"Chỗ ở: {len(game.refugees)}/{game.housing_capacity()}", 12, 48, (240, 200, 160))
        nxt = game.next_arrival_in()
        if nxt is not None:
            self.text(f"Người tị nạn tới sau {int(nxt) + 1}s", 160, 48, (200, 220, 255))
        # Vùng + địa hình hiện tại (+ tên biển nếu gần)
        bid = game.biome_at_world(game.player.x, game.player.y)
        binfo = BIOMES.get(bid, BIOMES["middle"])
        terr = game.terrain_at_world(game.player.x, game.player.y) if hasattr(game, "terrain_at_world") else "none"
        tname = TERRAIN.get(terr, {}).get("name", "")
        # Nếu đứng gần biển: hiện tên Biển Đông/Tây/Nam/Bắc
        sea_label = ""
        if hasattr(game, "sea_side_map"):
            pc, pr = int(game.player.x // TILE), int(game.player.y // TILE)
            for dc, dr in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
                nc, nr = pc + dc, pr + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS and game.terrain_map[nr][nc] == "sea":
                    side = game.sea_side_map[nr][nc]
                    if side:
                        from settings import SEA_NAMES
                        sea_label = f" | {SEA_NAMES.get(side, side)}"
                        break
        label = f"Vùng: {binfo['name']}" + (f" | {tname}" if tname else "") + sea_label
        self.text(label, 380, 48, binfo.get("grid", (200, 200, 200)))
        elabel = getattr(game, "biome_effect_label", "")
        if elabel:
            self.text(elabel, 380, 28, (255, 180, 120), self.small)
        if getattr(game, "player_poison", 0) > 0:
            self.text(f"Trúng độc! ({game.player_poison:.1f}s)", 500, 28, (80, 255, 100), self.small)
        n_boss = sum(1 for b in getattr(game, "region_bosses", []) if b.alive)
        if n_boss:
            self.text(f"Boss vùng: {n_boss}", 640, 48, (255, 120, 80), self.small)
        # Quan hệ 3 phe (ngắn)
        if hasattr(game, "player_relation"):
            parts = []
            for fid, fname in (("gov", "CP"), ("rebel", "PQ"), ("nomad", "DM")):
                r = game.player_relation.get(fid, 0)
                col = (120, 200, 120) if r >= 40 else (220, 100, 90) if r <= -40 else (200, 200, 180)
                parts.append((f"{fname}:{r:+d}", col))
            x = 12
            for label, col in parts:
                self.text(label, x, VIEW_H - 22, col, self.small)
                x += 70
        n_cow = sum(1 for a in game.animals if a.kind == "cow")
        n_horse = sum(1 for a in game.animals if a.kind == "horse")
        n_dog = sum(1 for a in game.animals if a.kind == "dog")
        # Để góc trái dưới (không bị minimap che)
        self.text(f"Bò:{n_cow} Ngựa:{n_horse} Chó:{n_dog}", 230, VIEW_H - 22, (235, 235, 225), self.small)
        s, p = self.screen, game.player
        self.text("Máu", 12, 72)
        pygame.draw.rect(s, (70, 0, 0), (56, 76, 140, 12))
        pygame.draw.rect(s, (224, 80, 58), (56, 76, 140 * max(0, p.hp) / p.max_hp, 12))
        self.text("Lõi", 210, 72)
        pygame.draw.rect(s, (70, 60, 0), (250, 76, 140, 12))
        pygame.draw.rect(s, (230, 200, 80), (250, 76, 140 * max(0, game.core.hp) / game.core.max, 12))
        label, col = game.morale_label()                     # tinh thần dân cư
        self.text("Tinh thần", 404, 72)
        pygame.draw.rect(s, (40, 40, 40), (486, 76, 120, 12))
        pygame.draw.rect(s, col, (486, 76, 120 * game.morale / 100, 12))
        self.text(label, 614, 72, col, self.small)

    def draw_minimap(self, game):
        """Minimap góc phải dưới (trên thanh công cụ): không che thông số trên."""
        mw, mh = 168, 112
        margin = 8
        x0 = VIEW_W - mw - margin
        # Nằm trên thanh công cụ
        tools_h = getattr(self, "tools_h", 30)
        y0 = VIEW_H - tools_h - mh - margin - 4
        scale_x = mw / W
        scale_y = mh / H
        # Nền
        pygame.draw.rect(self.screen, (15, 18, 22), (x0 - 2, y0 - 2, mw + 4, mh + 4), border_radius=3)
        pygame.draw.rect(self.screen, (40, 45, 50), (x0 - 2, y0 - 2, mw + 4, mh + 4), 1, border_radius=3)
        # Vẽ biome theo block (mỗi 2 ô 1 pixel-ish)
        step = 2
        for r in range(0, ROWS, step):
            for c in range(0, COLS, step):
                bid = game.biome_map[r][c]
                col = BIOMES[bid]["color"]
                terr = game.terrain_map[r][c] if hasattr(game, "terrain_map") else "none"
                from settings import TERRAIN as _T
                if terr != "none" and _T.get(terr, {}).get("color"):
                    col = _T[terr]["color"]
                px = x0 + int(c * TILE * scale_x)
                py = y0 + int(r * TILE * scale_y)
                pw = max(1, int(step * TILE * scale_x))
                ph = max(1, int(step * TILE * scale_y))
                pygame.draw.rect(self.screen, col, (px, py, pw, ph))
        # Faction bases
        if hasattr(game, "factions"):
            for f in game.factions.values():
                fx = x0 + int(f.base_x * scale_x)
                fy = y0 + int(f.base_y * scale_y)
                pygame.draw.circle(self.screen, f.color, (fx, fy), 3)
        # Căn cứ hải quân
        if hasattr(game, "naval_bases"):
            for bc, br, side in game.naval_bases:
                fx = x0 + int((bc * TILE + TILE // 2) * scale_x)
                fy = y0 + int((br * TILE + TILE // 2) * scale_y)
                pygame.draw.circle(self.screen, (220, 180, 80), (fx, fy), 3)
                pygame.draw.circle(self.screen, (40, 80, 140), (fx, fy), 3, 1)
        # Tộc vùng
        if hasattr(game, "tribes"):
            for t in game.tribes.values():
                tx = x0 + int(t.base_x * scale_x)
                ty = y0 + int(t.base_y * scale_y)
                pygame.draw.rect(self.screen, t.color, (tx - 2, ty - 2, 5, 5))
        # Quái vùng
        if hasattr(game, "region_monsters"):
            for m in game.region_monsters:
                if not m.alive:
                    continue
                mx = x0 + int(m.x * scale_x)
                my = y0 + int(m.y * scale_y)
                pygame.draw.circle(self.screen, (255, 100, 255), (mx, my), 2)
        # Thủy quái
        if hasattr(game, "sea_monsters"):
            for m in game.sea_monsters:
                if not m.alive:
                    continue
                mx = x0 + int(m.x * scale_x)
                my = y0 + int(m.y * scale_y)
                pygame.draw.circle(self.screen, (80, 200, 255), (mx, my), 2)
        # Boss vùng
        if hasattr(game, "region_bosses"):
            for b in game.region_bosses:
                if not b.alive:
                    continue
                bx = x0 + int(b.x * scale_x)
                by = y0 + int(b.y * scale_y)
                pygame.draw.circle(self.screen, (255, 50, 50), (bx, by), 4)
                pygame.draw.circle(self.screen, (255, 220, 80), (bx, by), 4, 1)
        # Core
        cx = x0 + int(game.core.x * scale_x)
        cy = y0 + int(game.core.y * scale_y)
        pygame.draw.rect(self.screen, (255, 220, 80), (cx - 2, cy - 2, 5, 5))
        # Zombies
        for z in game.zombies:
            if z.hp <= 0:
                continue
            zx = x0 + int(z.x * scale_x)
            zy = y0 + int(z.y * scale_y)
            col = (255, 60, 60) if not getattr(z, "region", None) else (255, 140, 80)
            pygame.draw.circle(self.screen, col, (zx, zy), 2)
        # Player
        px = x0 + int(game.player.x * scale_x)
        py = y0 + int(game.player.y * scale_y)
        pygame.draw.circle(self.screen, (100, 220, 255), (px, py), 3)
        pygame.draw.circle(self.screen, (255, 255, 255), (px, py), 3, 1)
        # Camera viewport
        cam = game.cam
        vx = x0 + int(cam[0] * scale_x)
        vy = y0 + int(cam[1] * scale_y)
        vw = max(4, int(VIEW_W * scale_x))
        vh = max(4, int(VIEW_H * scale_y))
        pygame.draw.rect(self.screen, (220, 220, 230), (vx, vy, vw, vh), 1)
        self.text("Map", x0, y0 - 14, (180, 190, 200), self.small)

    def draw_boss_bar(self, game):
        boss = next((z for z in game.zombies if z.kind == "boss" and z.hp > 0), None)
        if boss is None:
            return
        x, w = VIEW_W / 2 - 180, 360
        pygame.draw.rect(self.screen, (60, 0, 0), (x, 8, w, 16))
        pygame.draw.rect(self.screen, (200, 40, 40), (x, 8, w * max(0, boss.hp) / boss.max_hp, 16))
        pygame.draw.rect(self.screen, (240, 200, 70), (x, 8, w, 16), 2)
        self.text(f"BOSS  {int(boss.hp)}/{int(boss.max_hp)}", x + 8, 7, (255, 245, 220), self.small)

    def draw_tools(self, game):
        """Thanh công cụ: nhân vật (trái) + xây dựng (dưới, chọn bằng chuột)."""
        font = self.small
        screen_w, screen_h = VIEW_W, VIEW_H
        btn_h = 26
        pad = 4

        if self.tools_collapsed:
            t = game.player.tool
            if t == "gun":
                name = f"Súng: {game.player.current_weapon()['name']}"
            elif t in BUILDINGS:
                name = BUILDINGS[t]["name"]
            else:
                name = TOOL_LABELS.get(t, t)
            label = name
            if t in BUILDINGS:
                label += f"  ({self.cost_str(BUILDINGS[t]['cost'])})"
            self.tools_h = h = 32
            strip = pygame.Surface((screen_w, h), pygame.SRCALPHA)
            strip.fill((0, 0, 0, 150))
            self.screen.blit(strip, (0, screen_h - h))
            self.text(label, 12, screen_h - h + 7, (255, 230, 120), font)
            self.text("Click để chọn · Tab mở rộng", 12 + font.size(label)[0] + 12,
                      screen_h - h + 8, (140, 150, 145), font)
            self.button((screen_w - 96, screen_h - h + 4, 88, 22),
                        "Mở rộng ▲", ("toggle_tools",), font=font)
            return

        # ---- Nhân vật (hàng trên thanh dưới) ----
        char_labels = []
        for t in CHAR_TOOLS:
            if t == "gun":
                name = f"Súng: {game.player.current_weapon()['name']}"
            else:
                name = TOOL_LABELS.get(t, t)
            char_labels.append((t, name))

        # ---- Xây dựng: hiện đủ tên, xuống hàng nếu chật ----
        build_labels = []
        for t in BUILD_TOOLS:
            name = BUILDINGS[t]["name"] if t in BUILDINGS else TOOL_LABELS.get(t, t)
            build_labels.append((t, name))

        max_w = screen_w - 110
        rows_build, row, rw = [], [], 0
        for t, name in build_labels:
            bw = max(48, font.size(name)[0] + 12)
            if row and rw + bw > max_w:
                rows_build.append(row)
                row, rw = [], 0
            row.append((t, name, bw))
            rw += bw + pad
        if row:
            rows_build.append(row)

        n_rows = 1 + len(rows_build)
        self.tools_h = h = n_rows * (btn_h + 2) + 8
        strip = pygame.Surface((screen_w, h), pygame.SRCALPHA)
        strip.fill((0, 0, 0, 145))
        self.screen.blit(strip, (0, screen_h - h))

        y0 = screen_h - h + 4
        self.text("NV:", 4, y0 + 4, (160, 200, 255), font)
        x = 28
        for t, name in char_labels:
            bw = max(70, font.size(name)[0] + 16)
            self.button((x, y0, bw, btn_h), name, ("tool", t),
                        active=(game.player.tool == t), font=font)
            x += bw + pad
        self.text("Q: đổi súng  E: đàm phán  F: lên xe/ngựa", x + 6, y0 + 5, (130, 145, 140), font)

        self.text("Xây:", 2, y0 + btn_h + 6, (255, 210, 120), font)
        for ri, brow in enumerate(rows_build):
            x = 34
            y = y0 + (ri + 1) * (btn_h + 2)
            for t, name, bw in brow:
                active = game.player.tool == t
                self.button((x, y, bw, btn_h), name, ("tool", t), active=active, font=font)
                x += bw + pad

        self.button((screen_w - 96, screen_h - h + 4, 88, 22),
                    "Thu gọn ▼", ("toggle_tools",), font=font)

    def draw_refugees(self, game, mouse_pos):
        if game.refugees:
            self.text(f"Dân cư ({len(game.refugees)})", 12, 88, (200, 210, 195), self.small)
        for i, r in enumerate(game.refugees):
            star = "* " if r.elite else ""
            self.text(f"{star}{r.name} - {r.info['name']} Lv{r.level}", 12, 108 + i * 18, r.info["color"], self.small)
        for r in game.refugees:
            if dist(r.x, r.y, *mouse_pos) < 16:
                nxt = "" if r.level >= 5 else f" (kn {int(r.xp)})"
                self.text(f"{r.name} Lv{r.level}{nxt}: {r.info['desc']}", r.x + 14, r.y - 26, (255, 255, 255), self.small)

    def draw_log(self, game):
        """Nhật ký thông báo góc trái dưới: dòng mới ở dưới cùng, dòng cũ mờ dần rồi biến mất."""
        y = VIEW_H - self.tools_h - 8
        for e in reversed(game.log):
            fade = min(1.0, e["life"] / 1.2)
            surf = self.small.render(e["text"], True, e["color"])
            w, h = surf.get_size()
            y -= h + 4
            bg = pygame.Surface((w + 14, h + 2), pygame.SRCALPHA)
            bg.fill((0, 0, 0, int(140 * fade)))
            surf.set_alpha(int(255 * fade))
            self.screen.blit(bg, (8, y))
            self.screen.blit(surf, (15, y + 1))

    def draw_speed_buttons(self, game):
        x = VIEW_W - 4 * 46 - 4
        self.button((x, 6, 42, 22), "II", ("pause",))
        for i, n in enumerate(GAME_SPEEDS):
            self.button((x + (i + 1) * 46, 6, 42, 22), f"{n}x", ("speed", n), active=game.speed == n)

    # ----- các bảng giao dịch -----
    def open_panel(self, game, title, w, h):
        rect = pygame.Rect((VIEW_W - w) / 2, (VIEW_H - self.tools_h - h) / 2 - 10, w, h)
        pygame.draw.rect(self.screen, (28, 30, 38), rect, border_radius=8)
        pygame.draw.rect(self.screen, (170, 175, 190), rect, 2, border_radius=8)
        self.text(title, rect.x + 16, rect.y + 10, (255, 235, 150))
        self.button((rect.right - 78, rect.y + 8, 66, 24), "Đóng (E)", ("close",))
        self.panel_rect = rect
        return rect

    def draw_panel(self, game):
        panels = {"shop": self.panel_shop, "trainer": self.panel_trainer, "market": self.panel_market,
                  "research": self.panel_research, "black_market": self.panel_black_market,
                  "diplomacy": self.panel_diplomacy}
        fn = panels.get(game.panel)
        if fn:
            fn(game)

    def panel_diplomacy(self, game):
        region = game.diplomacy_region
        leader = game.region_leaders.get(region) if region else None
        if not leader:
            game.panel = None
            return
        bname = BIOMES.get(region, {}).get("name", region)
        rect = self.open_panel(game, f"Đàm phán — {leader.name} ({bname})", 560, 420)
        # Quan hệ / trạng thái
        st = {"neutral": "Trung lập", "peace": "Hòa bình", "war": "Chiến tranh"}.get(leader.state, leader.state)
        st_col = {"neutral": (200, 200, 140), "peace": (80, 220, 100), "war": (255, 80, 80)}.get(leader.state, (200, 200, 200))
        self.text(f"Quan hệ: {leader.relation:+d}   ·   Trạng thái: {st}", rect.x + 16, rect.y + 40, st_col)
        demand = leader.demand or "?"
        self.text(f"Vùng đang cần: {demand}  |  Kho vùng: gỗ{leader.stock.get('wood',0)} đá{leader.stock.get('stone',0)} lương{leader.stock.get('food',0)}",
                  rect.x + 16, rect.y + 62, (180, 190, 180), self.small)
        # Hòa bình / chiến / trung lập
        y = rect.y + 90
        self.button((rect.x + 16, y, 120, 28), "Hòa bình", ("diplomacy", "peace", region),
                    active=leader.state == "peace")
        self.button((rect.x + 146, y, 120, 28), "Chiến tranh", ("diplomacy", "war", region),
                    active=leader.state == "war")
        self.button((rect.x + 276, y, 120, 28), "Trung lập", ("diplomacy", "neutral", region),
                    active=leader.state == "neutral")
        # Trao đổi tài nguyên
        self.text("Trao đổi tài nguyên:", rect.x + 16, y + 40, (255, 230, 150))
        for i, offer in enumerate(REGION_TRADE_OFFERS):
            oy = y + 68 + i * 34
            ok = all(game.res.get(k, 0) >= v for k, v in offer["give"].items()) and leader.state != "war"
            self.text(offer["label"], rect.x + 20, oy + 4, (220, 220, 210), self.small)
            self.button((rect.right - 120, oy, 100, 26), "Đổi" if ok else "Không",
                        ("diplomacy", "trade", region, i), enabled=ok, font=self.small)
        # Trao đổi người
        ry = y + 68 + len(REGION_TRADE_OFFERS) * 34 + 8
        self.text("Trao đổi người:", rect.x + 16, ry, (255, 230, 150))
        self.button((rect.x + 16, ry + 28, 160, 28), "Đưa 1 dân → họ",
                    ("diplomacy", "give_refugee", region), enabled=bool(game.refugees))
        self.button((rect.x + 190, ry + 28, 160, 28), "Nhận 1 dân từ họ",
                    ("diplomacy", "get_refugee", region))
        self.text("AI vùng ưu tiên kho tài nguyên & an ninh lãnh thổ của họ.",
                  rect.x + 16, rect.bottom - 28, (140, 150, 145), self.small)

    def panel_shop(self, game):
        rect = self.open_panel(game, "Xưởng vũ khí (mua / nâng cấp cấp 1-5)", 600, 70 + 58 * len(WEAPON_ORDER))
        p = game.player
        for i, key in enumerate(WEAPON_ORDER):
            base = WEAPON_BASE[key]
            y = rect.y + 44 + i * 58
            owned = key in p.owned
            lvl = p.owned.get(key, 0)
            title = f"{base['name']}  Lv.{lvl}" if owned else base["name"]
            self.text(title, rect.x + 16, y, (240, 240, 230) if owned else (180, 180, 190))
            self.text(base["desc"], rect.x + 16, y + 20, (160, 170, 160), self.small)
            if owned:
                if lvl >= 5:
                    self.button((rect.right - 130, y + 6, 114, 28),
                                "Đang dùng" if p.weapon == key else "Trang bị",
                                ("buy", key), active=p.weapon == key)
                else:
                    cost = UPGRADE_COST.get(lvl, {})
                    ok = game.can_afford(cost)
                    self.text(f"Nâng: {self.cost_str(cost)}", rect.x + 280, y + 8, (220, 200, 140), self.small)
                    self.button((rect.right - 130, y + 6, 114, 28),
                                "Nâng cấp" if ok else "Thiếu NL",
                                ("buy", key), enabled=ok)
            else:
                ok = game.can_afford(base["cost"])
                self.text(self.cost_str(base["cost"]), rect.x + 280, y + 8, (220, 200, 140), self.small)
                self.button((rect.right - 130, y + 6, 114, 28),
                            "Mua" if ok else "Thiếu NL",
                            ("buy", key), enabled=ok)

    def panel_market(self, game):
        rect = self.open_panel(game, "Chợ - tỷ giá cố định", 520, 80 + 44 * len(MARKET_TRADES))
        for i, (give, gn, get, rn) in enumerate(MARKET_TRADES):
            y = rect.y + 50 + i * 44
            ok = game.res[give] >= gn and game.cap(get) - game.res[get] >= rn
            self.text(f"{gn} {RESOURCES[give]['name']}  ->  {rn} {RESOURCES[get]['name']}", rect.x + 16, y + 4,
                      RESOURCES[give]["color"])
            self.button((rect.right - 90, y, 74, 28), "Đổi", ("trade", i), enabled=ok)
        self.text("Cần chỗ trống ở kho nhận.", rect.x + 16, rect.bottom - 26, (150, 160, 150), self.small)

    def panel_black_market(self, game):
        rel = game.player_relation.get("nomad", 0)
        title = f"Chợ đen (Du mục)  |  Quan hệ: {rel:+d}"
        rect = self.open_panel(game, title, 560, 80 + 40 * len(BLACK_MARKET_TRADES))
        status = "Đang mở" if game.black_market_open else "Tạm đóng"
        self.text(status, rect.x + 16, rect.y + 36, (150, 220, 150) if game.black_market_open else (255, 120, 100), self.small)
        for i, (give, gn, get, rn) in enumerate(BLACK_MARKET_TRADES):
            y = rect.y + 58 + i * 40
            ok = game.black_market_open and game.res.get(give, 0) >= gn and not game.is_full(get)
            gname = RESOURCES.get(give, {}).get("name", give)
            tname = RESOURCES.get(get, {}).get("name", get)
            self.text(f"{gn} {gname}  →  {rn} {tname}", rect.x + 16, y + 4,
                      RESOURCES.get(give, {}).get("color", (200, 200, 200)))
            self.button((rect.right - 90, y, 74, 28), "Đổi", ("bm_trade", i), enabled=ok)
        self.text("E / Esc để đóng. Quan hệ tốt = giá ổn định hơn.", rect.x + 16, rect.bottom - 24, (150, 160, 150), self.small)

    def panel_research(self, game):
        keys = list(RESEARCHES.keys())
        rect = self.open_panel(game, "Nhà nghiên cứu - Sinh học & Kỹ năng & Giáp", 620, 70 + 52 * len(keys))
        y = rect.y + 40
        for key in keys:
            info = RESEARCHES[key]
            done = key in game.researched
            req_ok = not info.get("requires") or info["requires"] in game.researched
            ok = not done and req_ok and game.can_afford(info["cost"])
            col = (140, 220, 140) if done else (200, 200, 210) if ok else (140, 140, 150)
            status = " [ĐÃ HỌC]" if done else ""
            self.text(f"{info['name']}{status}", rect.x + 16, y, col)
            self.text(info["desc"], rect.x + 16, y + 18, (170, 175, 185), self.small)
            cost_s = self.cost_str(info["cost"])
            self.text(cost_s, rect.x + 360, y + 4, (220, 200, 140), self.small)
            if not done:
                self.button((rect.right - 100, y + 4, 84, 28), "Nghiên cứu", ("research", key), enabled=ok)
            y += 52

    def panel_trainer(self, game):
        n = max(len(game.refugees), 1)
        h = 120 + max(22 * n, 30 * len(SKILLS))
        rect = self.open_panel(game, "Nhà huấn luyện - đổi nghề", 640, h)
        sel = game.sel_ref if game.sel_ref in game.refugees else None
        game.sel_ref = sel
        self.text("Chọn người:", rect.x + 16, rect.y + 44, (190, 200, 190), self.small)
        if not game.refugees:
            self.text("Chưa có ai trong căn cứ.", rect.x + 16, rect.y + 70, (170, 170, 170), self.small)
        for i, r in enumerate(game.refugees):
            self.button((rect.x + 16, rect.y + 66 + i * 22, 270, 20), f"{r.name} - {r.info['name']} Lv{r.level}",
                        ("pick", r), active=r is sel)
        self.text(f"Nghề mới (mất 1/2 kinh nghiệm, {self.cost_full(RETRAIN_COST)}):", rect.x + 310, rect.y + 44,
                  (190, 200, 190), self.small)
        ok_cost = game.can_afford(RETRAIN_COST)
        for i, (key, sk) in enumerate(SKILLS.items()):
            self.button((rect.x + 310, rect.y + 66 + i * 30, 314, 26), f"{sk['name']} - {sk['desc']}", ("skill", key),
                        active=sel is not None and sel.skill == key,
                        enabled=sel is not None and sel.skill != key and ok_cost)

    # ----- menu tạm dừng & màn hình kết thúc -----
    def draw_pause(self, game):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        self.screen.blit(ov, (0, 0))
        rect = pygame.Rect(VIEW_W / 2 - 170, VIEW_H / 2 - 150, 340, 300)
        pygame.draw.rect(self.screen, (28, 30, 38), rect, border_radius=8)
        pygame.draw.rect(self.screen, (170, 175, 190), rect, 2, border_radius=8)
        self.text("TẠM DỪNG", rect.centerx - self.font.size("TẠM DỪNG")[0] / 2, rect.y + 14, (255, 235, 150))
        self.button((rect.x + 40, rect.y + 56, 260, 36), "Tiếp tục (Space)", ("resume",), font=self.font)
        self.text("Tốc độ game:", rect.x + 40, rect.y + 108, (200, 205, 195), self.small)
        for i, n in enumerate(GAME_SPEEDS):
            self.button((rect.x + 40 + i * 90, rect.y + 132, 80, 32), f"{n}x", ("speed", n), active=game.speed == n,
                        font=self.font)
        self.button((rect.x + 40, rect.y + 188, 260, 36), "Chơi lại (từ đầu)", ("restart",), font=self.font)
        self.button((rect.x + 40, rect.y + 236, 260, 36), "Thoát game", ("quit",), font=self.font)

    def draw_game_over(self, game):
        ov = pygame.Surface((W, H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        self.screen.blit(ov, (0, 0))
        title = "CĂN CỨ ĐÃ SỤP ĐỔ" if game.core.hp <= 0 else "BẠN ĐÃ BỊ CẮN!"
        self.centered(title, VIEW_H / 2 - 60, (224, 80, 58), self.big)
        self.centered(f"Bạn sống sót đến ngày {game.day}. Nhấn R để chơi lại.", VIEW_H / 2 + 10)
