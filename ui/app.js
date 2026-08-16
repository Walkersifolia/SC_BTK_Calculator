/* ============================================================
   BTK 计算器前端逻辑 — 通过 fetch 调用后端 API
   ============================================================ */
"use strict";

const API = ""; // 同源（后端服务提供 /api/* 与静态文件）

const state = {
  mode: "single",
  theme: localStorage.getItem("btk_theme") || "light",
  weaponsByCat: {},
  categories: [],
  armorDisplay: [],
  targetDisplay: [],
  parts: [],
  metaLoaded: false,
};

/* ── 工具 ── */
function $(id) { return document.getElementById(id); }

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

async function api(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error("API " + r.status);
  return r.json();
}

function params(obj) {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(obj)) {
    if (v !== undefined && v !== null && v !== "") sp.set(k, v);
  }
  return sp.toString();
}

/* ── 主题 ── */
function applyTheme() {
  document.body.setAttribute("data-theme", state.theme);
  $("themeToggle").textContent = state.theme === "dark" ? "\u2600" : "\u263E";
  localStorage.setItem("btk_theme", state.theme);
}

/* ── 数据加载 ── */
async function loadMeta() {
  const meta = await api("/api/meta");
  state.categories = meta.categories;
  state.armorDisplay = meta.armors;
  state.targetDisplay = meta.targets;
  state.parts = meta.parts;
  const w = await api("/api/weapons");
  state.weaponsByCat = w.byCategory;

  fillSelect($("catSelect"), state.categories);
  fillSelect($("armorSelect"), state.armorDisplay);
  fillSelect($("targetSelect"), state.targetDisplay);
  fillSelect($("partSelect"), state.parts.map(p => p[0]));
  fillSelect($("cmpLCat"), state.categories);
  fillSelect($("cmpRCat"), state.categories);

  $("catSelect").value = state.categories[0];
  $("cmpLCat").value = state.categories[0];
  $("cmpRCat").value = state.categories[0];
  syncDSelects();
  onCatChange();
  onCatChange("cmpL");
  onCatChange("cmpR");
  state.metaLoaded = true;
  refresh();
}

function fillSelect(sel, values) {
  sel.innerHTML = "";
  for (const v of values) {
    const o = document.createElement("option");
    o.value = v;
    o.textContent = v;
    sel.appendChild(o);
  }
  syncDSelects();
}

/* ── 自绘下拉（WebView2 原生 select 弹层不随页面主题渲染，自绘替代）── */
function buildCustomSelects() {
  document.querySelectorAll(".dselect").forEach(btn => {
    if (btn.dataset.bound) return;
    btn.dataset.bound = "1";
    btn.addEventListener("click", () => {
      const menu = document.querySelector(`.dmenu[data-menu-for="${btn.dataset.for}"]`);
      if (!menu) return;
      if (menu.hidden) {
        openMenu(btn);
      } else {
        closeMenus();
      }
    });
    btn.addEventListener("keydown", e => {
      if (e.key === "Escape" || e.key === "Tab") closeMenus();
    });
  });
  document.addEventListener("click", e => {
    if (!e.target.closest(".select-wrap")) closeMenus();
  });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeMenus();
  });
}

function syncDSelects() {
  document.querySelectorAll(".dselect").forEach(btn => {
    const sel = document.getElementById(btn.dataset.for);
    const label = btn.querySelector(".dselect-label");
    if (sel && label) label.textContent = sel.value || "";
  });
}

function openMenu(btn) {
  closeMenus();
  const sel = document.getElementById(btn.dataset.for);
  const menu = document.querySelector(`.dmenu[data-menu-for="${btn.dataset.for}"]`);
  if (!sel || !menu) return;
  syncDSelects();
  menu.innerHTML = "";
  for (const opt of sel.options) {
    const it = document.createElement("button");
    it.type = "button";
    it.className = "dmenu-item" + (opt.value === sel.value ? " selected" : "");
    it.textContent = opt.textContent;
    it.addEventListener("click", () => {
      sel.value = opt.value;
      sel.dispatchEvent(new Event("change", { bubbles: true }));
      closeMenus();
      syncDSelects();
    });
    menu.appendChild(it);
  }
  menu.hidden = false;
  btn.setAttribute("aria-expanded", "true");
}

function closeMenus() {
  document.querySelectorAll(".dmenu").forEach(m => { m.hidden = true; });
  document.querySelectorAll(".dselect").forEach(b => b.setAttribute("aria-expanded", "false"));
}

