# -*- coding: utf-8 -*-
"""Generate btk_data.py from StarBreaker-extracted game records.

数据源：StarBreaker 解包的 Game2.dcb 记录（records 目录，路径结构
`{records}/entities/scitem/weapons/fps_weapons/*.json` 等）。

用法：
    python generate_data.py [records_dir] [output.py]

records_dir 缺省为 `<项目>/game_data/full_extract/libs/foundry/records`。
"""
import json
import os
import re
import sys

DAMAGE_TYPES = ["DamagePhysical", "DamageEnergy", "DamageDistortion",
                "DamageThermal", "DamageBiochemical", "DamageStun"]

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RECORDS = os.path.join(_HERE, "game_data", "full_extract", "libs", "foundry", "records")
OUT = os.path.join(_HERE, "btk_data.py")

# 策展武器表: 文件名(去掉.json) -> 中文名（以官方简中 global.ini 为准，2026-08-08 版）
CURATED = [
    # 步枪
    ("behr_rifle_ballistic_01", "P4-AR 步枪"),
    ("behr_rifle_ballistic_02_civilian", "P8-AR 步枪"),
    ("behr_rifle_ballistic_03", "CQ7 步枪"),
    ("gmni_rifle_ballistic_01", "S71 步枪"),
    ("ksar_rifle_energy_01", "卡纳 步枪"),
    ("klwe_rifle_energy_01", "加伦特 步枪"),
    ("volt_rifle_energy_01", "视差 能量突击步枪"),
    ("none_rifle_multi_01", "绝杀 步枪"),
    ("hdgw_rifle_ballistic_01", "阿灵顿 步枪"),
    # 手枪
    ("behr_pistol_ballistic_01", "S-38 手枪"),
    ("gmni_pistol_ballistic_01", "LH86 手枪"),
    ("ksar_pistol_ballistic_01", "Coda 手枪"),
    ("klwe_pistol_energy_01", "弧光 手枪"),
    ("volt_pistol_energy_01", "脉冲 激光手枪"),
    ("none_pistol_ballistic_01", "三重击 手枪"),
    ("hdgw_pistol_ballistic_01", "齐射 碎片手枪"),
    ("lbco_pistol_energy_01", "尤巴列夫手枪"),
    ("sasu_pistol_toy_01", "惊爆恶徒 玩具手枪"),
    # 冲锋枪
    ("behr_smg_ballistic_01", "P8-SC 冲锋枪"),
    ("gmni_smg_ballistic_01", "C54 冲锋枪"),
    ("klwe_smg_energy_01", "卢敏 V 冲锋枪"),
    ("ksar_smg_energy_01", "监管者 冲锋枪"),
    ("volt_smg_energy_01", "石英 能量冲锋枪"),
    ("none_smg_energy_01", "开膛手 “蔽日” 冲锋枪"),
    # 机枪
    ("behr_lmg_ballistic_01", "FS-9 轻机枪"),
    ("gmni_lmg_ballistic_01", "F55 轻机枪"),
    ("klwe_lmg_energy_01", "德美科 轻机枪"),
    ("volt_lmg_energy_01", "菲涅尔 能量轻机枪"),
    ("none_lmg_ballistic_01", "粉碎者 轻机枪"),
    ("apar_hmg_ballistic_01", "世仇 重机枪"),
    # 霰弹枪
    ("behr_shotgun_ballistic_01", "BR-2 霰弹枪"),
    ("gmni_shotgun_ballistic_01", "R97 霰弹枪"),
    ("ksar_shotgun_ballistic_01", "劫掠者-212双管霰弹枪"),
    ("ksar_shotgun_energy_01", "破坏者 霰弹枪"),
    ("volt_shotgun_energy_01", "棱镜 激光霰弹枪"),
    ("none_shotgun_ballistic_01", "死钻 霰弹枪"),
    # 狙击步枪
    ("gmni_sniper_ballistic_01", "A03 狙击步枪"),
    ("klwe_sniper_energy_01", "箭头 狙击枪"),
    ("lbco_sniper_energy_01", "阿兹卡夫 狙击步枪"),
    ("behr_sniper_ballistic_01", "P6-LR 狙击步枪"),
    ("ksar_sniper_ballistic_01", "解剖刀 狙击步枪"),
    ("volt_sniper_energy_01", "天顶 激光狙击步枪"),
    # 特殊 / 榴弹 / 爆炸
    ("behr_glauncher_ballistic_01", "GP-33 MOD 榴弹发射器"),
    ("none_special_ballistic_01", "爆破筒 发射器"),
    ("apar_special_ballistic_01", "天灾 电磁炮"),
    ("apar_special_ballistic_02", "敌意 导弹发射器"),
    ("utfl_crossbow_ballistic_01", "诺维安 十字弩"),
    ("yormandi_weapon", "Yormandi 武器"),
]

