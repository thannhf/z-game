"""Hằng số và dữ liệu dùng chung cho toàn game."""
TILE, COLS, ROWS = 32, 128, 88   # large map: heartland + 6 regions + 4 seas
VIEW_W, VIEW_H = 1280, 768
W, H = TILE * COLS, TILE * ROWS
FPS = 60

# ----- Biomes -----
BIOMES = {
    "middle": dict(
        name="Trung địa",
        color=(34, 46, 30),
        grid=(38, 52, 34),
        color_winter=(50, 60, 70),
        grid_winter=(55, 65, 75),
        color_autumn=(42, 48, 28),
        grid_autumn=(50, 55, 32),
        danger=0.0,
        desc="Central safe zone. Your base and the factions live here.",
    ),
    "wizard": dict(
        name="Vùng Pháp sư",
        color=(55, 50, 75),
        grid=(70, 65, 95),
        color_winter=(60, 55, 80),
        grid_winter=(75, 70, 100),
        color_autumn=(50, 45, 70),
        grid_autumn=(65, 60, 90),
        danger=0.35,
        desc="Magic mist and glowing trees. Home to mages and golems.",
    ),
    "volcano": dict(
        name="Vùng Núi lửa",
        color=(55, 28, 18),
        grid=(75, 40, 25),
        color_winter=(50, 30, 22),
        grid_winter=(70, 42, 28),
        color_autumn=(60, 32, 20),
        grid_autumn=(80, 45, 28),
        danger=0.55,
        desc="Hot ground, lava and ash. Magma beasts and fire drakes.",
    ),
    "arctic": dict(
        name="Vùng Bắc cực",
        color=(45, 60, 80),
        grid=(60, 80, 100),
        color_winter=(70, 85, 105),
        grid_winter=(90, 105, 125),
        color_autumn=(50, 65, 85),
        grid_autumn=(65, 80, 100),
        danger=0.45,
        desc="Snow, ice and cold winds. Frost wolves and ice drakes.",
    ),
    "spirit": dict(
        name="Vùng Linh hồn",
        color=(30, 25, 40),
        grid=(45, 38, 55),
        color_winter=(35, 30, 48),
        grid_winter=(50, 42, 60),
        color_autumn=(28, 22, 38),
        grid_autumn=(42, 35, 52),
        danger=0.50,
        desc="Fog and shadows. Specters and the restless dead.",
    ),
    "tropical": dict(
        name="Rừng nhiệt đới",
        color=(28, 70, 32),
        grid=(40, 95, 45),
        color_winter=(32, 65, 38),
        grid_winter=(45, 85, 50),
        color_autumn=(35, 75, 30),
        grid_autumn=(50, 90, 40),
        danger=0.40,
        desc="Dense humid jungle full of predators and giant trees.",
    ),
    "rainforest": dict(
        name="Rừng mưa",
        color=(18, 55, 40),
        grid=(30, 80, 55),
        color_winter=(22, 50, 45),
        grid_winter=(35, 70, 60),
        color_autumn=(25, 58, 38),
        grid_autumn=(38, 75, 50),
        danger=0.42,
        desc="Misty rainforest with vines, toxins and rare herbs.",
    ),
}

BIOME_EFFECTS = {
    "middle":     dict(dmg_per_sec=0,   speed_mult=1.0,  vision_mult=1.0, shake=0,   overlay=None, label=""),
    "volcano":    dict(dmg_per_sec=2.5, speed_mult=0.92, vision_mult=0.9, shake=0.4, overlay=(180, 40, 10, 35), label="Nóng bức!"),
    "arctic":     dict(dmg_per_sec=1.8, speed_mult=0.85, vision_mult=0.95, shake=0,  overlay=(80, 140, 200, 40), label="Lạnh cóng!"),
    "spirit":     dict(dmg_per_sec=1.2, speed_mult=0.90, vision_mult=0.75, shake=0.6, overlay=(40, 10, 60, 50), label="Sợ hãi..."),
    "wizard":     dict(dmg_per_sec=0.4, speed_mult=1.0,  vision_mult=0.85, shake=0.2, overlay=(90, 60, 160, 30), label="Sương phép"),
    "tropical":   dict(dmg_per_sec=0.8, speed_mult=0.88, vision_mult=0.9, shake=0,   overlay=(20, 80, 30, 28), label="Nóng ẩm"),
    "rainforest": dict(dmg_per_sec=0.6, speed_mult=0.86, vision_mult=0.8, shake=0,   overlay=(10, 50, 40, 40), label="Sương rừng"),
}

