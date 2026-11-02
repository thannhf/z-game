"""Điểm vào. Chạy:  python main.py   (cần: pip install pygame)"""
import sys

import pygame

from settings import VIEW_W, VIEW_H, FPS, TOOL_KEYS, SAVE_FILE
import os
from game import Game


def main():
    pygame.init()
    screen = pygame.display.set_mode((VIEW_W, VIEW_H))
    pygame.display.set_caption("Zombie Base - Survival")
    clock = pygame.time.Clock()
    game = Game(screen)
    if os.path.isfile(SAVE_FILE):
        game.say(f"Tìm thấy {SAVE_FILE} - Ctrl+L để nạp, Ctrl+S để lưu.", 6)
    key_tool = {}
    for t, k in TOOL_KEYS.items():
        try:
            key_tool[pygame.key.key_code(k)] = t
        except ValueError:
            print(f"Cảnh báo: phím không hợp lệ cho {t}: {k!r}")
    speed_keys = {pygame.K_F1: 1, pygame.K_F2: 2, pygame.K_F3: 3}
    ui_hold = False      # cú bấm chuột đang giữ đã bị giao diện nuốt (không được bắn/xây theo)
    while True:
        dt = min(clock.tick(FPS) / 1000, 0.05)
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_SPACE, pygame.K_p) and not game.over:
                    game.paused = not game.paused
                elif e.key == pygame.K_ESCAPE:
                    if game.panel:
                        game.panel = None
                    elif not game.over:
                        game.paused = not game.paused
                elif game.paused:
                    pass                                   # đang tạm dừng: bỏ qua các phím khác
                elif e.key in speed_keys:
                    game.set_speed(speed_keys[e.key])
                elif e.key in key_tool:
                    game.player.tool = key_tool[e.key]
                elif e.key == pygame.K_q:
                    game.player.cycle_weapon(game)
                elif e.key == pygame.K_e and not game.over:
                    game.interact()
                elif e.key == pygame.K_f and not game.over and not game.paused:
                    game.player.try_mount(game)
                elif e.key == pygame.K_F4 and not game.over:
                    # Ngả theo phe gần nhất (hoặc trung lập nếu không gần ai)
                    fid = game.nearest_faction_base(game.player.x, game.player.y, max_dist=160)
                    if fid:
                        game.declare_allegiance(fid)
                    else:
                        game.declare_allegiance(None)
                        game.say("Lại gần căn cứ 1 phe rồi bấm F4 để ngả theo (hoặc trung lập).", 3)
                elif e.key == pygame.K_z:
                    game.show_routes = not game.show_routes
                elif e.key == pygame.K_TAB and not game.over:
                    game.hud.tools_collapsed = not game.hud.tools_collapsed
                elif e.key == pygame.K_n and game.phase == "day" and not game.over:
                    game.start_night()
                if e.key == pygame.K_r and game.over:
                    game.reset()
                elif e.key == pygame.K_s and (pygame.key.get_mods() & pygame.KMOD_CTRL) and not game.over:
                    game.save_game()
                elif e.key == pygame.K_l and (pygame.key.get_mods() & pygame.KMOD_CTRL) and not game.over:
                    game.load_game()
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                ui_hold = game.hud.click(game, e.pos)
            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
                ui_hold = False
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3 and not game.over \
                    and not game.paused and not game.panel:
                wx, wy = game.screen_to_world(e.pos)
                game.player.demolish(game, wx, wy)
        if game.want_quit:
            pygame.quit()
            sys.exit()
        mouse_pos = pygame.mouse.get_pos()
        mouse_down = pygame.mouse.get_pressed()[0] and not ui_hold and not game.paused and not game.panel
        if not game.paused:
            for _ in range(game.speed):                    # tốc độ 2x/3x = chạy nhiều bước nhỏ (đạn không xuyên tường)
                game.update(dt, pygame.key.get_pressed(), mouse_pos, mouse_down)
        game.draw(mouse_pos)
        pygame.display.flip()


if __name__ == "__main__":
    main()
