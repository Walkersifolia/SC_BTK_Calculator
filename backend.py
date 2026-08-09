# -*- coding: utf-8 -*-
"""BTK 计算器后端服务：提供数据查询与计算 API（零依赖，标准库 http.server）。

前端通过 fetch 调用以下 API：
  GET  /api/meta             -> 分类/护甲/目标/部位/伤害类型等元数据
  GET  /api/weapons          -> 全部武器（按分类分组）
  GET  /api/calc             -> 计算单武器
       ?name=&armor=&target=&part=&boost=&charged=&custom_*=
  GET  /api/calc_compare     -> 对比两武器
       ?l_name=&r_name=&armor=&target=&part=&boost=&l_charged=&r_charged=&custom_*=
  GET  /api/effective        -> 应用自定义 alpha/rpm 后的有效武器参数
"""
import json
import mimetypes
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import btk_core as core

UI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui")


def _fnum(v):
    """容忍空/None 的浮点解析。"""
    try:
        return float(v) if v not in (None, "") else 0.0
    except (TypeError, ValueError):
        return 0.0


def build_custom_weapon(q):
    """从查询参数构造自定义武器（存在 custom_ 参数时）。"""
    if "custom_damage" not in q:
        return None
    return core.make_custom_weapon(
        _fnum(q.get("custom_damage", [0])[0]),
        _fnum(q.get("custom_rpm", [0])[0]),
        _fnum(q.get("custom_pellet", [1])[0]),
        q.get("custom_type", ["物理"])[0],
    )


def resolve_weapon(q, key):
    """解析武器：自定义武器或按名字查。"""
    name = q.get(key, [""])[0]
    if name == "自定义武器":
        return build_custom_weapon(q)
    return core.get_weapon_by_name(name)


def build_custom_target(q):
    if "custom_target_health" not in q:
        return None
    return core.make_custom_target(
        _fnum(q.get("custom_target_health", [0])[0]),
        _fnum(q.get("custom_target_head", [1.5])[0]),
        _fnum(q.get("custom_target_torso", [1.0])[0]),
        _fnum(q.get("custom_target_arms", [0.8])[0]),
        _fnum(q.get("custom_target_legs", [0.8])[0]),
        q.get("armor", ["无护甲"])[0],
    )


def resolve_target(q):
    t = build_custom_target(q)
    if t is not None:
        return t
    name = q.get("target", ["普通AI"])[0]
    return core.TARGETS.get(name, core.TARGETS["普通AI"])