REGION_BOSSES = {
    "wizard":     dict(name="Archmage Cổ", r=20, hp=80, speed=38, dmg=18, color=(160, 120, 255),
                       defense="shield", shield_hp=40, spawn_adds=2, reward={"mana": 8, "runestone": 5, "wood": 15}),
    "volcano":    dict(name="Rồng Núi Lửa",    r=22, hp=100, speed=32, dmg=22, color=(255, 80, 20),
                       defense="armor", armor=0.35, spawn_adds=3, reward={"obsidian": 6, "sulfur": 8, "stone": 20}),
    "arctic":     dict(name="Vua Băng",         r=21, hp=90, speed=36, dmg=20, color=(150, 220, 255),
                       defense="freeze", freeze_chance=0.25, spawn_adds=2, reward={"ice_crystal": 8, "frozen_meat": 6, "food": 15}),
    "spirit":     dict(name="Chúa Tể Linh Hồn",    r=20, hp=85, speed=40, dmg=19, color=(100, 40, 140),
                       defense="phase", phase_cd=4.0, spawn_adds=2, reward={"soul_essence": 7, "bone": 10, "ectoplasm": 5}),
    "tropical":   dict(name="Thú Chúa Rừng",    r=22, hp=95, speed=45, dmg=21, color=(40, 140, 50),
                       defense="regen", regen=3.0, spawn_adds=3, reward={"wood": 25, "food": 12, "fruit": 8}),
    "rainforest": dict(name="Hồn Rừng Mưa", r=19, hp=88, speed=42, dmg=18, color=(30, 100, 80),
                       defense="poison", poison_dps=4.0, spawn_adds=2, reward={"wood": 20, "herb": 10, "food": 10}),
}

MIDDLE_RATIO = 0.42
TERRAIN = {
    "none":     dict(name="",          color=None,              block=False, slow=1.0,  buildable=True),
    "mountain": dict(name="Núi",  color=(90, 85, 80),      block=True,  slow=0.0,  buildable=False),
    "sea":      dict(name="Biển",       color=(25, 55, 110),     block=True,  slow=0.0,  buildable=False),
    "river":    dict(name="Sông",     color=(40, 90, 150),     block=True,  slow=0.0,  buildable=False),
    "lake":     dict(name="Hồ",      color=(35, 80, 140),     block=True,  slow=0.0,  buildable=False),
    "pond":     dict(name="Ao",      color=(45, 100, 130),    block=True,  slow=0.0,  buildable=False),
    "lava":     dict(name="Dung nham",      color=(220, 80, 20),     block=True,  slow=0.0,  buildable=False, hazard=True),
    "road":     dict(name="Đường",      color=(110, 100, 85),    block=False, slow=1.35, buildable=True),
    "bridge":   dict(name="Cầu",    color=(140, 110, 70),    block=False, slow=1.15, buildable=False),
    "port":     dict(name="Cảng biển",      color=(90, 100, 120),    block=False, slow=1.1,  buildable=False),
    "tunnel":   dict(name="Đường hầm",    color=(55, 50, 45),      block=False, slow=1.2,  buildable=False),
    "red_line": dict(name="Đường đỏ",  color=(160, 40, 40),     block=True,  slow=0.0,  buildable=False),
    "rail":     dict(name="Đường tàu",      color=(70, 65, 60),      block=False, slow=1.5,  buildable=False),
}

SEA_SIDES = ("north", "east", "south", "west")
SEA_NAMES = {
    "north": "Biển Bắc",
    "east":  "Biển Đông",
    "south": "Biển Nam",
    "west":  "Biển Tây",
}

