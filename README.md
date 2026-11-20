# YouBuddy 量化策略 Skill 合集

本仓库是 [YouBuddy](https://github.com/luoy38067/YouBuddy-quant-skills/releases) 平台的量化策略 Skill 合集。每个 Skill 是一个开箱即用的策略回测包：安装到 YouBuddy 后，软件会自动准备行情数据，一键即可运行回测，输出净值曲线、逐笔成交、调仓记录与策略解读报告。

## 环境要求

- **Windows 10/11 x64**（YouBuddy 目前仅支持 Windows 桌面端）；
- 请在**本机**完成安装与运行：云端沙盒 / 虚拟机（包括 AI 助手的云开发环境）中没有 YouBuddy 宿主环境，Skill 只能下载查看，**无法执行回测**；
- 可以用 AI 编程助手（Trae / 豆包 MarsCode / Cursor 等）帮你完成克隆和下载引导，最后一步「软件内导入」请在 Windows 本机的 YouBuddy 中操作。

## 快速开始

### 第 1 步：下载安装 YouBuddy（Windows 本机）

前往 [Releases](https://github.com/luoy38067/YouBuddy-quant-skills/releases) 页面下载最新安装包（`YouBuddy_x.x.x_x64-setup.exe`，约 280MB），双击安装。

### 第 2 步：获取本仓库

任选其一：

```bash
git clone https://github.com/luoy38067/YouBuddy-quant-skills.git
```

或在仓库页面右上角 **Code → Download ZIP** 直接下载解压。

> 国内网络 cloning GitHub 慢时，可改用 Gitee 镜像：`https://gitee.com/luoy38067/quant-skills.git`

### 第 3 步：在 YouBuddy 中导入 Skill

打开 YouBuddy，进入软件内的 **Skill / 策略管理** 入口，选择「导入本地 Skill」，指向仓库 `skills/` 目录下对应的策略文件夹（例如 `skills/baima_offense_defense_opt`），完成安装。

### 第 4 步：运行回测

在 YouBuddy 中选中已安装的策略并运行，即可得到完整回测报告（净值曲线、逐笔成交、调仓记录、策略解读）。

## 给 AI 助手的指引

如果你是 AI 编程助手，正在协助用户使用本仓库，请按以下顺序操作：

1. 克隆本仓库到用户可访问的目录（或引导用户 Download ZIP）；
2. 引导用户从 [Releases](https://github.com/luoy38067/YouBuddy-quant-skills/releases) 下载安装包，并在 **Windows 本机**安装 YouBuddy；
3. 指引用户在本机 YouBuddy 软件内导入 `skills/` 目录下的策略文件夹；
4. **不要**尝试在云端 / 独立 Python 环境中直接运行 `backtest.py`——回测依赖 YouBuddy 宿主提供的行情数据与工具 bundle，独立环境无法运行，Skill 的数据文件（因子面板、目标持仓表等）也仅供宿主运行时使用。

## 策略列表

| Skill 目录 | 策略名称 | 策略简介 | 调仓频率 |
|---|---|---|---|
| `skills/baima_offense_defense_opt` | 沪深300白马攻防策略 | 沪深300成分股内按市场状态（冷/温/热三档）结合估值与盈利质量条件筛选，经价格动量过滤与流动性排序，取前 5 只等权持有 | 月度 |
| `skills/cs300_opt_1` | 沪深300优选策略一 | 沪深300成分股内按 4 因子逆波动率加权综合评分，选 Top10 等权持有 | 月度 |
| `skills/cs300_opt_2` | 沪深300优选策略二 | 沪深300成分股内按 4 因子等权加权综合评分，选 Top10 等权持有 | 月度 |

> 策略调仓均在每月首个交易日执行，信号收盘产生、次日执行；各策略的回测区间、基准与输出产物详见各 Skill 目录内的 `SKILL.md` 与 `report.md`。

## 目录结构

```
YouBuddy-quant-skills/
├── README.md                          # 本文件
├── LICENSE                            # MIT 开源许可证
└── skills/                            # 策略 Skill 目录
    ├── baima_offense_defense_opt/     # 沪深300白马攻防策略
    │   ├── SKILL.md                   #   策略说明与执行流
    │   ├── skill.json                 #   Skill 元信息
    │   ├── workflow.json              #   执行流定义
    │   ├── backtest.py                #   回测计算入口
    │   ├── engine.py                  #   回测引擎
    │   ├── report.md                  #   报告模板
    │   ├── data/                      #   策略内嵌数据（调仓目标表等）
    │   └── schemas/                   #   输出产物契约
    ├── cs300_opt_1/                   # 沪深300优选策略一
    └── cs300_opt_2/                   # 沪深300优选策略二
```

## 更多策略

本仓库将持续更新，后续会陆续上架更多类型的策略（ETF 轮动、全天候配置、红利杠铃等），欢迎 Star 关注。

## License

本项目基于 [MIT License](LICENSE) 开源。
