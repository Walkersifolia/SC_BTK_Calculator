# -*- coding: utf-8 -*-
"""星际公民 BTK 计算器 v3"""
import math
import sys
import tkinter as tk
from tkinter import ttk

from btk_data import WEAPONS, ARMOR_KEYS, ARMORS, TARGETS, DAMAGE_TYPES

CATEGORIES = []
for w in WEAPONS:
    if w["category"] not in CATEGORIES:
        CATEGORIES.append(w["category"])
CATEGORIES.append("自定义武器")
CATEGORIES_MAIN = [c for c in CATEGORIES if c != "自定义武器"]
WEAPONS_BY_CAT = {c: [w for w in WEAPONS if w["category"] == c] for c in CATEGORIES_MAIN}

ARMOR_DISPLAY = list(ARMOR_KEYS.keys())
TARGET_DISPLAY = list(TARGETS.keys())
PARTS = [("头部", "head"), ("躯干", "torso"), ("手臂", "arms"), ("腿部", "legs")]

INF = float("inf")

THEMES = {
    "light": {
        "BG": "#f5f6f8", "PANEL": "#ffffff",
        "ACCENT": "#0a5ed6", "ACCENT_DK": "#0a4cc0",
        "TEXT": "#1a1d21", "MUTED": "#5f6b7a",
        "DANGER": "#dc2626", "OK": "#16a34a", "LINE": "#e2e5ea",
        "BTN_TEXT": "#ffffff", "BTN_HOVER": "#093f9e", "BTN_DISABLED": "#a9c5f0",
        "INPUT_BG": "#ffffff", "CANVAS_BG": "#f8fafc", "RES_BG": "#f8fafc",
        "THUMB_FILL_HIT": "#fca5a5", "THUMB_FILL": "#bfdbfe",
        "THUMB_OUTLINE": "#475569", "THUMB_DIM": "#334155",
        "THUMB_ACCENT": "#2563eb", "BADGE": "#b45309",
    },
    "dark": {
        "BG": "#1a1d24", "PANEL": "#242830",
        "ACCENT": "#4d9fff", "ACCENT_DK": "#7ab8ff",
        "TEXT": "#e6e8ec", "MUTED": "#9aa1ac",
        "DANGER": "#f87171", "OK": "#34d399", "LINE": "#333845",
        "BTN_TEXT": "#0b1420", "BTN_HOVER": "#6fb1ff", "BTN_DISABLED": "#39465c",
        "INPUT_BG": "#2a2f3a", "CANVAS_BG": "#1e222b", "RES_BG": "#1e222b",
        "THUMB_FILL_HIT": "#f87171", "THUMB_FILL": "#3b82f6",
        "THUMB_OUTLINE": "#4a5261", "THUMB_DIM": "#c3c9d4",
        "THUMB_ACCENT": "#4d9fff", "BADGE": "#fbbf24",
    },
}
CURRENT_THEME = "light"


def colors():
    return THEMES[CURRENT_THEME]


def setup_style():
    C = THEMES[CURRENT_THEME]
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass
    style.configure("TFrame", background=C["BG"])
    style.configure("TPanel.TFrame", background=C["PANEL"])
    style.configure("TLabel", background=C["BG"], foreground=C["TEXT"], font=("Microsoft YaHei UI", 10))
    style.configure("Panel.TLabel", background=C["PANEL"], foreground=C["TEXT"], font=("Microsoft YaHei UI", 10))
    style.configure("TLabelframe", background=C["BG"], bordercolor=C["LINE"], relief="solid")
    style.configure("TLabelframe.Label", background=C["BG"], foreground=C["TEXT"],
                    font=("Microsoft YaHei UI", 10, "bold"))
    style.configure("TButton", background=C["ACCENT"], foreground=C["BTN_TEXT"], padding=(14, 7),
                    font=("Microsoft YaHei UI", 10, "bold"))
    style.map("TButton", background=[("active", C["BTN_HOVER"]), ("disabled", C["BTN_DISABLED"])])
    style.configure("TCombobox", fieldbackground=C["INPUT_BG"], background=C["PANEL"],
                    foreground=C["TEXT"], arrowcolor=C["MUTED"])
    style.configure("TEntry", fieldbackground=C["INPUT_BG"], foreground=C["TEXT"])
    style.configure("TCheckbutton", background=C["BG"], foreground=C["TEXT"])
    style.configure("Panel.TCheckbutton", background=C["PANEL"], foreground=C["TEXT"])
    style.configure("Horizontal.TScale", background=C["BG"], troughcolor=C["INPUT_BG"])
    style.configure("TRadiobutton", background=C["BG"], foreground=C["TEXT"])


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


