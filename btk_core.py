# -*- coding: utf-8 -*-
"""BTK 计算核心（纯计算层，无 UI）。

从 btk_calculator.py 抽取，仅保留数据访问与计算逻辑，供 Web UI 后端调用。
底层运算逻辑与原版完全一致，未做任何改动。
"""
import math

from btk_data import WEAPONS, ARMOR_KEYS, ARMORS, TARGETS, DAMAGE_TYPES

INF = float("inf")

# 与旧 UI 一致的派生数据
CATEGORIES = []
for w in WEAPONS:
    if w["category"] not in CATEGORIES:
        CATEGORIES.append(w["category"])
CATEGORIES_MAIN = [c for c in CATEGORIES if c != "自定义武器"]
WEAPONS_BY_CAT = {c: [w for w in WEAPONS if w["category"] == c] for c in CATEGORIES_MAIN}

ARMOR_DISPLAY = list(ARMOR_KEYS.keys())
TARGET_DISPLAY = list(TARGETS.keys())
PARTS = [("头部", "head"), ("躯干", "torso"), ("手臂", "arms"), ("腿部", "legs")]


def per_shot_damage(weapon, armor_mult, armor_caps, part_mult, part_cap, boost, charged):
    total = 0.0
    for t in DAMAGE_TYPES:
        d = weapon["damage"][t] * (1 + boost)
        d *= armor_mult[t]
        c = armor_caps.get(t)
        if c and c > 0:
            d = min(d, c)
        total += d
    total *= weapon["mult"] * weapon["pellet"]
    if charged and weapon["alphaCharged"] is not None:
        total *= weapon["chargeDM"] or 1.0
    total *= part_mult
    if part_cap and part_cap > 0:
        total = min(total, part_cap)
    return total


def calc(weapon, armor_key, target, part_key, boost, charged):
    am = ARMORS[ARMOR_KEYS[armor_key]]
    dmg = per_shot_damage(weapon, am["mult"], am.get("caps", {}),
                          target["parts"][part_key], target.get("cap"), boost, charged)
    health = target["health"]
    rpm = weapon["fireRate"] or 0
    btk = math.ceil(health / dmg) if dmg > 0 else INF
    ttk_ms = ((btk - 1) * 60 / rpm) * 1000 if rpm > 0 and btk != INF else INF
    dps = dmg * rpm / 60 if rpm > 0 else 0
    return {"dmg": dmg, "btk": btk, "ttk_ms": ttk_ms, "dps": dps, "health": health}


def fmt_btk(n):
    return "∞" if n == INF else str(int(n))


def fmt_ms(v):
    return "∞" if v == INF else "%d ms" % round(v)


def is_charge_weapon(w):
    return w is not None and w.get("alphaCharged") is not None and "蓄力" in w.get("flags", "")


def get_weapon_by_name(name):
    for w in WEAPONS:
        if w["name"] == name:
            return w
    return None


def make_custom_weapon(dmg, rpm, pellet, dtype):
    """自定义武器（与原 UI 行为一致）。"""
    dmgmap = {t: 0.0 for t in DAMAGE_TYPES}
    dmgmap["DamagePhysical" if dtype == "物理" else "DamageEnergy"] = max(0.0, dmg)
    return {"name": "自定义武器", "category": "自定义武器", "fireRate": max(0.0, rpm),
            "heatPerShot": 0.0, "damage": dmgmap, "pellet": max(1, int(pellet)), "mult": 1.0,
            "alpha": max(0.0, dmg) * max(1, int(pellet)), "alphaCharged": None,
            "chargeTime": None, "chargeDM": None, "chargeBurst": None, "dps": None,
            "flags": "常规", "note": "", "is_custom": True}


def make_custom_target(health, head, torso, arms, legs, armor_key):
    return {"health": float(health),
            "parts": {"head": float(head), "torso": float(torso),
                      "arms": float(arms), "legs": float(legs)},
            "armor": armor_key, "cap": None}