CAT_MAP = {
    "rifle": "步枪", "pistol": "手枪", "smg": "冲锋枪", "shotgun": "霰弹枪",
    "sniper": "狙击步枪", "lmg": "机枪", "glauncher": "榴弹发射器",
    "special": "特殊武器", "hmg": "机枪", "crossbow": "弩", "weapon": "特殊武器",
}

# 特殊武器归类覆盖（游戏内部类名 -> 展示分类）
CAT_OVERRIDE = {
    "apar_hmg_ballistic_01": "机枪",
    "behr_glauncher_ballistic_01": "榴弹发射器",
    "apar_special_ballistic_01": "特殊武器",
    "apar_special_ballistic_02": "特殊武器",
    "none_special_ballistic_01": "特殊武器",
    "utfl_crossbow_ballistic_01": "弩",
    "yormandi_weapon": "特殊",
    "sasu_pistol_toy_01": "手枪",
    "hdgw_rifle_ballistic_01": "步枪",
    "lbco_pistol_energy_01": "手枪",
    "lbco_sniper_energy_01": "狙击步枪",
}

# 多模式武器：强制使用指定 fire action 类型（旧数据行为保持）
FIRE_ACTION_OVERRIDE = {
    # Arclight 手枪：旧数据采用单发模式 500 RPM（非 3 连发 700）
    "klwe_pistol_energy_01": "SWeaponActionFireSingleParams",
}

# 光束/连续武器（damage 按每 tick 计，fireRate 显示 1800 = 30 tick/s * 60s）
BEAM_FIRE_RATE = 1800


def load_json(fp):
    with open(fp, encoding="utf-8") as fh:
        return json.load(fh)


def find_components(d, type_name):
    out = []
    for c in (d.get("_RecordValue_") or {}).get("Components") or []:
        if c.get("_Type_") == type_name:
            out.append(c)
    return out


def _walk_actions(node, out):
    """递归收集所有开火动作（含 Sequence/Parallel/DynamicCondition 嵌套）。

    DynamicCondition 的条件动作优先于默认动作（如 VOLT 步枪热量≥40% 切光束，
    旧数据按光束模式处理；VOLT 霰弹枪条件模式为 200RPM 单发）。
    """
    if isinstance(node, dict):
        t = node.get("_Type_", "")
        if t in ("SWeaponActionFireRapidParams", "SWeaponActionFireSingleParams",
                 "SWeaponActionFireBurstParams", "SWeaponActionFireChargedParams",
                 "SWeaponActionFireBeamParams", "SWeaponActionFireProjectileParams"):
            out.append(node)
        if t == "SWeaponActionFireChargedParams" and isinstance(node.get("weaponAction"), dict):
            _walk_actions(node["weaponAction"], out)
        if t == "SWeaponActionSequenceParams":
            for se in node.get("sequenceEntries") or []:
                if isinstance(se, dict) and isinstance(se.get("weaponAction"), dict):
                    _walk_actions(se["weaponAction"], out)
        if t == "SWeaponActionParallelParams":
            for wa in node.get("weaponActions") or []:
                _walk_actions(wa, out)
        if t == "SWeaponActionDynamicConditionParams":
            for cwa in node.get("conditionalWeaponActions") or []:
                if isinstance(cwa, dict) and isinstance(cwa.get("weaponAction"), dict):
                    _walk_actions(cwa["weaponAction"], out)
            if isinstance(node.get("defaultWeaponAction"), dict):
                _walk_actions(node["defaultWeaponAction"], out)
    elif isinstance(node, list):
        for v in node:
            _walk_actions(v, out)


