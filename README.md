<div align="center">

# YouBuddy 量化策略 Skill 合集

**三个开箱即用的沪深300量化回测策略。**

[![License](https://img.shields.io/badge/License-MIT-3ECF8E?style=flat-square)](LICENSE)
[![Release](https://img.shields.io/github/v/release/luoy38067/YouBuddy-quant-skills?style=flat-square&color=0F9D8A&label=Release)](https://github.com/luoy38067/YouBuddy-quant-skills/releases/latest)
[![Platform](https://img.shields.io/badge/Windows-10%2F11%20x64-0078D6?style=flat-square&logo=windows)](https://github.com/luoy38067/YouBuddy-quant-skills/releases/latest)

</div>

---

## 这些 Skill 是做什么的

本仓库收录了三个可直接使用的量化策略 Skill。每个 Skill 是一个完整的回测包：策略逻辑、内嵌行情/因子数据、回测引擎与输出契约都放在同一个目录里。把它们部署进 YouBuddy（Windows 桌面软件）后，软件会准备好行情数据，选中策略一键回测，即可得到净值曲线、逐笔成交、调仓记录和策略解读报告。

三个策略都聚焦沪深300成分股，月频调仓（每月首个交易日执行，信号收盘产生、次日执行），默认回测区间为 2024-01-02 ~ 2026-11-10。

## 策略列表

| Skill 目录 | 策略名称 | 策略简介 | 调仓频率 | 默认回测区间 |
|---|---|---|---|---|
| `skills/baima_offense_defense_opt` | 沪深300白马攻防策略 | 沪深300成分股内按市场状态（冷/温/热三档）结合估值与盈利质量条件筛选，经价格动量过滤与流动性排序，取前 5 只等权持有 | 月度 | 2024-01-02 ~ 2026-11-10 |
| `skills/cs300_opt_1` | 沪深300优选策略一 | 沪深300成分股内按 4 因子逆波动率加权综合评分，选 Top10 等权持有 | 月度 | 2024-01-02 ~ 2026-11-10 |
| `skills/cs300_opt_2` | 沪深300优选策略二 | 沪深300成分股内按 4 因子等权加权综合评分，选 Top10 等权持有 | 月度 | 2024-01-02 ~ 2026-11-10 |

各策略的回测区间、基准与输出产物详见对应目录内的 `SKILL.md` 与 `report.md`。

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

## 给 AI 助手的部署说明

如果你是被用户带来查看本仓库的 AI 助手，请按下面的顺序协助。**全程不要替用户做决定。**

**第一步：介绍并询问**

用一两句话说明上面三个 Skill 是做什么的（见「策略列表」），然后问用户：「是否现在部署这套策略 Skill？」

用户明确同意之前，不要下载、安装或写入任何东西。如果用户有其他问题（例如想先看代码、了解策略逻辑），先正常回答。

**第二步：用户同意后，安装 YouBuddy（Windows 本机）**

- 告知用户：需要从 [Releases](https://github.com/luoy38067/YouBuddy-quant-skills/releases/latest) 下载 `YouBuddy_x.x.x_x64-setup.exe`（约 280MB），仅支持 Windows 10/11 x64 本机安装。
- 让用户确认并自行下载安装；如果你在本机且用户已授权，可以协助下载，但要如实说明文件来源、大小与用途。
- 云端沙盒 / 虚拟机里没有 YouBuddy 宿主环境，不要在那里尝试安装或运行回测。

**第三步：部署 Skill**

- 若 YouBuddy 提供命令行、配置目录或其他可自动化的入口，优先用它把 `skills/` 下的三个策略目录部署进去，并核对部署结果。
- 若没有可靠的自动入口，就明确告诉用户：打开 YouBuddy → 进入「Skill / 策略管理」→ 选择「导入本地 Skill」，依次指向以下三个目录：

  - `skills/baima_offense_defense_opt`
  - `skills/cs300_opt_1`
  - `skills/cs300_opt_2`

  等用户确认导入成功后，再进行下一步。

**第四步：运行回测**

引导用户在 YouBuddy 中选中已安装的策略并运行。回测需通过 YouBuddy 宿主完成，产物包括净值曲线、逐笔成交、调仓记录与策略解读报告。不要在独立 Python 环境里运行 `backtest.py`——它依赖宿主提供的数据与工具 bundle。

**兜底联系方式**：如果安装或部署过程中失败（例如 YouBuddy 无法安装、Skill 导入不成功），告诉用户可以联系微信 `huangzh0605` 获取帮助。

## 反馈与更新

欢迎通过 [Issues](https://github.com/luoy38067/YouBuddy-quant-skills/issues) 反馈使用问题与策略需求；更多类型的策略（ETF 轮动、全天候配置、红利杠铃等）将持续上架。

## License

本项目基于 [MIT License](LICENSE) 开源。