# Núi lửa phun trào
VOLCANO_ERUPT_INTERVAL = (35, 55)   # giây giữa các lần phun (min, max)
VOLCANO_ERUPT_DURATION = 8.0        # thời gian phun
VOLCANO_ERUPT_RADIUS = 5            # bán kính ô bị ảnh hưởng
VOLCANO_ERUPT_DMG = 12              # sát thương / giây khi đứng trong vùng phun

DAY_LEN = 45            # giây ban ngày
BUILD_RANGE = 220       # tầm xây / khai thác quanh người chơi
MAX_REFUGEES = 10

# Người tị nạn tới ĐỀU ĐẶN suốt ban ngày: mỗi ngày có REFUGEES_PER_DAY người (cứ 4 ngày thêm 1, tối đa 5),
# chia đều thành các mốc cách nhau một khoảng; người cuối tới trước khi đêm xuống ARRIVAL_LEAD giây.
REFUGEES_PER_DAY = 3
ARRIVAL_LEAD = 12

# Lương thực: mỗi sáng mỗi người tị nạn ăn FOOD_PER_REFUGEE; ai không có ăn mất STARVE_DMG máu.
# Đặt FOOD_PER_REFUGEE = 0 để tắt cơ chế đói.
FOOD_PER_REFUGEE = 1
STARVE_DMG = 10

HUNT_RANGE = 170        # tầm bắn của thợ săn

# Tự mọc lại: cây, đá, bò, kim loại. Bản đồ khởi đầu đầy `limit`. Khi số lượng < limit, cứ mỗi `interval` giây
# mọc thêm tối đa `batch` (không bao giờ vượt `limit`). Đặt batch lớn (vd 999) = mỗi lần mọc cho đủ limit ngay.
SPAWN_RULES = {
    "wood":    dict(type="node",   limit=90, interval=12, batch=3),
    "stone":   dict(type="node",   limit=50, interval=20, batch=2),
    "copper":  dict(type="node",   limit=22, interval=28, batch=1),
    "iron":    dict(type="node",   limit=18, interval=32, batch=1),
    "silver":  dict(type="node",   limit=10, interval=45, batch=1),
    "gold":    dict(type="node",   limit=6,  interval=60, batch=1),
    # Tài nguyên vùng đặc biệt (số lượng ít hơn, mọc chậm hơn)
    "mana":        dict(type="node", limit=14, interval=35, batch=1),
    "runestone":   dict(type="node", limit=10, interval=40, batch=1),
    "obsidian":    dict(type="node", limit=12, interval=38, batch=1),
    "magma_core":  dict(type="node", limit=6,  interval=55, batch=1),
    "sulfur":      dict(type="node", limit=14, interval=32, batch=1),
    "ice_crystal": dict(type="node", limit=12, interval=40, batch=1),
    "frozen_meat": dict(type="node", limit=10, interval=35, batch=1),
    "soul_essence":dict(type="node", limit=8,  interval=50, batch=1),
    "bone":        dict(type="node", limit=16, interval=30, batch=1),
    "ectoplasm":   dict(type="node", limit=8,  interval=48, batch=1),
    "cow":     dict(type="animal", limit=8,  interval=30, batch=1),
    "horse":   dict(type="animal", limit=4,  interval=50, batch=1),
    "dog":     dict(type="animal", limit=5,  interval=40, batch=1),
}

