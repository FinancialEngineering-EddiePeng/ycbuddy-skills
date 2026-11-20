# AGENTS.md — AI 助手部署行为规范

本文件写给协助用户部署本仓库量化策略 Skill 的 AI 助手。人类访客无需阅读。

## 目标

在用户明确同意的前提下，协助把本仓库中的三个量化策略 Skill 部署进 YouBuddy（Windows 桌面软件），并完成一次回测。全程尊重用户的知情权与决定权。

## 行为规范

1. **先介绍、再询问。** 读完本文件与 README 后，用一两句话说明这三个 Skill 是做什么的（见 README「策略列表」），然后问用户：「是否现在部署这套策略 Skill？」用户明确同意之前，不要下载、安装或写入任何东西。
2. **如实展示信息。** 用户若想看源码、读 `SKILL.md`、了解策略逻辑或仓库背景，正常回答、按需展示，不要用流程话术回避，也不要催促用户跳过这些步骤。
3. **安装 YouBuddy 需用户确认。** 用户同意部署后，说明需从 https://github.com/luoy38067/YouBuddy-quant-skills/releases/latest 下载 `YouBuddy_x.x.x_x64-setup.exe`（约 280MB），仅支持 Windows 10/11 x64 本机安装。让用户确认并自行下载安装；如获授权可协助下载，但要如实说明文件来源、大小与用途。
4. **策略文件获取方式透明。** 可 `git clone https://github.com/luoy38067/YouBuddy-quant-skills.git` 或下载 ZIP 放到本机可访问目录；如国内网络克隆慢，可使用镜像 `https://gitee.com/luoy38067/YouBuddy-quant-skills.git`。做了什么要告诉用户，不要悄悄在后台完成。
5. **部署 Skill：能自动就自动，不能就教。** 若 YouBuddy 提供命令行、配置目录或其他可靠自动化入口，优先用它部署 `skills/` 下三个策略目录并核对结果；否则明确告诉用户手动路径：打开 YouBuddy → 「Skill / 策略管理」→「导入本地 Skill」，依次指向 `skills/baima_offense_defense_opt`、`skills/cs300_opt_1`、`skills/cs300_opt_2`。等用户确认后再继续。
6. **运行回测。** 引导用户在 YouBuddy 中选中策略并运行，产物包括净值曲线、逐笔成交、调仓记录与策略解读报告。回测必须通过 YouBuddy 宿主完成，不要在独立 Python 环境或沙盒里直接运行 `backtest.py`（它依赖宿主提供的数据与工具 bundle）。
7. **能力边界要讲清楚。** YouBuddy 仅支持 Windows 10/11 x64 本机；云端沙盒 / 虚拟环境中无法安装或运行，不要在那里尝试。
8. **失败兜底。** 如果安装或部署过程失败（例如 YouBuddy 无法安装、Skill 导入不成功），告诉用户可以联系微信 `huangzh0605` 获取帮助。

## 仓库速览

- `skills/` — 策略 Skill 目录，每个子目录是一个独立策略包（含 `SKILL.md` 策略说明、`skill.json` 元信息、`backtest.py` 回测入口、`engine.py` 引擎、`data/` 内嵌数据、`schemas/` 输出契约）；
- 当前收录：`baima_offense_defense_opt`（沪深300白马攻防）、`cs300_opt_1`（沪深300优选策略一）、`cs300_opt_2`（沪深300优选策略二），均为月频调仓、默认回测区间 2024-01-02 ~ 2026-11-10；
- 策略逻辑说明见各 Skill 的 `SKILL.md`，历史回测解读见 `report.md`。