def ammo_file_for(records, weapon_fp):
    """通过 ammoContainerRecord -> mag -> ammoParamsRecord 解析弹药 JSON 路径。"""
    d = load_json(weapon_fp)
    wc = find_components(d, "SCItemWeaponComponentParams")
    if not wc:
        return None
    rec = wc[0].get("ammoContainerRecord") or ""
    m = re.search(r"records/(.+?\.json)$", rec)
    if not m:
        return None
    mag_fp = os.path.join(records, m.group(1).replace("/", os.sep))
    if not os.path.exists(mag_fp):
        return None
    mag = load_json(mag_fp)
    ac = find_components(mag, "SAmmoContainerComponentParams")
    if not ac:
        return None
    rec2 = ac[0].get("ammoParamsRecord") or ""
    m2 = re.search(r"records/(.+?\.json)$", rec2)
    if not m2:
        return None
    return os.path.join(records, m2.group(1).replace("/", os.sep))


def ammo_damage(ammo_fp):
    """弹药 projectileParams.damage（直击伤害）。"""
    if not ammo_fp:
        return None
    d = load_json(ammo_fp)
    pp = (d.get("_RecordValue_") or {}).get("projectileParams") or {}
    dmg = pp.get("damage") or {}
    return {t: dmg.get(t, 0.0) or 0.0 for t in DAMAGE_TYPES}


def explosion_info(ammo_fp):
    """爆炸伤害 detonationParams.explosionParams.damage + maxRadius。"""
    if not ammo_fp:
        return None, None
    d = load_json(ammo_fp)
    pp = (d.get("_RecordValue_") or {}).get("projectileParams") or {}
    det = pp.get("detonationParams") or {}
    ex = det.get("explosionParams") or {}
    dmg = ex.get("damage") or {}
    total = sum(dmg.get(t, 0.0) or 0.0 for t in DAMAGE_TYPES)
    if total <= 0:
        return None, None
    return {t: dmg.get(t, 0.0) or 0.0 for t in DAMAGE_TYPES}, ex.get("maxRadius")


def pick_primary(actions):
    """选择主开火动作：优先单发/连发/点射，其次蓄力子动作，最后光束。

    注意：蓄力武器的 fireRate 取子动作（weaponAction）射速，由调用方处理。
    """
    for a in actions:
        if a.get("_Type_") in ("SWeaponActionFireRapidParams", "SWeaponActionFireSingleParams",
                               "SWeaponActionFireBurstParams"):
            return a
    for a in actions:
        if a.get("_Type_") == "SWeaponActionFireChargedParams":
            return a
    for a in actions:
        if a.get("_Type_") == "SWeaponActionFireBeamParams":
            return a
    for a in actions:
        if a.get("_Type_") == "SWeaponActionFireProjectileParams":
            return a
    return None


def beam_dps_of(actions):
    """返回第一个 SWeaponActionFireBeamParams 的 damagePerSecond（每秒），没有则 None。"""
    for a in actions:
        if a.get("_Type_") == "SWeaponActionFireBeamParams":
            dps = a.get("damagePerSecond") or {}
            return {t: dps.get(t, 0.0) or 0.0 for t in DAMAGE_TYPES}
    return None


def charged_params_of(actions):
    """蓄力参数：chargeTime / maxChargeModifier.damageMultiplier / burstShots + 子动作。"""
    for a in actions:
        if a.get("_Type_") == "SWeaponActionFireChargedParams":
            mcm = a.get("maxChargeModifier") or {}
            return (a.get("chargeTime"), mcm.get("damageMultiplier"),
                    mcm.get("burstShots"), a.get("weaponAction"))
    return None, None, None, None


def burst_shots_of(actions):
    """点射子弹数（burstShots，来自蓄力 maxChargeModifier 或 Burst 动作 shotCount）。"""
    _, _, mcm_burst, wa = charged_params_of(actions)
    if mcm_burst is not None:
        return mcm_burst
    for a in actions:
        if a.get("_Type_") == "SWeaponActionFireBurstParams":
            return a.get("shotCount")
    return None