class App:
    def __init__(self, root):
        self.root = root
        root.title("星际公民 BTK 计算器")
        root.geometry("1380x880")
        root.minsize(1120, 740)

        self.theme = "light"

        self.mode = tk.StringVar(value="single")
        self.boost_var = tk.DoubleVar(value=0.0)
        self.boost_label_var = tk.StringVar(value="0%")
        self.hit_var = tk.StringVar(value="躯干")
        self.target_var = tk.StringVar(value="普通AI")
        self.armor_var = tk.StringVar(value="无护甲")
        self.charged_l = tk.BooleanVar(value=False)
        self.charged_r = tk.BooleanVar(value=False)

        self.custom_health = tk.StringVar(value="100")
        self.custom_head = tk.StringVar(value="1.5")
        self.custom_torso = tk.StringVar(value="1.0")
        self.custom_arms = tk.StringVar(value="0.8")
        self.custom_legs = tk.StringVar(value="0.8")

        self.cw_damage = tk.StringVar(value="30")
        self.cw_rpm = tk.StringVar(value="600")
        self.cw_pellet = tk.StringVar(value="1")
        self.cw_type = tk.StringVar(value="物理")

        # 可编辑武器参数
        self.edit_alpha = tk.StringVar()
        self.edit_rpm = tk.StringVar()

        self.cat_var = tk.StringVar(value=CATEGORIES[0])
        self.wvar_l = tk.StringVar()
        self.wvar_r = tk.StringVar()

        self._auto_after = None
        self._build_ui()
        self._bind_auto()

    # ---------------- UI ----------------
    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(12, 8, 12, 4))
        top.pack(fill=tk.X)
        self.title_l = ttk.Label(top, text="星际公民 BTK 计算器", font=("Microsoft YaHei UI", 14, "bold"),
                                 foreground=colors()["ACCENT_DK"])
        self.title_l.pack(side=tk.LEFT)
        self.mode_l = ttk.Label(top, text="模式:", foreground=colors()["MUTED"])
        self.mode_l.pack(side=tk.LEFT, padx=(40, 4))
        for text, val in (("单武器", "single"), ("武器对比", "compare")):
            ttk.Radiobutton(top, text=text, value=val, variable=self.mode,
                            command=self._on_mode).pack(side=tk.LEFT, padx=4)
        self.theme_btn = ttk.Button(top, text="🌓 深色", command=self._toggle_theme)
        self.theme_btn.pack(side=tk.LEFT, padx=(24, 0))

        main = ttk.Frame(self.root, padding=(12, 4, 12, 12))
        main.pack(fill=tk.BOTH, expand=True)
        self.left_pane = ttk.Frame(main, style="TPanel.TFrame", padding=10)
        self.right_pane = ttk.Frame(main, style="TPanel.TFrame", padding=10)
        self.left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        self.right_pane.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_right_pane()
        self._on_mode()
        self._on_target_changed()
        self._apply_theme()

    # ---------------- 右侧 ----------------
    def _build_right_pane(self):
        cfg = ttk.LabelFrame(self.right_pane, text="目标 / 命中 / 增益", padding=10)
        cfg.pack(fill=tk.X)

        ttk.Label(cfg, text="目标类型:").grid(row=0, column=0, sticky=tk.W, pady=3)
        tc = ttk.Combobox(cfg, textvariable=self.target_var, values=TARGET_DISPLAY,
                          state="readonly", width=24)
        tc.grid(row=0, column=1, padx=8, pady=3, sticky=tk.W)
        tc.bind("<<ComboboxSelected>>", lambda e: self._on_target_changed())

        ttk.Label(cfg, text="护甲类型:").grid(row=1, column=0, sticky=tk.W, pady=3)
        ttk.Combobox(cfg, textvariable=self.armor_var, values=ARMOR_DISPLAY,
                     state="readonly", width=24).grid(row=1, column=1, padx=8, pady=3, sticky=tk.W)

        ttk.Label(cfg, text="命中部位:").grid(row=2, column=0, sticky=tk.W, pady=3)
        ttk.Combobox(cfg, textvariable=self.hit_var, values=[p[0] for p in PARTS],
                     state="readonly", width=24).grid(row=2, column=1, padx=8, pady=3, sticky=tk.W)

        ttk.Label(cfg, text="伤害增益:").grid(row=3, column=0, sticky=tk.W, pady=3)
        row = ttk.Frame(cfg)
        row.grid(row=3, column=1, padx=8, pady=3, sticky=tk.W)
        ttk.Scale(row, from_=-100, to=100, variable=self.boost_var, orient=tk.HORIZONTAL,
                  length=200, command=self._on_boost).pack(side=tk.LEFT)
        ttk.Label(row, textvariable=self.boost_label_var, width=7).pack(side=tk.LEFT, padx=6)

        self.custom_frame = ttk.LabelFrame(self.right_pane, text="自定义目标", padding=8)
        fields = [("生命值", self.custom_health), ("头部倍率", self.custom_head),
                  ("躯干倍率", self.custom_torso), ("手臂倍率", self.custom_arms),
                  ("腿部倍率", self.custom_legs)]
        for i, (lab, var) in enumerate(fields):
            ttk.Label(self.custom_frame, text=lab).grid(row=i, column=0, sticky=tk.W, pady=2)
            ttk.Entry(self.custom_frame, textvariable=var, width=10).grid(row=i, column=1, padx=6, pady=2)

        thumb = ttk.LabelFrame(self.right_pane, text="目标部位减伤预览", padding=8)
        thumb.pack(fill=tk.X, pady=(8, 0))
        self.thumb_canvas = tk.Canvas(thumb, width=560, height=230, bg=colors()["CANVAS_BG"],
                                      highlightthickness=1, highlightbackground=colors()["LINE"])
        self.thumb_canvas.pack(fill=tk.X)

        res = ttk.LabelFrame(self.right_pane, text="计算结果", padding=8)
        res.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.res_text = tk.Text(res, font=("Consolas", 10), bg=colors()["RES_BG"], relief="flat",
                                wrap="word", padx=8, pady=6, state="disabled")
        self.res_text.pack(fill=tk.BOTH, expand=True)
        self.res_text.tag_configure("title", font=("Microsoft YaHei UI", 11, "bold"), foreground=colors()["ACCENT_DK"])
        self.res_text.tag_configure("big", font=("Microsoft YaHei UI", 15, "bold"), foreground=colors()["DANGER"])
        self.res_text.tag_configure("muted", foreground=colors()["MUTED"])
        self.res_text.tag_configure("part", font=("Microsoft YaHei UI", 9))
        self.res_text.tag_configure("custom", foreground=colors()["BADGE"], font=("Microsoft YaHei UI", 9, "bold"))

    # ---------------- 左侧 ----------------
    def _build_single(self):
        sel = ttk.LabelFrame(self.left_pane, text="武器选择", padding=10)
        sel.pack(fill=tk.X)
        ttk.Label(sel, text="分类:").grid(row=0, column=0, sticky=tk.W, pady=3)
        cc = ttk.Combobox(sel, values=CATEGORIES, state="readonly", width=26, textvariable=self.cat_var)
        cc.grid(row=0, column=1, padx=8, pady=3, sticky=tk.W)
        cc.bind("<<ComboboxSelected>>", self._on_cat_l)
        ttk.Label(sel, text="武器:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.wcombo_l = ttk.Combobox(sel, textvariable=self.wvar_l, state="readonly", width=34)
        self.wcombo_l.grid(row=1, column=1, padx=8, pady=3, sticky=tk.W)
        self.wcombo_l.bind("<<ComboboxSelected>>", lambda e: self._on_weapon_changed("l"))
        self.charge_chk_l = ttk.Checkbutton(sel, text="满蓄力", variable=self.charged_l,
                                            style="Panel.TCheckbutton")
        self.charge_chk_l.grid(row=2, column=1, sticky=tk.W, padx=8, pady=3)
        self.chk_l = self.charge_chk_l

        # 自定义武器输入
        self.cw_frame = ttk.LabelFrame(self.left_pane, text="自定义武器属性", padding=8)
        cw_fields = [("伤害/发", self.cw_damage), ("射速 RPM", self.cw_rpm), ("弹丸数", self.cw_pellet)]
        for i, (lab, var) in enumerate(cw_fields):
            ttk.Label(self.cw_frame, text=lab).grid(row=i, column=0, sticky=tk.W, pady=2)
            ttk.Entry(self.cw_frame, textvariable=var, width=10).grid(row=i, column=1, padx=6, pady=2)
        ttk.Label(self.cw_frame, text="伤害类型:").grid(row=3, column=0, sticky=tk.W, pady=2)
        ttk.Combobox(self.cw_frame, textvariable=self.cw_type, values=["物理", "能量"],
                     state="readonly", width=10).grid(row=3, column=1, padx=6, pady=2, sticky=tk.W)
        self.cw_frame.pack_forget()

        # 可编辑武器参数
        params = ttk.LabelFrame(self.left_pane, text="武器参数（可直接修改，改后按自定义计算）", padding=10)
        params.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(params, text="伤害 Alpha:").grid(row=0, column=0, sticky=tk.W, pady=3)
        self.edit_alpha_entry = ttk.Entry(params, textvariable=self.edit_alpha, width=10)
        self.edit_alpha_entry.grid(row=0, column=1, padx=8, pady=3, sticky=tk.W)
        ttk.Label(params, text="射速 RPM:").grid(row=1, column=0, sticky=tk.W, pady=3)
        self.edit_rpm_entry = ttk.Entry(params, textvariable=self.edit_rpm, width=10)
        self.edit_rpm_entry.grid(row=1, column=1, padx=8, pady=3, sticky=tk.W)
        self.custom_badge_l = tk.Label(params, text="", fg=colors()["BADGE"], bg=colors()["PANEL"],
                                       font=("Microsoft YaHei UI", 9, "bold"))
        self.custom_badge_l._semantic = "badge"
        self.custom_badge_l.grid(row=0, column=2, rowspan=2, padx=8)

        info = ttk.LabelFrame(self.left_pane, text="武器信息", padding=10)
        info.pack(fill=tk.X, pady=(8, 0))
        self.info_l = tk.Label(info, text="", justify=tk.LEFT, bg=colors()["PANEL"], fg=colors()["MUTED"],
                               font=("Microsoft YaHei UI", 9))
        self.info_l._semantic = "muted"
        self.info_l.pack(anchor=tk.W)

        self.warn_l = tk.Label(self.left_pane, text="", fg=colors()["DANGER"], justify=tk.LEFT,
                               bg=colors()["PANEL"], font=("Microsoft YaHei UI", 11, "bold"),
                               wraplength=500)
        self.warn_l._semantic = "danger"
        self.warn_l.pack(anchor=tk.W, pady=(8, 0))

        ttk.Button(self.left_pane, text="计算 BTK", command=self._auto_run).pack(fill=tk.X, pady=(10, 0))
        self._on_cat_l()

    def _build_compare(self):
        frame = ttk.Frame(self.left_pane, style="TPanel.TFrame")
        frame.pack(fill=tk.BOTH, expand=True)
        lf = ttk.Frame(frame, style="TPanel.TFrame")
        rf = ttk.Frame(frame, style="TPanel.TFrame")
        lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 6))
        rf.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(6, 0))
        self._cmp_panel(lf, "左侧", "l", self.wvar_l, self.charged_l)
        self._cmp_panel(rf, "右侧", "r", self.wvar_r, self.charged_r)
        ttk.Button(frame, text="计算对比", command=self._auto_run).pack(fill=tk.X, pady=(8, 0))

    def _cmp_panel(self, parent, title, side, wvar, charged_var):
        f = ttk.LabelFrame(parent, text=title, padding=10)
        f.pack(fill=tk.BOTH, expand=True)
        ttk.Label(f, text="分类:").grid(row=0, column=0, sticky=tk.W, pady=3)
        catvar = tk.StringVar()
        ccombo = ttk.Combobox(f, textvariable=catvar, values=CATEGORIES_MAIN, state="readonly", width=15)
        ccombo.grid(row=0, column=1, padx=6, pady=3)
        ttk.Label(f, text="武器:").grid(row=1, column=0, sticky=tk.W, pady=3)
        cb = ttk.Combobox(f, textvariable=wvar, state="readonly", width=26)
        cb.grid(row=1, column=1, padx=6, pady=3, sticky=tk.W)
        ccombo.bind("<<ComboboxSelected>>", lambda e: self._fill_weapons(cb, catvar.get()))
        cb.bind("<<ComboboxSelected>>", lambda e: self._on_weapon_changed(side))
        chk = ttk.Checkbutton(f, text="满蓄力", variable=charged_var, style="Panel.TCheckbutton")
        chk.grid(row=2, column=1, sticky=tk.W, padx=6)
        # 可编辑参数
        ttk.Label(f, text="伤害:").grid(row=3, column=0, sticky=tk.W, pady=3)
        ev = tk.StringVar()
        ttk.Entry(f, textvariable=ev, width=8).grid(row=3, column=1, padx=6, pady=3, sticky=tk.W)
        ttk.Label(f, text="射速:").grid(row=4, column=0, sticky=tk.W, pady=3)
        ev2 = tk.StringVar()
        ttk.Entry(f, textvariable=ev2, width=8).grid(row=4, column=1, padx=6, pady=3, sticky=tk.W)
        label = tk.Label(f, text="", justify=tk.LEFT, bg=colors()["PANEL"], fg=colors()["MUTED"],
                         font=("Microsoft YaHei UI", 9), wraplength=240)
        label._semantic = "muted"
        label.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=(8, 0))
        setattr(self, "info_" + side, label)
        setattr(self, "chk_" + side, chk)
        setattr(self, "edit_" + side + "_alpha", ev)
        setattr(self, "edit_" + side + "_rpm", ev2)
        ev.trace_add("write", lambda *a, s=side: self._on_param_edit(s))
        ev2.trace_add("write", lambda *a, s=side: self._on_param_edit(s))
        if not catvar.get():
            catvar.set(CATEGORIES_MAIN[0])
        self._fill_weapons(cb, catvar.get())
        self._on_weapon_changed(side)

    # ---------------- 主题 ----------------
    def _walk(self):
        stack = [self.root]
        while stack:
            w = stack.pop()
            yield w
            stack.extend(w.winfo_children())

    def _toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self._apply_theme()
        self._auto_run()

    def _apply_theme(self):
        global CURRENT_THEME
        CURRENT_THEME = self.theme
        C = THEMES[self.theme]
        setup_style()
        self.root.configure(bg=C["BG"])
        self.title_l.configure(foreground=C["ACCENT_DK"])
        self.mode_l.configure(foreground=C["MUTED"])
        self.theme_btn.configure(text="🌓 浅色" if self.theme == "dark" else "🌓 深色")
        self.res_text.configure(bg=C["RES_BG"], fg=C["TEXT"])
        self.res_text.tag_configure("title", foreground=C["ACCENT_DK"])
        self.res_text.tag_configure("big", foreground=C["DANGER"])
        self.res_text.tag_configure("muted", foreground=C["MUTED"])
        self.res_text.tag_configure("part", foreground=C["TEXT"])
        self.res_text.tag_configure("custom", foreground=C["BADGE"])
        for w in self._walk():
            if isinstance(w, tk.Label):
                sem = getattr(w, "_semantic", "text")
                fg = {"badge": C["BADGE"], "danger": C["DANGER"],
                      "muted": C["MUTED"]}.get(sem, C["TEXT"])
                w.configure(bg=C["PANEL"], fg=fg)
            elif isinstance(w, tk.Text):
                w.configure(bg=C["RES_BG"], fg=C["TEXT"])
            elif isinstance(w, tk.Canvas):
                w.configure(bg=C["CANVAS_BG"], highlightbackground=C["LINE"])

    # ---------------- 事件 ----------------
    def _bind_auto(self):
        for v in (self.boost_var, self.hit_var, self.target_var, self.armor_var,
                  self.charged_l, self.charged_r):
            v.trace_add("write", lambda *a: self._schedule_auto())
        for v in (self.edit_alpha, self.edit_rpm, self.cw_damage, self.cw_rpm,
                  self.cw_pellet, self.custom_health, self.custom_head,
                  self.custom_torso, self.custom_arms, self.custom_legs):
            v.trace_add("write", lambda *a: (self._on_param_edit("l"), self._schedule_auto()))
        self.cw_type.trace_add("write", lambda *a: self._schedule_auto())

    def _schedule_auto(self):
        if self._auto_after is not None:
            try:
                self.root.after_cancel(self._auto_after)
            except tk.TclError:
                pass
        self._auto_after = self.root.after(120, self._auto_run)

    def _auto_run(self):
        self._auto_after = None
        try:
            if self.mode.get() == "compare":
                self._calc_compare()
            else:
                self._calc_single()
            self._refresh_thumb()
        except Exception:
            pass

    def _on_mode(self):
        for w in self.left_pane.winfo_children():
            w.destroy()
        self.cat_var = tk.StringVar(value=CATEGORIES[0])
        if self.mode.get() == "compare":
            self._build_compare()
        else:
            self._build_single()

    def _on_cat_l(self, event=None):
        cat = self.cat_var.get()
        if cat == "自定义武器":
            self.wvar_l.set("自定义武器")
            self.wcombo_l["values"] = []
            self.cw_frame.pack(fill=tk.X, pady=(8, 0))
            self.edit_alpha_entry.config(state="disabled")
            self.edit_rpm_entry.config(state="disabled")
        else:
            self.cw_frame.pack_forget()
            self.edit_alpha_entry.config(state="normal")
            self.edit_rpm_entry.config(state="normal")
            self._fill_weapons(self.wcombo_l, cat)
        self._on_weapon_changed("l")
        self._schedule_auto()

    def _fill_weapons(self, combo, cat):
        if cat in WEAPONS_BY_CAT:
            combo["values"] = [w["name"] for w in WEAPONS_BY_CAT[cat]]
            combo.set(combo["values"][0])

    def _on_weapon_changed(self, side):
        wvar = self.wvar_l if side == "l" else self.wvar_r
        weapon = self.get_weapon(wvar)
        # 填参数输入框
        if side == "l":
            self.edit_alpha.set("%.1f" % weapon["alpha"] if weapon else "")
            self.edit_rpm.set(str(int(weapon["fireRate"])) if weapon and weapon["fireRate"] else "")
        else:
            ev = getattr(self, "edit_" + side + "_alpha", None)
            ev2 = getattr(self, "edit_" + side + "_rpm", None)
            if ev and ev2 and weapon:
                ev.set("%.1f" % weapon["alpha"])
                ev2.set(str(int(weapon["fireRate"])) if weapon["fireRate"] else "")
        # 满蓄力可见性
        chk = getattr(self, "chk_" + side, None)
        if chk is not None:
            if is_charge_weapon(weapon):
                chk.grid()
            else:
                chk.grid_remove()
                (self.charged_l if side == "l" else self.charged_r).set(False)
        # 信息
        label = getattr(self, "info_" + side, None)
        try:
            if label is not None and label.winfo_exists():
                self.show_weapon_info(weapon, label)
        except tk.TclError:
            pass
        if side == "l":
            warn = getattr(self, "warn_l", None)
            if warn is not None:
                try:
                    if self.is_explosive(weapon) and weapon.get("explosionRadius"):
                        warn.config(text="⚠ 爆炸武器：伤害含直击+爆炸（半径 %sm），按命中即爆炸计算" %
                                    weapon["explosionRadius"])
                    else:
                        warn.config(text="")
                except tk.TclError:
                    pass
        self._schedule_auto()

    def _on_param_edit(self, side):
        try:
            if side == "l" and self.mode.get() == "single" and hasattr(self, "custom_badge_l"):
                base = self.get_weapon(self.wvar_l)
                a = float(self.edit_alpha.get())
                r = float(self.edit_rpm.get() or 0)
                if base and not base.get("is_custom") and (abs(a - base["alpha"]) > 0.01 or abs(r - (base["fireRate"] or 0)) > 0.01):
                    self.custom_badge_l.config(text="◆ 已按自定义参数计算")
                else:
                    self.custom_badge_l.config(text="")
        except (ValueError, tk.TclError):
            try:
                if hasattr(self, "custom_badge_l"):
                    self.custom_badge_l.config(text="◆ 参数无效")
            except tk.TclError:
                pass

    def _on_boost(self, val):
        self.boost_label_var.set("%+.0f%%" % float(val))

    def _on_target_changed(self):
        t = self.target_var.get()
        if t == "自定义目标":
            self.custom_frame.pack(fill=tk.X, pady=(8, 0))
        else:
            self.custom_frame.pack_forget()
            self.armor_var.set(TARGETS[t]["armor"])
        self._schedule_auto()

    # ---------------- 数据 ----------------
    def get_target(self):
        t = self.target_var.get()
        if t == "自定义目标":
            return {"health": float(self.custom_health.get()),
                    "parts": {"head": float(self.custom_head.get()),
                              "torso": float(self.custom_torso.get()),
                              "arms": float(self.custom_arms.get()),
                              "legs": float(self.custom_legs.get())},
                    "armor": self.armor_var.get(), "cap": None}
        return TARGETS[t]

    def get_custom_weapon(self):
        try:
            dmg = max(0.0, float(self.cw_damage.get()))
            rpm = max(0.0, float(self.cw_rpm.get()))
            pellet = max(1, int(float(self.cw_pellet.get())))
        except ValueError:
            return None
        dmgmap = {"DamagePhysical": 0.0, "DamageEnergy": 0.0, "DamageDistortion": 0.0,
                  "DamageThermal": 0.0, "DamageBiochemical": 0.0, "DamageStun": 0.0}
        dmgmap["DamagePhysical" if self.cw_type.get() == "物理" else "DamageEnergy"] = dmg
        return {"name": "自定义武器", "category": "自定义武器", "fireRate": rpm,
                "heatPerShot": 0.0, "damage": dmgmap, "pellet": pellet, "mult": 1.0,
                "alpha": dmg * pellet, "alphaCharged": None, "chargeTime": None,
                "chargeDM": None, "chargeBurst": None, "dps": None,
                "flags": "常规", "note": "", "is_custom": True}

    def get_weapon(self, wvar):
        if wvar.get() == "自定义武器":
            return self.get_custom_weapon()
        for w in WEAPONS:
            if w["name"] == wvar.get():
                return w
        return None

    def get_effective_weapon(self, wvar, side="l"):
        base = self.get_weapon(wvar)
        if base is None:
            return None
        if base.get("is_custom"):
            return base
        if self.mode.get() == "single" and side == "l":
            ev, ev2 = self.edit_alpha, self.edit_rpm
        else:
            ev = getattr(self, "edit_" + side + "_alpha", None)
            ev2 = getattr(self, "edit_" + side + "_rpm", None)
            if ev is None:
                return base
        try:
            a = float(ev.get())
            r = float(ev2.get() or 0)
        except ValueError:
            return base
        if abs(a - base["alpha"]) < 0.01 and abs(r - (base["fireRate"] or 0)) < 0.01:
            return base
        w = dict(base)
        w["fireRate"] = r
        w["is_customized"] = True
        dmg = dict(base["damage"])
        total = sum(dmg.values())
        target = a / base["pellet"]
        if total > 0:
            for t in dmg:
                dmg[t] = dmg[t] * target / total
        else:
            dmg["DamagePhysical"] = target
        w["damage"] = dmg
        w["alpha"] = a
        if base.get("alphaCharged") is not None:
            w["alphaCharged"] = a * (base.get("chargeDM") or 1.0)
        return w

    def is_explosive(self, weapon):
        return weapon is not None and "爆炸" in weapon.get("flags", "")

    def show_weapon_info(self, weapon, label):
        if not weapon:
            label.config(text="")
            return
        parts = ["射速: %s RPM" % ("—" if not weapon["fireRate"] else int(weapon["fireRate"]))]
        if "蓄力" in weapon.get("flags", "") and weapon["alphaCharged"] is not None:
            parts.append("不蓄力 %.1f | 满蓄力 %.1f (x%s)" % (weapon["alpha"], weapon["alphaCharged"],
                                                              weapon["chargeDM"]))
            if weapon.get("chargeTime"):
                parts.append("蓄力时间 %.1fs" % weapon["chargeTime"])
        elif weapon.get("dps"):
            parts.append("DPS %.1f | 每tick %.1f" % (weapon["dps"], weapon["alpha"]))
        else:
            parts.append("单发 %.1f" % weapon["alpha"])
        if weapon.get("explosionRadius"):
            parts.append("爆炸半径 %sm" % weapon["explosionRadius"])
        if weapon.get("heatPerShot"):
            parts.append("过热/发 %.2f" % weapon["heatPerShot"])
        if weapon.get("pellet", 1) > 1:
            parts.append("%d 弹丸" % weapon["pellet"])
        label.config(text="   |  ".join(parts))

    # ---------------- 减伤预览 ----------------
    def _refresh_thumb(self):
        try:
            target = self.get_target()
            weapon = self.get_effective_weapon(self.wvar_l, "l")
            if weapon is None:
                weapon = self.get_weapon(self.wvar_l)
        except Exception:
            self.thumb_canvas.delete("all")
            return
        c = self.thumb_canvas
        c.delete("all")
        x, y0 = 36, 14
        w, h = 34, 34
        head = (x, y0, x + w, y0 + h)
        torso = (x + 8, y0 + h + 4, x + w - 8, y0 + h + 46)
        armL = (x + 1, y0 + h + 6, x + 8, y0 + h + 44)
        armR = (x + w - 8, y0 + h + 6, x + w - 1, y0 + h + 44)
        legL = (x + 8, y0 + h + 48, x + 16, y0 + h + 90)
        legR = (x + 18, y0 + h + 48, x + 26, y0 + h + 90)
        shapes = {"head": head, "torso": torso, "arms": (armL, armR), "legs": (legL, legR)}

        am = ARMORS[ARMOR_KEYS[self.armor_var.get()]]
        dom = max(DAMAGE_TYPES, key=lambda t: weapon["damage"][t])
        armor_mult = am["mult"][dom]

        hit_key = dict(PARTS)[self.hit_var.get()]
        C = THEMES[self.theme]
        for key, box in shapes.items():
            fill = C["THUMB_FILL_HIT"] if key == hit_key else C["THUMB_FILL"]
            if isinstance(box, tuple) and isinstance(box[0], tuple):
                for b in box:
                    c.create_rectangle(*b, fill=fill, outline=C["THUMB_OUTLINE"])
            else:
                c.create_rectangle(*box, fill=fill, outline=C["THUMB_OUTLINE"])

        bx = 90
        c.create_text(bx, y0 - 2, text="部位减伤 × 护甲减伤 = 总减伤", anchor=tk.W,
                      font=("Microsoft YaHei UI", 8, "bold"), fill=C["ACCENT_DK"])
        for i, (pname, pkey) in enumerate(PARTS):
            yy = y0 + 6 + i * 30
            pm = target["parts"][pkey]
            tm = pm * armor_mult
            sel = pname == self.hit_var.get()
            c.create_text(bx, yy, text="%s" % pname, anchor=tk.W,
                          font=("Microsoft YaHei UI", 9, "bold"),
                          fill=C["DANGER"] if sel else C["THUMB_DIM"])
            c.create_text(bx + 30, yy, text="x%.2f" % pm, anchor=tk.W,
                          font=("Microsoft YaHei UI", 10, "bold"), fill=C["DANGER"])
            c.create_text(bx + 86, yy, text="x", anchor=tk.W, font=("Microsoft YaHei UI", 10), fill=C["MUTED"])
            c.create_text(bx + 102, yy, text="%.2f" % armor_mult, anchor=tk.W,
                          font=("Microsoft YaHei UI", 10, "bold"), fill=C["THUMB_ACCENT"])
            c.create_text(bx + 158, yy, text="=", anchor=tk.W, font=("Microsoft YaHei UI", 10), fill=C["MUTED"])
            c.create_text(bx + 174, yy, text="%.2f" % tm, anchor=tk.W,
                          font=("Microsoft YaHei UI", 11, "bold"), fill=C["OK"])
            dmg = per_shot_damage(weapon, am["mult"], am.get("caps", {}), pm, target.get("cap"),
                                  self.boost_var.get() / 100.0, self.charged_l.get())
            btk = math.ceil(target["health"] / dmg) if dmg > 0 else INF
            c.create_text(bx + 240, yy, text="伤害 %.1f | BTK %s" % (dmg, fmt_btk(btk)), anchor=tk.W,
                          font=("Microsoft YaHei UI", 8), fill=C["MUTED"])
        c.create_text(bx, y0 + 132, text="目标 %d HP | %s" % (target["health"], self.armor_var.get()),
                      anchor=tk.W, font=("Microsoft YaHei UI", 8, "bold"), fill=C["THUMB_DIM"])
        c.create_text(bx, y0 + 150, text="（红=部位倍率  蓝=护甲倍率  绿=总倍率）", anchor=tk.W,
                      font=("Microsoft YaHei UI", 8), fill=C["MUTED"])

    # ---------------- 计算 ----------------
    def _calc_single(self):
        weapon = self.get_effective_weapon(self.wvar_l, "l")
        if weapon is None:
            self._show_lines(["请先选择武器"])
            return
        target = self.get_target()
        part_key = dict(PARTS)[self.hit_var.get()]
        boost = self.boost_var.get() / 100.0
        r = calc(weapon, self.armor_var.get(), target, part_key, boost, self.charged_l.get())
        self._show_result(weapon, target, r, part_key)

    def _calc_compare(self):
        wl = self.get_effective_weapon(self.wvar_l, "l")
        wr = self.get_effective_weapon(self.wvar_r, "r")
        if wl is None or wr is None:
            self._show_lines(["请先选择左右两把武器"])
            return
        target = self.get_target()
        part_key = dict(PARTS)[self.hit_var.get()]
        boost = self.boost_var.get() / 100.0
        rl = calc(wl, self.armor_var.get(), target, part_key, boost, self.charged_l.get())
        rr = calc(wr, self.armor_var.get(), target, part_key, boost, self.charged_r.get())

        self.res_text.config(state="normal")
        self.res_text.delete("1.0", tk.END)
        self.res_text.insert("end", "%s  vs  %s\n" % (wl["name"], wr["name"]), "title")
        self.res_text.insert("end", "目标 %s（%d HP）  %s  命中%s\n\n" %
                             (self.target_var.get(), target["health"], self.armor_var.get(), self.hit_var.get()))
        for name, r in (("左侧", rl), ("右侧", rr)):
            self.res_text.insert("end", "%s：单发 %.2f | BTK %s | TTK %s | DPS %.0f\n" %
                                 (name, r["dmg"], fmt_btk(r["btk"]), fmt_ms(r["ttk_ms"]), r["dps"]))
        diff = rl["btk"] - rr["btk"]
        verdict = "BTK 相同" if diff == 0 else "%s侧更快 %d 发" % ("右" if diff > 0 else "左", abs(diff))
        self.res_text.insert("end", "\nBTK 差距：%s" % verdict, "big")
        self.res_text.config(state="disabled")

    def _show_result(self, weapon, target, r, part_key):
        self.res_text.config(state="normal")
        self.res_text.delete("1.0", tk.END)
        name = weapon["name"]
        if weapon.get("is_customized"):
            name += "  ◆自定义参数"
        self.res_text.insert("end", "%s\n" % name, "title")
        self.res_text.insert("end", "目标 %s（%d HP） | %s | 命中%s\n" %
                             (self.target_var.get(), r["health"], self.armor_var.get(), self.hit_var.get()), "muted")
        self.res_text.insert("end", "\n")
        self.res_text.insert("end", "击杀所需（BTK）：%s 发\n" % fmt_btk(r["btk"]), "big")
        self.res_text.insert("end", "TTK：%s\n" % fmt_ms(r["ttk_ms"]))
        self.res_text.insert("end", "单发伤害：%.2f    DPS：%.0f\n" % (r["dmg"], r["dps"]))
        self.res_text.insert("end", "\n各部位 BTK：\n", "title")
        for pname, pkey in PARTS:
            rp = calc(weapon, self.armor_var.get(), target, pkey, self.boost_var.get() / 100.0, self.charged_l.get())
            mark = "◀" if pname == self.hit_var.get() else " "
            self.res_text.insert("end", " %s %s：单发 %.2f | BTK %s | TTK %s\n" %
                                 (mark, pname, rp["dmg"], fmt_btk(rp["btk"]), fmt_ms(rp["ttk_ms"])), "part")
        self.res_text.config(state="disabled")

    def _show_lines(self, lines):
        self.res_text.config(state="normal")
        self.res_text.delete("1.0", tk.END)
        for ln in lines:
            self.res_text.insert("end", ln + "\n")
        self.res_text.config(state="disabled")


def _icon_path():
    """定位应用图标：PyInstaller 解包目录或源码目录。"""
    import os
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    for name in ("app_icon_black.ico", "app_icon_white.ico"):
        p = os.path.join(base, name)
        if os.path.exists(p):
            return p
    return None


def main():
    root = tk.Tk()
    root.option_add("*Font", ("Microsoft YaHei UI", 10))
    setup_style()
    icon = _icon_path()
    if icon:
        try:
            root.iconbitmap(icon)
        except tk.TclError:
            pass
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

