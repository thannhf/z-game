# Zombie Base

Sinh tồn xây căn cứ phòng thủ (pygame).

    pip install pygame
    python main.py

## Điều khiển
- WASD: di chuyển
- 1 Súng | 2 Tường | 3 Tháp súng | 4 Mỏ đá (xây trên ô đá) | 5 Nhà ở | 6 Khai thác/Thu hoạch
- 7 Nông trại | 8 Kho gỗ | 9 Kho đá | 0 Kho lương thực
- M Nhà máy gỗ (xây trên ô cây) | G Cổng | U Nâng cấp
- Nâng cấp (U): Click vào công trình. Tường -> Tường đá. Tháp súng -> Tháp bắn nhanh (Click)
  hoặc Tháp tầm xa (Shift+Click). Di chuột lên công trình để xem giá.
- Chuột trái: dùng công cụ (giữ để bắn/xây liên tục), chuột phải: phá công trình (hoàn 50%)
- N: gọi đêm đến sớm, R: chơi lại
- Q: đổi súng | E: tương tác với Xưởng vũ khí / Nhà huấn luyện / Chợ ở gần (hoặc bấm Esc/E để đóng)
- V Xưởng vũ khí | H Nhà huấn luyện | C Chợ | B Chuồng bò
- Z: hiện đường zombie sẽ đi (để thiết kế mê cung) | Space/P/Esc: tạm dừng | F1/F2/F3 hoặc nút góc phải: tốc độ 1x/2x/3x

## Cấu trúc (mỗi đối tượng một file)
    main.py              vòng lặp chính, nhận phím/chuột
    settings.py          hằng số, danh sách tài nguyên, thứ tự công cụ
    game.py              thế giới, ngày/đêm, sinh zombie & người tị nạn
    hud.py               giao diện
    pathfinding.py       tìm đường BFS cho người tị nạn
    utils.py             hàm tiện ích
    entities/
      player.py          người chơi, công cụ, xây/phá
      building.py        BUILDINGS (dữ liệu) + hành vi tháp súng, nhà máy sản xuất
      zombie.py          ZOMBIES (dữ liệu) + AI zombie
      refugee.py         người tị nạn: di chuyển, vòng đời
      skills.py          SKILLS: kỹ năng ngẫu nhiên của người tị nạn
      animal.py          ANIMALS (dữ liệu) + hành vi động vật (bò)
      weapons.py         WEAPONS: súng lục, shotgun, súng trường
      bullet.py          đạn (có xuyên, tầm bay)
      resource_node.py   cây / mỏ đá trên bản đồ

## Mở rộng
- Công trình mới: thêm mục vào BUILDINGS (building.py) và tên vào TOOL_ORDER (settings.py).
  Hành vi riêng: viết hàm (b, game, dt) và đăng ký vào BEHAVIORS.
  Có thể dùng on_node để buộc xây trên ô tài nguyên (như mỏ đá).
- Kỹ năng mới: viết hàm act(r, game, dt) trong skills.py và thêm vào SKILLS.
- Zombie mới: thêm vào ZOMBIES, chọn trong Game.pick_zombie().
- Tài nguyên mới: thêm vào RESOURCES (settings.py, có start và cap) + một kho trong BUILDINGS (store, store_amount).
- Động vật mới: thêm vào ANIMALS (animal.py), sinh bằng Game.spawn_animal(kind).

Nhà ở (sức chứa 2) quyết định số người tị nạn nhận được. Ban đêm chỉ xạ thủ thức, còn lại về nhà ngủ.

Cổng (G): người chơi và người tị nạn đi xuyên qua được, zombie thì không (chúng sẽ phá cổng như tường).
Nên bao kín căn cứ bằng tường và chừa cổng thay vì để hở.

Tự mọc lại (SPAWN_RULES trong settings.py): cây, đá và bò mọc thêm theo chu kỳ khi số lượng dưới giới hạn,
đủ giới hạn thì dừng. Đặt batch lớn để mỗi lần mọc cho đủ giới hạn ngay.

## Lương thực, kho, nông trại, săn bắn
- Mỗi tài nguyên có sức chứa cơ bản (RESOURCES[...]["cap"]); xây Kho gỗ / Kho đá / Kho lương thực để nâng sức chứa.
  Đầy kho thì không nhận thêm (mỏ đá tạm dừng, thịt bị bỏ phí...).
- Nông trại: khoai tây tự lớn (26s), chín thì thu hoạch bằng công cụ 6 (Khai thác/Thu hoạch) hoặc để Nông dân lo
  (có nông dân đứng cạnh thì cây lớn nhanh hơn, 10s, và tự thu hoạch).