/* ── 分类/武器联动 ── */
function onCatChange(side) {
  const catSel = side ? $(side === "cmpL" ? "cmpLCat" : "cmpRCat") : $("catSelect");
  const wSel = side ? $(side === "cmpL" ? "cmpLWeapon" : "cmpRWeapon") : $("weaponSelect");
  const cat = catSel.value;
  if (cat === "自定义武器") {
    wSel.innerHTML = "";
    const o = document.createElement("option");
    o.value = "自定义武器";
    o.textContent = "自定义武器";
    wSel.appendChild(o);
    $("customWeaponCard").hidden = false;
    $("editAlpha").disabled = true;
    $("editRpm").disabled = true;
  } else {
    $("customWeaponCard").hidden = true;
    $("editAlpha").disabled = false;
    $("editRpm").disabled = false;
    const weapons = state.weaponsByCat[cat] || [];
    fillSelect(wSel, weapons.map(w => w.name));
    wSel.value = weapons.length ? weapons[0].name : "";
  }
  if (side) { onWeaponChange(side); } else { onWeaponChange(); }
  syncDSelects();
}

function onWeaponChange(side) {
  updateWeaponInfo(side);
  refresh();
}

function currentWeaponName(side) {
  const sel = side ? $(side === "cmpL" ? "cmpLWeapon" : "cmpRWeapon") : $("weaponSelect");
  return sel ? sel.value : "";
}

/* ── 武器信息 ── */
function describeWeapon(w) {
  if (!w) return "";
  const parts = [];
  parts.push("射速: " + (w.fireRate ? w.fireRate + " RPM" : "—"));
  if (w.flags && w.flags.includes("蓄力") && w.alphaCharged != null) {
    parts.push(`不蓄力 ${w.alpha.toFixed(1)} | 满蓄力 ${w.alphaCharged.toFixed(1)} (x${w.chargeDM})`);
    if (w.chargeTime) parts.push(`蓄力时间 ${w.chargeTime}s`);
  } else if (w.dps) {
    parts.push(`DPS ${w.dps.toFixed(1)} | 每tick ${w.alpha.toFixed(1)}`);
  } else {
    parts.push(`单发 ${w.alpha.toFixed(1)}`);
  }
  if (w.explosionRadius) parts.push(`爆炸半径 ${w.explosionRadius}m`);
  if (w.heatPerShot) parts.push(`过热/发 ${w.heatPerShot}`);
  if (w.pellet > 1) parts.push(`${w.pellet} 弹丸`);
  return parts.join("   |   ");
}

async function updateWeaponInfo(side) {
  const name = currentWeaponName(side);
  if (!name) return;
  const el = side ? $(side === "cmpL" ? "cmpLInfo" : "cmpRInfo") : $("weaponInfo");
  try {
    const w = await api("/api/weapons");
    let found = null;
    for (const cat of Object.keys(w.byCategory)) {
      const f = w.byCategory[cat].find(x => x.name === name);
      if (f) { found = f; break; }
    }
    if (el) el.textContent = found ? describeWeapon(found) : "";
    // 警告（爆炸武器）
    if (!side) {
      const warn = $("warnText");
      if (found && found.flags && found.flags.includes("爆炸")) {
        warn.hidden = false;
        warn.textContent = found.explosionRadius
          ? `⚠ 爆炸武器：伤害含直击+爆炸（半径 ${found.explosionRadius}m），按命中即爆炸计算`
          : "⚠ 爆炸武器";
      } else {
        warn.hidden = true;
      }
    }
    // 填参数框
    if (found && !side) {
      $("editAlpha").value = found.alpha.toFixed(1);
      $("editRpm").value = found.fireRate ? String(Math.round(found.fireRate)) : "";
    }
  } catch (e) { /* 静默 */ }
}

/* ── 计算 ── */
function baseParams(side) {
  const p = {
    armor: $("armorSelect").value,
    target: $("targetSelect").value,
    part: state.parts.find(pp => pp[0] === $("partSelect").value)[1],
    boost: $("boostRange").value,
  };
  if (p.target === "自定义目标") {
    p.custom_target_health = $("ctHealth").value;
    p.custom_target_head = $("ctHead").value;
    p.custom_target_torso = $("ctTorso").value;
    p.custom_target_arms = $("ctArms").value;
    p.custom_target_legs = $("ctLegs").value;
  }
  return p;
}

function customWeaponParams() {
  return {
    custom_damage: $("cwDamage").value,
    custom_rpm: $("cwRpm").value,
    custom_pellet: $("cwPellet").value,
    custom_type: $("cwType").value,
  };
}

