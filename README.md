# YouBuddy 量化策略 Skill 合集

本仓库是 [YouBuddy](https://github.com/luoy30867/quant-skills/releases) 平台的量化策略 Skill 合集。每个 Skill 是一个开箱即用的策略回测包：安装到 YouBuddy 后，软件会自动准备行情数据，一键即可运行回测，输出净值曲线、逐笔成交、调仓记录与策略解读报告。

## 快速开始

1. **下载安装 YouBuddy**：前往 [Releases](https://github.com/luoy30867/quant-skills/releases) 页面下载最新安装包（`YouBuddy_x.x.x_x64-setup.exe`），双击安装；
2. **获取本仓库**：执行 `git clone https://github.com/luoy30867/quant-skills.git`，或在页面右上角 Code → Download ZIP 直接下载；
3. **安装 Skill**：打开 YouBuddy，在软件内使用 Skill 导入功能，选择仓库 `skills/` 目录下对应的策略文件夹，完成安装；
4. **运行回测**：在 YouBuddy 中选中已安装的策略并运行，即可得到完整回测报告。

## 策略列表

| Skill 目录 | 策略名称 | 策略简介 | 调仓频率 |
|---|---|---|---|
| `skills/baima_offense_defense_opt` | 沪深300白马攻防策略 | 沪深300成分股内按市场状态（冷/温/热三档）结合估值与盈利质量条件筛选，经价格动量过滤与流动性排序，取前 5 只等权持有 | 月度 |
| `skills/cs300_opt_1` | 沪深300优选策略一 | 沪深300成分股内按 4 因子逆波动率加权综合评分，选 Top10 等权持有 | 月度 |
| `skills/cs300_opt_2` | 沪深300优选策略二 | 沪深300成分股内按 4 因子等权加权综合评分，选 Top10 等权持有 | 月度 |

> 策略调仓均在每月首个交易日执行，信号收盘产生、次日执行；各策略的回测区间、基准与输出产物详见各 Skill 目录内的 `SKILL.md` 与 `report.md`。

## 目录结构

```
quant-skills/
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