- Bò đi lang thang trên bản đồ, bắn hạ (người chơi hoặc Thợ săn) được 4 lương thực. Bò mới xuất hiện dần theo thời gian.
- Mỗi sáng mỗi người tị nạn ăn 1 lương thực; thiếu thì mất máu (FOOD_PER_REFUGEE = 0 để tắt).
- Người tị nạn tới đều đặn suốt ban ngày (REFUGEES_PER_DAY, ARRIVAL_LEAD trong settings.py); HUD hiện đếm ngược tới người kế tiếp.
  Chỉ nhận thêm khi còn chỗ ở và chưa vượt MAX_REFUGEES.

## Chiều sâu chiến thuật
- **Zombie biết tìm đường** (pathfinding.zombie_field): chi phí ô trống = 1, cổng = 5, tường gỗ ~21, tường đá ~46 (theo máu hiện tại).
  Có lối hở hoặc cổng thì cả bầy kéo qua đó thay vì đập tường -> dựng mê cung, đặt tháp quanh cổng làm "kill zone".
  Bầy chỉ đâm thẳng tới bạn / người tị nạn khi họ ở gần. Bấm Z để xem đường dự kiến (vòng kín không lối thì chúng đập điểm rẻ nhất).
  Muốn zombie ngại đi vòng hơn/bớt hơn: sửa GATE_COST và hệ số trong zombie_tile_cost (pathfinding.py).
- **Zombie mới** (entities/zombie.py, ZOMBIES + trọng số trong Game.pick_zombie):
  chạy (từ ngày 2, nhanh, 1 máu), bom (từ ngày 3, chạm tường/người thì nổ sau 0.7s, phá cả cụm), cắn (từ ngày 4, đuổi người tị nạn đang thức, cắn đau x2).
- **Boss mỗi 5 đêm** (BOSS_EVERY): rất trâu, đập công trình x2, còn nửa máu thì triệu hồi 5 zombie chạy.
  Hạ boss: BOSS_REWARD (gói tài nguyên) + 1 người tị nạn đặc biệt (xuất phát cấp 4, 50 máu) nếu còn chỗ ở, +10 tinh thần.
- **Vũ khí** (entities/weapons.py): xây Xưởng vũ khí (V), lại gần bấm E để mua bằng gỗ/đá. Q đổi súng.
  Shotgun: 6 viên chùm, tầm ngắn. Súng trường: mỗi lần bấm chuột một phát, 3 sát thương, xuyên 2 zombie, tầm xa.

## Kinh tế và dân cư
- **Tinh thần** (0-100, thanh "Tinh thần"): mỗi sáng cộng/trừ theo ăn uống (đói trừ nặng, ăn no cộng), có đủ nhà không,
  tường/cổng/tháp vững, lõi còn khỏe. Mỗi người chết trừ ngay MORALE_DEATH. >=75 làm x1.2, <40 làm x0.8, <20 làm x0.65;
  dưới 25 thì mỗi sáng 1 người bỏ đi (dưới 10: 2 người). Người đặc biệt không bỏ đi.
- **Cấp kỹ năng**: làm việc thật thì có kinh nghiệm (LEVEL_XP), tối đa cấp 5, mỗi cấp nhanh thêm 20% (chấm vàng dưới chân,
  rê chuột xem). Xạ thủ cấp 4+ bắn 2 sát thương. **Nhà huấn luyện** (H, bấm E): đổi nghề, mất một nửa kinh nghiệm + RETRAIN_COST.
- **Chợ** (C, bấm E): đổi gỗ/đá lấy lương thực và ngược lại theo MARKET_TRADES (tỷ giá cố định, không có lời nếu đổi qua lại). Cần kho nhận còn chỗ.
- **Chuồng bò** (B): chứa tối đa 4 bò (bắt đầu 2, tốn 6 lương thực mua bò giống). Từ 2 con trở lên bò sinh sản (45s/con);
  mỗi con cho thịt đều: thịt/giây tăng theo số bò, không cần săn. Zombie phá chuồng thì mất bò.

## Chất lượng chơi
- Space/P/Esc mở menu tạm dừng (tiếp tục, tốc độ, chơi lại, thoát). Tốc độ 2x/3x chạy nhiều bước nhỏ nên đạn không xuyên tường.
- Thông báo hiện thành nhật ký ở góc trái dưới (tối đa 7 dòng, mờ dần, trùng nội dung thì không lặp).


## Tài nguyên kim loại & mùa & nghiên cứu (mở rộng)
- **Kim loại**: Đồng, Sắt, Bạc, Vàng xuất hiện trên bản đồ (mỏ quặng). Xây **Mỏ đồng/sắt/bạc/vàng** trên đúng ô quặng (phím F1–F4).
  Xây **Kho đồng/sắt/bạc/vàng** (F5–F8) để tăng sức chứa.