async function refresh() {
  if (!state.metaLoaded) return;
  try {
    if (state.mode === "single") {
      await refreshSingle();
    } else {
      await refreshCompare();
    }
    await refreshPreview();
  } catch (e) {
    showResult("加载失败: " + e.message);
  }
}

async function refreshSingle() {
  const name = currentWeaponName();
  if (!name) { showResult("请先选择武器"); return; }
  const p = baseParams();
  if (name === "自定义武器") Object.assign(p, customWeaponParams());
  p.name = name;
  p.charged = $("chargedChk").checked;
  p.edit_alpha = $("editAlpha").value;
  p.edit_rpm = $("editRpm").value;

  const d = await api("/api/calc?" + params(p));
  renderSingle(d);
}

function renderSingle(d) {
  const r = d.result;
  const lines = [];
  lines.push({ t: "title", s: d.weapon.name + (d.weapon.is_customized ? "  ◆自定义参数" : "") });
  lines.push({ t: "muted", s: `目标 ${d.target.name}（${r.health} HP） | ${d.target.armor} | 命中${d.target.part}` });
  lines.push({ t: "spacer" });
  lines.push({ t: "big", s: `击杀所需（BTK）：${fmtBtk(r.btk)} 发` });
  lines.push({ t: "plain", s: `TTK：${fmtMs(r.ttk_ms)}` });
  lines.push({ t: "plain", s: `单发伤害：${r.dmg.toFixed(2)}    DPS：${Math.round(r.dps)}` });
  lines.push({ t: "title", s: "各部位 BTK：" });
  for (const pp of d.perPart) {
    const rr = pp.r;
    const mark = pp.key === d.target.part ? "◀" : " ";
    lines.push({ t: "plain", s: `    ${mark} ${pp.part}：单发 ${rr.dmg.toFixed(2)} | BTK ${fmtBtk(rr.btk)} | TTK ${fmtMs(rr.ttk_ms)}` });
  }
  showResult(lines);
}

async function refreshCompare() {
  const ln = currentWeaponName("cmpL");
  const rn = currentWeaponName("cmpR");
  if (!ln || !rn) { showResult("请先选择左右两把武器"); return; }
  const p = baseParams();
  p.l_name = ln;
  p.r_name = rn;
  p.l_charged = $("cmpLCharged").checked;
  p.r_charged = $("cmpRCharged").checked;
  p.l_alpha = $("cmpLAlpha").value;
  p.l_rpm = $("cmpLRpm").value;
  p.r_alpha = $("cmpRAlpha").value;
  p.r_rpm = $("cmpRRpm").value;
  if (ln === "自定义武器") Object.assign(p, prefixCustom(customWeaponParams(), ""));
  if (rn === "自定义武器") Object.assign(p, customWeaponParams());
  const d = await api("/api/calc_compare?" + params(p));
  const lines = [];
  lines.push({ t: "title", s: `${d.left.weapon}  vs  ${d.right.weapon}` });
  lines.push({ t: "muted", s: `目标 ${$("targetSelect").value} | ${$("armorSelect").value} | 命中${$("partSelect").value}` });
  lines.push({ t: "spacer" });
  for (const [label, side] of [["左侧", d.left], ["右侧", d.right]]) {
    lines.push({ t: "plain", s: `${label}：单发 ${side.r.dmg.toFixed(2)} | BTK ${fmtBtk(side.r.btk)} | TTK ${fmtMs(side.r.ttk_ms)} | DPS ${Math.round(side.r.dps)}` });
  }
  lines.push({ t: "spacer" });
  lines.push({ t: "big", s: `BTK 差距：${d.verdict}` });
  showResult(lines);
}

function prefixCustom(cw, prefix) {
  const out = {};
  for (const [k, v] of Object.entries(cw)) out[prefix + k] = v;
  return out;
}

/* ── 结果渲染 ── */
function fmtBtk(n) { return n === Infinity ? "∞" : String(Math.round(n)); }
function fmtMs(v) { return v === Infinity ? "∞" : Math.round(v) + " ms"; }

function showResult(lines) {
  const el = $("resultText");
  el.innerHTML = "";
  for (const ln of lines) {
    if (ln.t === "spacer") {
      el.appendChild(document.createElement("br"));
    } else {
      const d = document.createElement("div");
      d.className = ln.t === "plain" ? "" : ln.t;
      d.textContent = ln.s;
      el.appendChild(d);
    }
  }
}

/* ── 部位预览 ── */
let lastPreview = null;