def launch_of(a):
    lp = a.get("launchParams") or {}
    return lp.get("pelletCount"), lp.get("damageMultiplier")


def extract_weapon(records, base):
    """从解包 JSON 提取一把武器的 btk_data 条目。"""
    wdir = os.path.join(records, "entities", "scitem", "weapons", "fps_weapons")
    fp = os.path.join(wdir, base + ".json")
    if not os.path.exists(fp):
        print("!! MISSING:", base)
        return None
    d = load_json(fp)
    wc = find_components(d, "SCItemWeaponComponentParams")
    if not wc:
        print("!! NO SCItemWeaponComponentParams:", base)
        return None
    wc = wc[0]

    # 攻击方式归类（用于 flags 标注）
    atypes = []
    for fa in wc.get("fireActions") or []:
        atypes.append(fa.get("_Type_", ""))
    act_tree = []
    for fa in wc.get("fireActions") or []:
        _walk_actions(fa, act_tree)

    ammo_fp = ammo_file_for(records, fp)
    dmg = ammo_damage(ammo_fp)
    if dmg is None:
        dmg = {t: 0.0 for t in DAMAGE_TYPES}
    exp_dmg, exp_radius = explosion_info(ammo_fp)

    # 光束武器：damage 用 damagePerSecond/30（每 tick），fireRate=1800
    beam_dps = beam_dps_of(act_tree)
    is_beam = beam_dps is not None
    if is_beam:
        dmg = {t: v / 30.0 for t, v in beam_dps.items()}

    charge_time, charge_dm, _, charge_wa = charged_params_of(act_tree)
    prim = pick_primary(act_tree)
    # 多模式武器 override（保持旧数据行为）
    force_type = FIRE_ACTION_OVERRIDE.get(base)
    if force_type:
        for a in act_tree:
            if a.get("_Type_") == force_type:
                prim = a
                break
    fire_rate = None
    heat = 0.0
    pellet = 1
    mult = 1.0
    if is_beam:
        fire_rate = BEAM_FIRE_RATE
        # 光束武器热量取默认动作的 heatPerShot（如 VOLT 步枪 3.5）
        for a in act_tree:
            if a.get("_Type_") in ("SWeaponActionFireRapidParams", "SWeaponActionFireSingleParams"):
                heat = a.get("heatPerShot") or 0.0
                break
    elif charge_dm is not None and charge_wa is not None:
        # 蓄力武器：fireRate 取子动作的射速（Karna 350 / Custodian 900）
        fire_rate = charge_wa.get("fireRate")
        lp = charge_wa.get("launchParams") or {}
        pellet = lp.get("pelletCount") or 1
        mult = lp.get("damageMultiplier") or 1.0
        heat = charge_wa.get("heatPerShot") or 0.0
    elif prim is not None:
        fire_rate = prim.get("fireRate")
        lp = prim.get("launchParams") or {}
        pellet = lp.get("pelletCount") or 1
        mult = lp.get("damageMultiplier") or 1.0
        heat = prim.get("heatPerShot") or 0.0

    # 分类：优先显式覆盖，其次从文件名类别段解析（rifle/pistol/smg/lmg/shotgun/sniper/glauncher/special/crossbow/hmg）
    category = CAT_OVERRIDE.get(base)
    if category is None:
        m_cat = re.search(r"_(rifle|pistol|smg|lmg|shotgun|sniper|glauncher|special|crossbow|hmg)_", base)
        category = CAT_MAP.get(m_cat.group(1)) if m_cat else "特殊武器"

    # flags 标注
    flags = []
    if is_beam:
        flags.append("光束")
        flags.append("连续")
    if charge_dm is not None and charge_time is not None:
        flags.append("蓄力")
    if exp_dmg:
        flags.append("爆炸")
    # 热量标注（有 heatPerShot 且非 0）
    if heat and heat > 0:
        flags.append("热量")
    if not flags:
        flags.append("常规")

    charge_time, charge_dm, charge_burst, _ = charged_params_of(act_tree)
    burst = burst_shots_of(act_tree)

    # alpha = 单发总伤害（光束=每 tick）
    alpha = round(sum(dmg.values()) * mult * pellet, 2)
    alpha_charged = None
    if charge_dm is not None and charge_time is not None:
        alpha_charged = round(alpha * charge_dm, 2)

    note = ""
    if exp_dmg:
        exp_total = sum(exp_dmg.values())
        note = "爆炸伤害 %.1f（半径 %sm）" % (exp_total, exp_radius if exp_radius is not None else 0)
        # 直击+爆炸合计作为总伤害
        dmg = {t: dmg.get(t, 0.0) + exp_dmg.get(t, 0.0) for t in DAMAGE_TYPES}
        alpha = round(sum(dmg.values()) * mult * pellet, 2)
        if alpha_charged is not None:
            alpha_charged = round(alpha * charge_dm, 2)

    return {
        "name": dict(CURATED)[base] if base in dict(CURATED) else base,
        "file": base + ".json",
        "category": category,
        "fireRate": fire_rate,
        "heatPerShot": heat,
        "damage": dmg,
        "pellet": pellet,
        "mult": mult,
        "alpha": alpha,
        "alphaCharged": alpha_charged,
        "chargeTime": charge_time,
        "chargeDM": charge_dm,
        "chargeBurst": burst,
        "dps": round(sum(beam_dps.values()), 4) if beam_dps else None,
        "flags": "/".join(flags) if flags else "常规",
        "note": note,
        "explosionRadius": exp_radius,
    }