# Thêm tài nguyên mới ở đây.  start = số lượng khởi đầu, cap = sức chứa cơ bản
# (mỗi kho tương ứng cộng thêm sức chứa, xem BUILDINGS).
RESOURCES = {
    "wood":    dict(name="Gỗ",       color=(110, 190, 110), node_color=(60, 130, 60),   start=20, cap=40),
    "stone":   dict(name="Đá",       color=(175, 175, 190), node_color=(130, 130, 140), start=20, cap=40),
    "food":    dict(name="Lương thực", color=(235, 170, 80), start=10, cap=30),
    "copper":  dict(name="Đồng",     color=(200, 140, 70),  node_color=(160, 100, 50),  start=0,  cap=25),
    "iron":    dict(name="Sắt",      color=(160, 165, 175), node_color=(110, 115, 125), start=0,  cap=20),
    "silver":  dict(name="Bạc",      color=(210, 220, 235), node_color=(170, 180, 195), start=0,  cap=15),
    "gold":    dict(name="Vàng",     color=(240, 200, 70),  node_color=(200, 160, 40),  start=0,  cap=10),
    # Tài nguyên vùng đặc biệt
    "mana":       dict(name="Tinh thể Mana", color=(180, 140, 255), node_color=(140, 100, 220), start=0, cap=20),
    "runestone":  dict(name="Đá rune",     color=(200, 190, 230), node_color=(160, 150, 200), start=0, cap=15),
    "obsidian":   dict(name="Obsidian",    color=(40, 30, 50),    node_color=(25, 20, 35),    start=0, cap=18),
    "magma_core": dict(name="Magma Core",   color=(255, 100, 40),  node_color=(200, 60, 20),   start=0, cap=12),
    "sulfur":     dict(name="Sulfur",   color=(220, 210, 80),  node_color=(180, 170, 50),  start=0, cap=20),
    "ice_crystal":dict(name="Tinh thể băng", color=(160, 220, 255), node_color=(120, 180, 230), start=0, cap=18),
    "frozen_meat":dict(name="Thịt đông",   color=(180, 200, 220), node_color=(140, 160, 180), start=0, cap=25),
    "soul_essence":dict(name="Tinh hồn",   color=(160, 80, 200),  node_color=(120, 50, 160),  start=0, cap=15),
    "bone":       dict(name="Xương",       color=(220, 210, 190), node_color=(180, 170, 150), start=0, cap=25),
    "ectoplasm":  dict(name="Dịch hồn",    color=(100, 220, 180), node_color=(60, 170, 140),  start=0, cap=15),
    "fruit":      dict(name="Trái cây",    color=(255, 140, 60),  node_color=(200, 100, 40),  start=0, cap=30),
    "herb":       dict(name="Thảo dược",   color=(80, 200, 100),  node_color=(50, 160, 70),   start=0, cap=25),
}

# Biome ưu tiên cho từng loại node (spawn sẽ cố gắng đặt đúng vùng)
NODE_BIOME = {
    "wood":        "middle",
    "stone":       "middle",
    "copper":      "middle",
    "iron":        "middle",
    "silver":      "middle",
    "gold":        "middle",
    "mana":        "wizard",
    "runestone":   "wizard",
    "obsidian":    "volcano",
    "magma_core":  "volcano",
    "sulfur":      "volcano",
    "ice_crystal": "arctic",
    "frozen_meat": "arctic",
    "soul_essence":"spirit",
    "bone":        "spirit",
    "ectoplasm":   "spirit",
    "fruit":       "tropical",
    "herb":        "rainforest",
}

# Công cụ nhân vật (chiến đấu / cá nhân) — thanh riêng bên trái
CHAR_TOOLS = ["gun", "gather", "upgrade"]
# Công cụ xây dựng — chọn bằng chuột trên thanh xây
BUILD_TOOLS = ["wall", "turret", "quarry", "house",
               "farm", "wood_store", "stone_store", "food_store",
               "sawmill", "gate", "armory", "trainer", "market", "pen",
               "copper_mine", "iron_mine", "silver_mine", "gold_mine",
               "copper_store", "iron_store", "silver_store", "gold_store",
               "research", "stable", "kennel", "floor", "turret_flame", "turret_shock",
               "factory_motor", "factory_car", "factory_apc", "factory_tank",
               "factory_heli", "factory_plane", "station", "rail"]
