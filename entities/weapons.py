"""Vũ khí của người chơi. Mỗi súng có 5 cấp (nâng cấp tại Xưởng vũ khí).

  cost     giá mua / nâng cấp
  rate     giây giữa hai lần bắn
  auto     True: giữ chuột để bắn liên tục; False: mỗi lần bấm chuột một phát
  pellets  số viên mỗi phát, spread: độ tản (radian), life: thời gian bay (= tầm bắn)
  pierce   số zombie đạn xuyên qua thêm
  level    cấp hiện tại (1..5)
"""
# Cấp cơ bản (level 1). Nâng cấp tăng dmg/rate/pierce.
WEAPON_BASE = {
    "pistol":  dict(name="Súng lục", cost={}, rate=0.15, auto=True, dmg=1, pellets=1,
                    spread=0.04, life=1.0, pierce=0, speed=620,
                    desc="Súng mặc định, bắn liên tục"),
    "shotgun": dict(name="Shotgun", cost={"wood": 25, "stone": 15}, rate=0.75, auto=True, dmg=1,
                    pellets=6, spread=0.30, life=0.34, pierce=0, speed=560,
                    desc="6 viên đạn chùm, tầm ngắn"),
    "rifle":   dict(name="Súng trường", cost={"wood": 15, "stone": 30}, rate=0.5, auto=False, dmg=3,
                    pellets=1, spread=0.01, life=1.3, pierce=1, speed=900,
                    desc="Bắn từng phát, sát thương cao, tầm xa"),
    "smg":     dict(name="SMG", cost={"copper": 12, "iron": 8}, rate=0.08, auto=True, dmg=1,
                    pellets=1, spread=0.08, life=0.7, pierce=0, speed=700,
                    desc="Bắn cực nhanh, sát thương thấp"),
    "sniper":  dict(name="Sniper", cost={"iron": 15, "silver": 5, "copper": 8}, rate=1.1, auto=False, dmg=6,
                    pellets=1, spread=0.005, life=1.8, pierce=2, speed=1100,
                    desc="Sát thương cực cao, xuyên nhiều, tầm rất xa"),
}

WEAPON_ORDER = ["pistol", "shotgun", "rifle", "smg", "sniper"]

# Chi phí nâng cấp từ cấp n -> n+1 (n=1..4)
UPGRADE_COST = {
    1: {"wood": 10, "stone": 8},
    2: {"wood": 12, "stone": 10, "copper": 4},
    3: {"iron": 8, "copper": 6, "stone": 10},
    4: {"iron": 12, "silver": 4, "copper": 8},
}


def weapon_stats(kind, level=1):
    """Trả về dict stats đã áp dụng cấp (1..5)."""
    base = WEAPON_BASE[kind]
    lvl = max(1, min(5, level))
    d = dict(base)
    d["level"] = lvl
    d["dmg"] = base["dmg"] + (lvl - 1) * (1 if base["dmg"] <= 2 else 1)
    d["rate"] = max(0.05, base["rate"] * (1.0 - 0.08 * (lvl - 1)))
    d["pierce"] = base["pierce"] + (lvl - 1) // 2
    d["life"] = base["life"] * (1.0 + 0.06 * (lvl - 1))
    d["name"] = f"{base['name']} Lv.{lvl}"
    return d


# Compatibility: WEAPONS[kind] = level 1 stats
WEAPONS = {k: weapon_stats(k, 1) for k in WEAPON_BASE}