async function refreshPreview() {
  try {
    const name = currentWeaponName();
    if (!name) { clearPreview(); return; }
    const p = baseParams();
    if (name === "自定义武器") Object.assign(p, customWeaponParams());
    p.name = name;
    p.charged = $("chargedChk").checked;
    p.edit_alpha = $("editAlpha").value;
    p.edit_rpm = $("editRpm").value;
    const d = await api("/api/calc?" + params(p));
    renderPreview(d);
  } catch (e) { clearPreview(); }
}

function renderPreview(d) {
  lastPreview = d;
  const weapon = d.weapon;
  const target = d.target;
  // 高亮选中部位
  document.querySelectorAll(".body-part").forEach(r => {
    r.classList.toggle("active", r.dataset.part === target.part);
  });
  // 部位统计
  const stats = $("partStats");
  stats.innerHTML = "";
  for (const pp of d.perPart) {
    const div = document.createElement("div");
    div.className = "stat" + (pp.key === target.part ? " hl" : "");
    const rr = pp.r;
    div.innerHTML = `<span>${pp.part}</span><span><b>${rr.dmg.toFixed(1)}</b> / BTK ${fmtBtk(rr.btk)}</span>`;
    stats.appendChild(div);
  }
}

function clearPreview() {
  document.querySelectorAll(".body-part").forEach(r => r.classList.remove("active"));
  $("partStats").innerHTML = "";
}

/* ── 事件绑定 ── */
function bindEvents() {
  // 模式切换
  document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".mode-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.mode = btn.dataset.mode;
      $("singlePanel").hidden = state.mode !== "single";
      $("comparePanel").hidden = state.mode !== "compare";
      // 同步参数框
      syncEditToCompare();
      refresh();
    });
  });

  // 主题
  $("themeToggle").addEventListener("click", () => {
    state.theme = state.theme === "dark" ? "light" : "dark";
    applyTheme();
  });

  // 选择器
  $("catSelect").addEventListener("change", () => onCatChange());
  $("weaponSelect").addEventListener("change", () => onWeaponChange());
  $("cmpLCat").addEventListener("change", () => onCatChange("cmpL"));
  $("cmpLWeapon").addEventListener("change", () => onWeaponChange("cmpL"));
  $("cmpRCat").addEventListener("change", () => onCatChange("cmpR"));
  $("cmpRWeapon").addEventListener("change", () => onWeaponChange("cmpR"));

  // 右侧
  $("targetSelect").addEventListener("change", () => {
    $("customTargetCard").hidden = $("targetSelect").value !== "自定义目标";
    refresh();
  });
  $("armorSelect").addEventListener("change", refresh);
  $("partSelect").addEventListener("change", refresh);
  $("boostRange").addEventListener("input", () => {
    $("boostLabel").textContent = (Number($("boostRange").value) > 0 ? "+" : "") + $("boostRange").value + "%";
    refresh();
  });

  // 参数输入（防抖）
  const debounce = (fn, ms) => {
    let t;
    return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), 120); };
  };
  const debouncedRefresh = debounce(refresh, 120);
  for (const id of ["chargedChk", "cmpLCharged", "cmpRCharged", "editAlpha", "editRpm",
                     "cmpLAlpha", "cmpLRpm", "cmpRAlpha", "cmpRRpm",
                     "cwDamage", "cwRpm", "cwPellet", "cwType",
                     "ctHealth", "ctHead", "ctTorso", "ctArms", "ctLegs"]) {
    const el = $(id);
    if (el) el.addEventListener("input", debouncedRefresh);
    if (el && el.type === "checkbox") el.addEventListener("change", debouncedRefresh);
  }

  // 部位点击
  document.querySelectorAll(".body-part").forEach(rect => {
    rect.addEventListener("click", () => {
      const part = rect.dataset.part;
      const idx = state.parts.findIndex(p => p[1] === part);
      if (idx >= 0) {
        $("partSelect").value = state.parts[idx][0];
        refresh();
      }
    });
  });
}

function syncEditToCompare() {
  $("cmpLAlpha").value = $("editAlpha").value;
  $("cmpLRpm").value = $("editRpm").value;
  $("cmpRAlpha").value = $("editAlpha").value;
  $("cmpRRpm").value = $("editRpm").value;
}

/* ── 启动 ── */
async function init() {
  applyTheme();
  bindEvents();
  buildCustomSelects();
  try {
    await loadMeta();
  } catch (e) {
    showResult("无法连接后端服务: " + e.message);
  }
}

document.addEventListener("DOMContentLoaded", init);