- **Giáp trụ**: Nghiên cứu tại **Nhà nghiên cứu** (phím R, bấm E khi gần) — Giáp cơ bản (-20% sát thương), Giáp nâng cao (-35%).
- **Ngựa & Chó**: Động vật hoang trên bản đồ. Xây **Chuồng ngựa** (J) và **Chuồng chó** (K).
  Ngựa trong chuồng tăng tốc độ di chuyển của bạn; chó thỉnh thoảng sủa làm chậm zombie gần chuồng.
- **Bốn mùa** (Xuân → Hạ → Thu → Đông, mỗi mùa 3 ngày):
  - Xuân: cây lớn nhanh, động vật nhanh, zombie hơi chậm, sản xuất tốt.
  - Hạ: nóng, động vật nhanh, zombie hơi hung.
  - Thu: mỏ/nhà máy hiệu quả cao.
  - Đông: sinh trưởng chậm, động vật & zombie chậm (dễ săn/đánh).
- **Nhà nghiên cứu**: Sinh học cường hóa (+HP), Thể lực (+tốc độ), Phương pháp huấn luyện (+XP kỹ năng),
  Kỹ thuật khai thác (mỏ kim loại nhanh hơn), Thuần hóa nâng cao (ngựa/chó mạnh hơn).
- **Nhà huấn luyện** (H) vẫn dùng để đổi nghề người tị nạn như trước.


## Cập nhật mới
- **Đá lát sàn** (phím T): lát nền, cây/quặng **không mọc** trên ô đã lát. Đi xuyên qua được.
- **Nhà cấp 1→5** (công cụ Nâng cấp U): sức chứa 2→6 người, máu tăng dần.
- **Súng cấp 1→5**: mua/nâng tại Xưởng vũ khí (V + E). Thêm SMG, Sniper.
- **Tháp mới**: Minigun, Bắn tỉa (nâng từ tháp nhanh/xa), Tháp lửa (,), Tháp điện (.).
- **Hàng rào / Cổng sắt**: tường gỗ → đá → sắt; cổng gỗ → sắt.
- **Mùa thu**: lá vàng rơi, cây chuyển màu vàng.
- **Mùa đông**: tuyết rơi, cây chết dần, động vật hoang giảm.
- **Bản đồ rộng**: 64×40 ô (camera theo bạn).
- **Lưu / Nạp**: Ctrl+S lưu vào `savegame.json`, Ctrl+L nạp lại.

## Bản đồ vùng (cập nhật)
- Bản đồ lớn **96×64** ô.
- **Trung địa** (giữa): vùng mặc định, cây/đá/quặng/động vật như cũ.
- **4 vùng đặc biệt** xung quanh:
  - **Bắc – Bắc cực**: tuyết, tinh thể băng, thịt đông.
  - **Đông – Pháp sư**: tím nhạt, mana, đá rune.
  - **Nam – Núi lửa**: cam đỏ, obsidian, lõi magma, lưu huỳnh.
  - **Tây – Linh hồn**: tím đen, tinh hồn, xương, dịch hồn.
- HUD hiện tên vùng đang đứng. Khi bước sang vùng mới sẽ có thông báo.
- Tài nguyên vùng đặc biệt chỉ mọc chủ yếu đúng biome của chúng.

## 3 Phe AI (Giai đoạn 2 + 3)
- **Chính phủ** (góc Tây-Bắc Trung địa): quân đội, thiên phòng thủ, thiết quân luật.
- **Phiến quân** (góc Đông-Nam): hung hăng, tấn công nhiều hơn.
- **Du mục / Chợ đen** (góc Đông-Bắc): trung lập, buôn bán, có tài nguyên vùng đặc biệt.

### Điều khiển liên quan
- **E** gần căn cứ Du mục: mở **Chợ đen**.
- **F4** gần căn cứ 1 phe: **ngả theo** phe đó (quan hệ thay đổi). F4 ở xa = trung lập.
- Bắn chết lính phe → quan hệ với phe đó giảm.
- HUD góc dưới hiện quan hệ CP / PQ / DM.

### AI
- Unit tuần tra quanh căn cứ, tấn công zombie và unit thù địch gần.
- Chính phủ ↔ Phiến quân giao tranh định kỳ (war_timer).
- Khi chiến tranh: một phần unit lao về căn cứ địch; chợ đen đôi khi tạm đóng.
- AI hồi unit khi thiếu, quyết định tấn công/phòng thủ theo lực lượng + quan hệ.