def extract_armors(records):
    """从 records/damage/*.json 提取护甲。"""
    ddir = os.path.join(records, "damage")
    out = {}
    for fn in os.listdir(ddir):
        if not fn.endswith(".json"):
            continue
        fp = os.path.join(ddir, fn)
        d = load_json(fp)
        rv = d.get("_RecordValue_") or {}
        if rv.get("_Type_") != "DamageResistanceMacro":
            continue
        dr = rv.get("damageResistance") or {}
        mult = {}
        caps = {}
        for t in DAMAGE_TYPES:
            short = t.replace("Damage", "")
            entry = dr.get(short + "Resistance") or {}
            v = entry.get("Multiplier")
            mult[t] = v if v is not None else 1.0
            c = entry.get("DamageCap") or 0.0
            if c and c > 0:
                caps[t] = c
        key = fn[:-5]
        out[key] = {"mult": mult, "caps": caps}
    return out


def main():
    records = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_RECORDS
    out_fp = sys.argv[2] if len(sys.argv) > 2 else OUT
    records = os.path.abspath(records)
    if not os.path.isdir(records):
        print("!! records dir not found:", records)
        sys.exit(1)

    # 武器
    weapons = []
    for base, ename in CURATED:
        w = extract_weapon(records, base)
        if w is None:
            continue
        w["name"] = ename
        weapons.append(w)
        print("OK  %-42s %-8s RPM=%s alpha=%s flags=%s %s" % (
            ename, w["category"], w["fireRate"], w["alpha"], w["flags"],
            ("爆炸R=%s" % w["explosionRadius"]) if w["explosionRadius"] else ""))

    # 护甲
    armors = extract_armors(records)
    armors_display = {
        "无护甲": "damageresistancemacro.defaultdamageresistance",
        "内衬(undersuit)": "undersuitarmor",
        "飞行服": "combatflightsuitarmor",
        "轻甲": "lightarmor",
        "中甲": "mediumarmor",
        "重甲": "heavyarmor",
        "堡垒甲 Citadel 75% (AI专属)": "heavyarmor_ai_exclusive",
        "超重甲 CDS Superheavy": "superheavyarmor",
    }

    # 目标（游戏机制数据，保持既有硬编码）
    targets = {
        "玩家": {"health": 100, "parts": {"head": 1.5, "torso": 1.0, "arms": 0.8, "legs": 0.8},
                 "partHealth": {"head": 30, "torso": 60, "arms": 36, "legs": 48},
                 "armor": "无护甲", "cap": None},
        "普通AI": {"health": 100, "parts": {"head": 2.4, "torso": 1.8, "arms": 1.5, "legs": 1.5},
                   "partHealth": {"head": 30, "torso": 60, "arms": 36, "legs": 48},
                   "armor": "无护甲", "cap": None},
        "AI队长": {"health": 185, "parts": {"head": 2.4, "torso": 1.8, "arms": 1.5, "legs": 1.5},
                   "partHealth": {"head": 30, "torso": 60, "arms": 36, "legs": 48},
                   "armor": "无护甲", "cap": None},
        "AI精英": {"health": 250, "parts": {"head": 2.4, "torso": 1.8, "arms": 1.5, "legs": 1.5},
                   "partHealth": {"head": 30, "torso": 60, "arms": 36, "legs": 48},
                   "armor": "无护甲", "cap": None},
        "无畏战士(Juggernaut)": {"health": 235, "parts": {"head": 1.95, "torso": 1.3, "arms": 1.0, "legs": 1.0},
                   "partHealth": {"head": 30, "torso": 60, "arms": 36, "legs": 48},
                   "armor": "堡垒甲 Citadel 75% (AI专属)", "cap": None},
        "AI BOSS": {"health": 280, "parts": {"head": 2.4, "torso": 1.8, "arms": 1.5, "legs": 1.5},
                   "partHealth": {"head": 30, "torso": 60, "arms": 36, "legs": 48},
                   "armor": "堡垒甲 Citadel 75% (AI专属)", "cap": None},
        "超级BOSS": {"health": 560, "parts": {"head": 2.4, "torso": 1.8, "arms": 1.5, "legs": 1.5},
                   "partHealth": {"head": 30, "torso": 60, "arms": 36, "legs": 48},
                   "armor": "堡垒甲 Citadel 75% (AI专属)", "cap": None},
        "凡杜 Vanduul": {"health": 275, "parts": {"head": 12.0, "torso": 4.0, "arms": 4.0, "legs": 4.0},
                   "partHealth": {"head": 200, "torso": 250, "arms": 100, "legs": 100},
                   "armor": "无护甲", "cap": None},
        "vlk 幼崽": {"health": 110, "parts": {"head": 2.0, "torso": 1.0, "arms": 1.0, "legs": 1.0},
                   "partHealth": None, "armor": "无护甲", "cap": None},
        "vlk 成体": {"health": 550, "parts": {"head": 2.0, "torso": 1.0, "arms": 1.0, "legs": 1.0},
                   "partHealth": None, "armor": "无护甲", "cap": None},
        "vlk 变异成体": {"health": 475, "parts": {"head": 2.0, "torso": 1.0, "arms": 1.0, "legs": 1.0},
                   "partHealth": None, "armor": "无护甲", "cap": None},
        "vlk Apex": {"health": 400000, "parts": {"head": 1.0, "torso": 0.01, "arms": 0.01, "legs": 0.01},
                   "partHealth": None, "armor": "无护甲", "cap": 100.0},
        "yormandi": {"health": 3355, "parts": {"head": 1.0, "torso": 0.05, "arms": 0.05, "legs": 0.05},
                   "partHealth": None, "armor": "无护甲", "cap": 100.0},
    }

    # 缺少的护甲键补齐（armors 里可能没有的显示项）
    for disp, key in armors_display.items():
        if key not in armors:
            print("!! MISSING armor:", key, "->", disp)
            armors[key] = {"mult": {t: 1.0 for t in DAMAGE_TYPES}, "caps": {}}

    with open(out_fp, "w", encoding="utf-8") as fh:
        fh.write("# -*- coding: utf-8 -*-\n")
        fh.write("# Generated by generate_data.py from StarBreaker records. Do not edit by hand.\n")
        fh.write("DAMAGE_TYPES = %s\n\n" % repr(DAMAGE_TYPES))
        fh.write("WEAPONS = %s\n\n" % repr(weapons))
        fh.write("ARMOR_KEYS = %s\n\n" % repr(armors_display))
        fh.write("ARMORS = %s\n\n" % repr(armors))
        fh.write("TARGETS = %s\n" % repr(targets))
    print()
    print("weapons=%d armors=%d targets=%d -> %s" % (len(weapons), len(armors), len(targets), out_fp))


if __name__ == "__main__":
    main()