TOOL_ORDER = CHAR_TOOLS + BUILD_TOOLS
TOOL_LABELS_EXTRA = {
    "factory_motor": "Xưởng xe máy", "factory_car": "Nhà máy ô tô",
    "factory_apc": "Xe bọc thép", "factory_tank": "Nhà máy tăng",
    "factory_heli": "Trực thăng", "factory_plane": "Máy bay",
    "station": "Ga tàu", "rail": "Đường tàu",
}
TOOL_KEYS = {"gun": "1", "wall": "2", "turret": "3", "quarry": "4", "house": "5", "gather": "6",
             "farm": "7", "wood_store": "8", "stone_store": "9", "food_store": "0",
             "sawmill": "m", "gate": "g", "upgrade": "u",
             "armory": "v", "trainer": "h", "market": "c", "pen": "b",
             "copper_mine": "f5", "iron_mine": "f6", "silver_mine": "f7", "gold_mine": "f8",
             "copper_store": "f9", "iron_store": "f10", "silver_store": "f11", "gold_store": "f12",
             "research": "r", "stable": "j", "kennel": "k", "floor": "t",
             "turret_flame": ",", "turret_shock": "."}
TOOL_LABELS = {"gun": "Súng", "gather": "Khai thác", "upgrade": "Nâng cấp",
               "copper_mine": "Mỏ đồng", "iron_mine": "Mỏ sắt", "silver_mine": "Mỏ bạc", "gold_mine": "Mỏ vàng",
               "copper_store": "Kho đồng", "iron_store": "Kho sắt", "silver_store": "Kho bạc", "gold_store": "Kho vàng",
               "research": "Nhà nghiên cứu", "stable": "Chuồng ngựa", "kennel": "Chuồng chó",
               "floor": "Đá lát sàn", "turret_flame": "Tháp lửa", "turret_shock": "Tháp điện",
               "factory_motor": "Xưởng xe máy", "factory_car": "Nhà máy ô tô",
               "factory_apc": "Xe bọc thép", "factory_tank": "Nhà máy tăng",
               "factory_heli": "Trực thăng", "factory_plane": "Máy bay",
               "station": "Ga tàu", "rail": "Ray tàu"}

# Gói trao đổi với lãnh đạo vùng
REGION_TRADE_OFFERS = [
    dict(give={"wood": 20}, get={"food": 10}, label="20 gỗ → 10 lương thực"),
    dict(give={"stone": 15}, get={"wood": 20}, label="15 đá → 20 gỗ"),
    dict(give={"food": 12}, get={"stone": 10}, label="12 lương thực → 10 đá"),
    dict(give={"wood": 30, "stone": 10}, get={"iron": 4}, label="30 gỗ+10 đá → 4 sắt"),
    dict(give={"food": 20}, get={"fruit": 8}, label="20 lương thực → 8 trái cây"),
]

# Boss: cứ BOSS_EVERY đêm lại có một con; hạ nó được gói tài nguyên + một người tị nạn đặc biệt.
BOSS_EVERY = 5
BOSS_REWARD = {"wood": 25, "stone": 20, "food": 12, "copper": 4, "iron": 3}

# Tinh thần dân cư (0..100). Cập nhật mỗi sáng; chết người trừ ngay (MORALE_DEATH).
MORALE_START = 60
MORALE_DEATH = 10

# Chợ: (đưa cái gì, số lượng, nhận cái gì, số lượng). Tỷ giá cố định, không có lời nếu đổi qua đổi lại.
MARKET_TRADES = [
    ("wood", 4, "food", 1),
    ("stone", 3, "food", 1),
    ("food", 1, "wood", 2),
    ("food", 1, "stone", 1),
    ("copper", 3, "iron", 1),
    ("iron", 2, "copper", 3),
    ("silver", 2, "gold", 1),
    ("gold", 1, "silver", 2),
    ("copper", 5, "food", 2),
    ("iron", 4, "food", 2),
]

# Cấp kỹ năng của người tị nạn: kinh nghiệm cần để đạt cấp 1..5; mỗi cấp làm nhanh thêm LEVEL_BONUS.
LEVEL_XP = [0, 25, 70, 140, 240]
LEVEL_BONUS = 0.2
RETRAIN_COST = {"wood": 8, "stone": 8}