def apply_effective(weapon, alpha, rpm):
    """模拟原 UI 的 get_effective_weapon：按自定义 alpha/rpm 缩放伤害分布。

    参数为空字符串时表示用户未修改，返回原武器。
    """
    if weapon is None or weapon.get("is_custom"):
        return weapon
    if alpha in (None, "") and rpm in (None, ""):
        return weapon
    a = _fnum(alpha)
    r = _fnum(rpm)
    # 只有一个参数被修改时，另一个取武器原值
    if alpha in (None, ""):
        a = weapon["alpha"]
    if rpm in (None, ""):
        r = weapon["fireRate"] or 0
    if abs(a - weapon["alpha"]) < 0.01 and abs(r - (weapon["fireRate"] or 0)) < 0.01:
        return weapon
    w = dict(weapon)
    w["fireRate"] = r
    w["is_customized"] = True
    dmg = dict(weapon["damage"])
    total = sum(dmg.values())
    target = a / weapon["pellet"]
    if total > 0:
        for t in dmg:
            dmg[t] = dmg[t] * target / total
    else:
        dmg["DamagePhysical"] = target
    w["damage"] = dmg
    w["alpha"] = a
    if weapon.get("alphaCharged") is not None:
        w["alphaCharged"] = a * (weapon.get("chargeDM") or 1.0)
    return w


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # 静默日志

    def _send(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            self._route()
        except Exception as e:
            self._send({"error": str(e)}, 500)

    def _serve_static(self, path):
        """服务 ui/ 目录下的静态文件。"""
        if path in ("/", ""):
            path = "/index.html"
        fp = os.path.normpath(os.path.join(UI_DIR, path.lstrip("/")))
        if not fp.startswith(os.path.normpath(UI_DIR)) or not os.path.isfile(fp):
            self._send({"error": "not found"}, 404)
            return
        ctype = mimetypes.guess_type(fp)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/json",):
            ctype += "; charset=utf-8"
        with open(fp, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _route(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        p = u.path

        if p.startswith("/api/"):
            self._route_api(p, q)
        else:
            self._serve_static(p)

    def _route_api(self, p, q):
        if p == "/api/meta":
            self._send({
                "categories": core.CATEGORIES,
                "armors": core.ARMOR_DISPLAY,
                "targets": core.TARGET_DISPLAY,
                "parts": core.PARTS,
                "damageTypes": core.DAMAGE_TYPES,
            })
        elif p == "/api/weapons":
            self._send({
                "byCategory": core.WEAPONS_BY_CAT,
                "categories": core.CATEGORIES,
            })
        elif p == "/api/calc":
            weapon = resolve_weapon(q, "name")
            if weapon is None:
                self._send({"error": "武器不存在"}, 404)
                return
            weapon = apply_effective(weapon,
                                     q.get("edit_alpha", [""])[0],
                                     q.get("edit_rpm", [""])[0])
            target = resolve_target(q)
            part_key = q.get("part", ["torso"])[0]
            boost = _fnum(q.get("boost", [0])[0]) / 100.0
            charged = q.get("charged", ["false"])[0] == "true"
            r = core.calc(weapon, q.get("armor", ["无护甲"])[0], target, part_key, boost, charged)
            self._send({
                "result": r,
                "weapon": {k: weapon.get(k) for k in
                           ("name", "category", "fireRate", "alpha", "alphaCharged",
                            "chargeTime", "chargeDM", "flags", "note", "dps",
                            "explosionRadius", "is_custom", "is_customized")},
                "perPart": [
                    {"part": name, "key": key,
                     "r": core.calc(weapon, q.get("armor", ["无护甲"])[0], target,
                                    key, boost, charged)}
                    for name, key in core.PARTS
                ],
                "target": {"name": target.get("name", "自定义目标"),
                           "health": target["health"], "armor": q.get("armor", ["无护甲"])[0],
                           "part": part_key},
            })
        elif p == "/api/calc_compare":
            wl = resolve_weapon(q, "l_name")
            wr = resolve_weapon(q, "r_name")
            if wl is None or wr is None:
                self._send({"error": "武器不存在"}, 404)
                return
            wl = apply_effective(wl, q.get("l_alpha", [""])[0], q.get("l_rpm", [""])[0])
            wr = apply_effective(wr, q.get("r_alpha", [""])[0], q.get("r_rpm", [""])[0])
            target = resolve_target(q)
            part_key = q.get("part", ["torso"])[0]
            boost = _fnum(q.get("boost", [0])[0]) / 100.0
            armor = q.get("armor", ["无护甲"])[0]
            lc = q.get("l_charged", ["false"])[0] == "true"
            rc = q.get("r_charged", ["false"])[0] == "true"
            rl = core.calc(wl, armor, target, part_key, boost, lc)
            rr = core.calc(wr, armor, target, part_key, boost, rc)
            diff = rl["btk"] - rr["btk"]
            verdict = "BTK 相同" if diff == 0 else "%s侧更快 %d 发" % ("右" if diff > 0 else "左", abs(diff))
            self._send({
                "left": {"weapon": wl["name"], "r": rl},
                "right": {"weapon": wr["name"], "r": rr},
                "verdict": verdict,
            })
        else:
            self._send({"error": "not found"}, 404)


def start_server(port=0):
    """启动后端服务，返回 (server, port)。port=0 时自动选空闲端口。"""
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, server.server_address[1]


if __name__ == "__main__":
    srv, port = start_server(8765)
    print("后端服务已启动: http://127.0.0.1:%d" % port)
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        srv.shutdown()
