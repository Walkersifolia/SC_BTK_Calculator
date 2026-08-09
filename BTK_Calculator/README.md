# 星际公民 BTK 计算器

Star Citizen FPS 武器 BTK（Bullets To Kill，击杀所需子弹数）/ TTK / DPS 计算器。
数据来自 StarBreaker 解包的游戏 DataCore 记录（PTU 分支）。

## 功能

- 48 把 FPS 武器（含榴弹、光束、蓄力、爆炸武器）
- 13 种目标（玩家 / AI / Vanduul / vlk / Yormandi 等）
- 8 种护甲减伤（含超重甲 DamageCap）
- 4 部位命中倍率 + Canvas 减伤预览
- 单武器计算 / 左右武器对比
- 自定义武器 / 自定义目标 / 伤害增益 / 满蓄力 / 可编辑武器参数
- 爆炸武器按「直击 + 爆炸伤害」计算，显示爆炸半径

## 安装与运行

需要 Python 3.10+（含 tkinter）。

```powershell
pip install -r requirements.txt
python btk_calculator.py
```

打包为单文件 exe（可选）：

```powershell
pip install pyinstaller
pyinstaller SC_BTK_Calculator.spec
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
BTK_Calculator/
├── btk_calculator.py      # 主程序（tkinter GUI）
├── btk_data.py            # 生成的数据模块（勿手改）
├── generate_data.py       # 数据生成脚本（读解包记录）
├── SC_BTK_Calculator.spec # PyInstaller 打包配置
└── game_data/             # StarBreaker 解包数据快照
```

## 数据来源与版本

- 游戏分支：PTU（2026-08-09 快照）
- 解包工具：StarBreaker CLI v0.3.2
- 数据口径：
  - 光束武器 damage 为每 tick 伤害（dps/30），fireRate 显示 1800
  - 爆炸武器 damage 含直击 + 爆炸合计，note 标注爆炸伤害与半径
  - 护甲减伤取 DamageResistanceMacro 的 Multiplier 与 DamageCap
