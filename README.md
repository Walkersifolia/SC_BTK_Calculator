# 星际公民 BTK 计算器

Star Citizen FPS 武器 BTK（Bullets To Kill，击杀所需子弹数）/ TTK / DPS 计算器。
数据来自 StarBreaker 解包的游戏 DataCore 记录（PTU 分支）。

## 功能

- 48 把 FPS 武器（含榴弹、光束、蓄力、爆炸武器）
- 13 种目标（玩家 / AI / Vanduul / vlk / Yormandi 等）
- 8 种护甲减伤（含超重甲 DamageCap）
- 4 部位命中倍率 + SVG 减伤预览
- 单武器计算 / 左右武器对比
- 自定义武器 / 自定义目标 / 伤害增益 / 满蓄力 / 可编辑武器参数
- 爆炸武器按「直击 + 爆炸伤害」计算，显示爆炸半径
- 浅色 / 深色主题一键切换，圆角简洁 UI（WebView2 渲染，参考 VRCA.Toolbox.App 风格）

## 安装与运行

### 方式一：直接运行 exe（推荐）

双击项目根目录的 `SC_BTK_Calculator.exe`（单文件，已内置 WebView2 依赖与 SC LOGO 图标）。

### 方式二：源码运行

需要 Python 3.10+，以及 Windows 10/11（自带 WebView2 Runtime）。

```powershell
pip install -r requirements.txt
python main.py
```

> 旧版 tkinter 界面保留在 `btk_calculator.py`，计算逻辑已抽取为 `btk_core.py` 供新旧界面共用。

## 重新打包 exe

```powershell
pip install pyinstaller
python -m PyInstaller SC_BTK_Calculator.spec --noconfirm
copy dist\SC_BTK_Calculator.exe .   # 复制到项目根目录
```

## 架构

```
SC_BTK_Calculator.exe # 根目录启动 exe（单文件，双击即用）
main.py           # 入口：启动后端 + pywebview 打开 WebView2 窗口
backend.py        # 本地 HTTP 服务（/api/* 计算接口 + ui/ 静态文件）
btk_core.py       # 纯计算层（数据 + BTK/TTK/DPS 算法，无 UI）
btk_data.py       # 数据模块（48 武器 / 12 护甲 / 13 目标）
ui/
  index.html      # 前端页面（圆角卡片布局）
  style.css       # 浅/深双主题样式（CSS 变量）
  app.js          # 前端交互（fetch 调用后端 API）
assets/icons/     # 应用图标（exe 打包用）
```

## 数据更新

数据由 `generate_data.py` 从 StarBreaker 解包记录生成：

1. 用 StarBreaker 从游戏 `Data.p4k` 提取 `Game2.dcb`
2. 解包记录到 `game_data/full_extract/libs/foundry/records/`（本仓库已含最新快照）
3. 重新生成：

```powershell
python generate_data.py
```

> `game_data/` 目录是解包数据快照（约 60 万条记录，体积较大），可用 `generate_data.py` 重新生成 `btk_data.py` 后删除。

## 项目结构

```
├── SC_BTK_Calculator.exe # 启动 exe（单文件，双击运行）
├── main.py               # 入口（WebView2 UI）
├── backend.py            # 本地 HTTP 服务
├── btk_core.py           # 纯计算层
├── btk_data.py           # 数据模块（勿手改）
├── generate_data.py      # 数据生成脚本
├── btk_calculator.py     # 旧版 tkinter 界面（备用）
├── ui/                   # Web 前端（HTML/CSS/JS）
├── assets/icons/         # 应用图标
├── SC_BTK_Calculator.spec # PyInstaller 打包配置
├── requirements.txt      # 依赖（pywebview）
└── game_data/            # StarBreaker 解包数据快照（不入库）
```

## 数据来源与版本

- 游戏分支：PTU（2026-08-09 快照）
- 解包工具：StarBreaker CLI v0.3.2
- 数据口径：
  - 光束武器 damage 为每 tick 伤害（dps/30），fireRate 显示 1800
  - 爆炸武器 damage 含直击 + 爆炸合计，note 标注爆炸伤害与半径
  - 护甲减伤取 DamageResistanceMacro 的 Multiplier 与 DamageCap