GAME_SPEEDS = (1, 2, 3)

# ----- Bốn mùa -----
# Mỗi mùa kéo dài SEASON_DAYS ngày. Hiệu ứng áp dụng lên tốc độ sinh trưởng, động vật, zombie, sản xuất.
SEASON_DAYS = 3
SEASONS = ("xuân", "hạ", "thu", "đông")
SEASON_EFFECTS = {
    "xuân": dict(
        name="Xuân", color=(120, 200, 120),
        grow_mult=1.25,          # cây/nông trại lớn nhanh
        animal_speed=1.1,        # động vật nhanh hơn một chút
        zombie_speed=0.95,       # zombie hơi chậm
        produce_mult=1.1,        # mỏ/nhà máy nhanh hơn
        food_yield=1,            # thưởng thêm lương thực khi thu hoạch
        desc="Cây cối xanh tốt, sinh vật năng động.",
    ),
    "hạ": dict(
        name="Hạ", color=(240, 180, 60),
        grow_mult=1.15,
        animal_speed=1.15,
        zombie_speed=1.05,
        produce_mult=1.0,
        food_yield=0,
        desc="Nóng bức, động vật nhanh, zombie hơi hung hăng.",
    ),
    "thu": dict(
        name="Thu", color=(210, 140, 70),
        grow_mult=1.0,
        animal_speed=1.0,
        zombie_speed=1.0,
        produce_mult=1.15,
        food_yield=1,
        leaf_fall=True,          # lá vàng rơi
        tree_tint=(180, 140, 40), # cây vàng
        desc="Mùa thu hoạch, lá vàng rơi, mỏ hiệu quả cao.",
    ),
    "đông": dict(
        name="Đông", color=(160, 190, 230),
        grow_mult=0.55,
        animal_speed=0.70,
        zombie_speed=0.80,
        produce_mult=0.75,
        food_yield=-1,
        snow=True,               # tuyết rơi
        tree_die_chance=0.08,    # mỗi sáng % cây chết
        animal_die_chance=0.12,  # động vật hoang giảm
        desc="Tuyết rơi, cây chết nhiều, động vật thưa thớt.",
    ),
}

# Nghiên cứu (Nhà nghiên cứu): khóa -> (tên, mô tả, chi phí, hiệu ứng)
# Hiệu ứng được áp dụng một lần khi nghiên cứu xong (game.researched set).
RESEARCHES = {
    "bio_hp": dict(
        name="Sinh học cường hóa",
        desc="+20 HP tối đa cho bạn và người tị nạn",
        cost={"copper": 8, "iron": 6, "food": 10},
    ),
    "bio_speed": dict(
        name="Thể lực tăng cường",
        desc="+15% tốc độ di chuyển người tị nạn & bạn",
        cost={"iron": 10, "copper": 6, "food": 8},
    ),
    "skill_xp": dict(
        name="Phương pháp huấn luyện",
        desc="+30% kinh nghiệm kỹ năng nhận được",
        cost={"silver": 4, "iron": 8, "wood": 15},
    ),
    "armor_basic": dict(
        name="Giáp cơ bản",
        desc="Bạn nhận -20% sát thương (giáp trụ)",
        cost={"iron": 12, "copper": 10, "stone": 15},
    ),
    "armor_adv": dict(
        name="Giáp nâng cao",
        desc="Bạn nhận -35% sát thương (yêu cầu Giáp cơ bản)",
        cost={"iron": 15, "silver": 6, "gold": 2},
        requires="armor_basic",
    ),
    "mine_eff": dict(
        name="Kỹ thuật khai thác",
        desc="Mỏ kim loại sản xuất nhanh hơn 25%",
        cost={"copper": 10, "iron": 8, "stone": 12},
    ),
    "animal_bond": dict(
        name="Thuần hóa nâng cao",
        desc="Ngựa/chó trong chuồng cho lợi ích mạnh hơn",
        cost={"food": 15, "silver": 3, "wood": 10},
    ),
}


SAVE_FILE = "savegame.json"
