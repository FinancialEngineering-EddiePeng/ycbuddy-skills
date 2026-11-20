"""沪深300优选策略二（CS300W_C00221_EQ）回测入口。

Usage:
    python backtest.py <run_manifest.json>

策略算法、调仓规则与撮合口径详见 SKILL.md；内嵌数据文件位于 data/
（4 因子面板、38 期 等权 EQ权重表、成分区间、涨跌停价）。

数据口径：交易日历/个股行情/基准由宿主运行时提供（inputs/）；个股
行情必须为不复权（adjustment=none）口径，方能与官方净值对齐。
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import Inputs, _write_csv, compute_metrics, write_json  # noqa: E402

# 与源脚本常量一致（写死，不暴露参数）。
INITIAL_CASH = 1_000_000.0
TARGET_COUNT = 10
COMMISSION = 0.0003   # 佣金，双边
TAX = 0.0005          # 印花税，仅卖出
DATA_DIR = Path(__file__).resolve().parent / "data"


# ──────────────────────────────────────────────────────────────
# 内嵌数据：因子面板 / IV 权重表 / 成分区间
# ──────────────────────────────────────────────────────────────

class EmbeddedModel:
    """data/ 下三个内嵌文件的只读视图（DDB 一次性导出，禁止运行时改写）。"""

    def __init__(self, data_dir: Path):
        # (rdate, fidx) -> {ticker: (val, dirn)}
        self.factors: Dict[Tuple[str, str], Dict[str, Tuple[float, int]]] = {}
        with (data_dir / "factors.csv").open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                key = (row["rdate"].strip(), row["fidx"].strip())
                self.factors.setdefault(key, {})[row["TICKER_SYMBOL"].strip()] = (
                    float(row["val"]), int(row["dirn"]))

        # rdate -> {fidx: w}（保持文件顺序，即源脚本 [1,2,4,8] 顺序）
        self.wall: Dict[str, Dict[str, float]] = {}
        with (data_dir / "wall.csv").open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                self.wall.setdefault(row["rdate"].strip(), {})[row["fidx"].strip()] = \
                    float(row["w"])

        # 成分在册区间：intoDate <= d 且 (outDate 为空 或 d < outDate)
        self.cons: List[Tuple[str, str, str]] = []
        with (data_dir / "constituents.csv").open("r", encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                self.cons.append((row["symbol"].strip(),
                                  row["intoDate"].strip(), row["outDate"].strip()))

        # 涨跌停价（交易所 mkt_limit 真实值，仅覆盖权重表调仓日）：
        # (date, ticker) -> (up_limit, down_limit)
        self.limits: Dict[Tuple[str, str], Tuple[float, float]] = {}
        limits_path = data_dir / "limits.csv"
        if limits_path.exists():
            with limits_path.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    self.limits[(row["date"].strip(), row["ticker"].strip())] = (
                        float(row["up_limit"]), float(row["down_limit"]))

    def cons_at(self, date: str) -> List[str]:
        active = [sym for sym, into, out in self.cons
                  if into <= date and (not out or date < out)]
        return sorted(active)

    def score_at(self, rdate: str) -> List[Tuple[str, float]]:
        """与源脚本打分管道逐行一致；返回 (ticker, score) 按 score 降序、代码升序。"""
        per: Dict[str, float] = defaultdict(float)
        nz: Dict[str, int] = defaultdict(int)
        for fidx, weight in self.wall.get(rdate, {}).items():
            panel = self.factors.get((rdate, fidx))
            if not panel:
                continue
            vals = [v for v, _ in panel.values()]
            mu = sum(vals) / len(vals)
            sd = math.sqrt(sum((v - mu) ** 2 for v in vals) / (len(vals) - 1))
            if sd <= 1e-12:
                # 源脚本该因子组被过滤，left join miss 的行 z=0 但计入覆盖数。
                for ticker in panel:
                    nz[ticker] += 1
                continue
            for ticker, (val, dirn) in panel.items():
                z = dirn * min(max((val - mu) / sd, -3.0), 3.0)
                if not math.isfinite(z):
                    continue
                per[ticker] += weight * z
                nz[ticker] += 1
        kk = len(self.wall.get(rdate, {}))
        scored = [(t, s) for t, s in per.items() if nz[t] == kk]
        scored.sort(key=lambda kv: (-kv[1], kv[0]))
        return scored


# ──────────────────────────────────────────────────────────────
# 模拟主流程（源脚本 onBar 语义 + 引擎产物结构）
# ──────────────────────────────────────────────────────────────

class Backtest:
    def __init__(self, manifest_path: str):
        manifest_path = Path(manifest_path)
        self.run_dir = manifest_path.parent
        with manifest_path.open("r", encoding="utf-8-sig") as handle:
            self.manifest = json.load(handle)
        self.run_id = str(self.manifest.get("run_id") or "")
        params = dict(((self.manifest.get("parameters") or {}).get("structured") or {}))
        self.start = str(params.get("start") or "")
        requested_end = str(params.get("end") or "")
        data_context = dict(self.manifest.get("data_context") or {})
        effective_end = str(data_context.get("effective_end") or
                            data_context.get("data_cutoff") or requested_end)
        self.end = min(requested_end, effective_end) if effective_end else requested_end
        self.inputs = Inputs(self.run_dir)
        self.calendar_index = {d: i for i, d in enumerate(self.inputs.calendar)}
        self.dates = [d for d in self.inputs.calendar if self.start <= d <= self.end]
        self.model = EmbeddedModel(DATA_DIR)
        self.staging = self.run_dir / "staging"
        self.staging.mkdir(parents=True, exist_ok=True)
        # 组合状态
        self.cash = INITIAL_CASH
        self.shares: Dict[str, float] = {}
        # 产物
        self.nav_rows: List[Dict[str, object]] = []
        self.trade_rows: List[Dict[str, object]] = []
        self.record_rows: List[Dict[str, object]] = []
        self.event_seq = 0

    # ── 调仓（源脚本 onBar）──

    def rebalance(self, date: str) -> None:
        cons = set(self.model.cons_at(date))
        if not cons:
            return
        scored = [(t, s) for t, s in self.model.score_at(date) if t in cons]
        if not scored:
            return
        top = [t for t, _ in scored[:TARGET_COUNT]]
        top_set = set(top)

        def px(ticker: str) -> Optional[float]:
            # 仅当日在册行情可成交（msg.keys() 语义），停牌缺失不得伪造。
            price = self.inputs.close(ticker, date)
            return price if price is not None and price > 0 else None

        # 先算持仓市值（卖出之前，仅有当日行情者计入）。
        pos_mv = sum(q * px(t) for t, q in self.shares.items() if px(t) is not None)
        total = self.cash + pos_mv
        if not math.isfinite(total) or total <= 0:
            return
        target_value = total / len(top)
        self.event_seq += 1
        event_id = f"{date}-scheduled-{self.event_seq:04d}"
        signal_date = self.prev_trading_day(date) or date

        # 阶段1：清仓不在名单内的持仓（有当日行情者）。
        for ticker in sorted(self.shares):
            if ticker in top_set:
                continue
            price = px(ticker)
            qty = self.shares.get(ticker, 0.0)
            if price is None or qty <= 0:
                continue
            # 收盘价触跌停的卖单不成交（无回款、无持仓变动），跳过。
            limit = self.model.limits.get((date, ticker))
            if limit is not None and price <= limit[1] + 1e-9:
                continue
            notional = qty * price
            fee = notional * (COMMISSION + TAX)
            self.cash += notional - fee
            del self.shares[ticker]
            self.trade_rows.append({
                "date": date, "ticker": ticker, "side": "sell",
                "quantity": f"{qty:.4f}", "price": f"{price:.6f}", "fee": f"{fee:.8f}"})
            self.record_rows.append({
                "event_id": event_id, "signal_date": signal_date,
                "execution_date": date, "trigger_type": "scheduled",
                "trigger_reason": "monthly_iv_weight_rebalance", "ticker": ticker,
                "old_weight": f"{notional / total:.6f}",
                "target_weight": "0.000000", "actual_weight": "0.000000"})

        # 阶段2：按名单顺序整百股增减到目标市值。
        # 四舍五入取整（非截断语义）。
        for ticker in top:
            price = px(ticker)
            if price is None:
                continue
            ex_qty = self.shares.get(ticker, 0.0)
            ex_value = ex_qty * price
            gap = abs(target_value - ex_value) / price / 100
            whole = math.floor(gap)
            if gap - whole >= 0.5:
                whole += 1
            diff_qty = whole * 100
            if diff_qty <= 0:
                continue
            limit = self.model.limits.get((date, ticker))
            limit_up = limit[0] if limit else None
            limit_down = limit[1] if limit else None
            if target_value > ex_value:
                if limit_up is not None and price >= limit_up - 1e-9:
                    # 收盘价触涨停的买单不成交（无现金、无持仓变动），跳过。
                    continue
                notional = diff_qty * price
                fee = notional * COMMISSION
                # 资金不足整单拒单（金额+佣金 > 现金即拒）。
                if notional + fee > self.cash:
                    continue
                self.cash -= notional + fee
                self.shares[ticker] = ex_qty + diff_qty
                side = "buy"
                qty = diff_qty
            else:
                if limit_down is not None and price <= limit_down + 1e-9:
                    # 收盘价触跌停的卖单不成交（无现金、无持仓变动），跳过。
                    continue
                sq = min(diff_qty, ex_qty)
                notional = sq * price
                fee = notional * (COMMISSION + TAX)
                self.cash += notional - fee
                self.shares[ticker] = ex_qty - sq
                side = "sell"
                qty = sq
            if self.shares.get(ticker, 0.0) <= 0:
                self.shares.pop(ticker, None)
            self.trade_rows.append({
                "date": date, "ticker": ticker, "side": side,
                "quantity": f"{(diff_qty if side == 'buy' else sq):.4f}",
                "price": f"{price:.6f}", "fee": f"{fee:.8f}"})
            new_value = self.shares.get(ticker, 0.0) * price
            self.record_rows.append({
                "event_id": event_id, "signal_date": signal_date,
                "execution_date": date, "trigger_type": "scheduled",
                "trigger_reason": "monthly_iv_weight_rebalance", "ticker": ticker,
                "old_weight": f"{ex_value / total:.6f}",
                "target_weight": f"{target_value / total:.6f}",
                "actual_weight": f"{new_value / total:.6f}"})

    def prev_trading_day(self, date: str) -> Optional[str]:
        index = self.calendar_index.get(date)
        if index is None or index == 0:
            return None
        return self.inputs.calendar[index - 1]

    # ── 逐日净值（收盘价盯市，停牌用最近可得收盘）──

    def mark(self, date: str) -> float:
        value = self.cash
        for ticker, qty in self.shares.items():
            price = self.inputs.last_close_at_or_before(ticker, date)
            if price is not None:
                value += qty * price
        return value

    def run(self) -> Dict[str, object]:
        nav_values: List[float] = []
        for date in self.dates:
            if date in self.model.wall:
                self.rebalance(date)
            nav_values.append(self.mark(date))
        return self._write_outputs(nav_values)

    # ── 产物写出（与宿主 verifier 对齐的产物结构）──

    def _write_outputs(self, nav_values: List[float]) -> Dict[str, object]:
        nav0 = nav_values[0] if nav_values and nav_values[0] > 0 else 1.0
        prev: Optional[float] = None
        for date, value in zip(self.dates, nav_values):
            daily_return = 0.0 if not prev else value / prev - 1.0
            prev = value
            self.nav_rows.append({
                "date": date,
                "nav_value": value / nav0,
                "strategy_nav": f"{value / nav0:.12f}",
                "daily_return": f"{daily_return:.12f}"})
        metrics = compute_metrics(self, nav_values)  # 只用比例，归一化无影响
        write_json(self.staging / "metrics.json", {"contract": "strategy.metrics.v1", **metrics})
        _write_csv(self.staging / "daily_nav.csv",
                   ["date", "strategy_nav", "daily_return"], self.nav_rows)
        self._write_benchmark_nav()
        self._write_holdings(nav_values)
        _write_csv(self.staging / "trades.csv",
                   ["date", "ticker", "side", "quantity", "price", "fee"], self.trade_rows)
        _write_csv(self.staging / "rebalance_records.csv",
                   ["event_id", "signal_date", "execution_date", "trigger_type",
                    "trigger_reason", "ticker", "old_weight", "target_weight",
                    "actual_weight"], self.record_rows)
        summary = {
            "strategy": self.describe(),
            "start": metrics.get("start"),
            "end": metrics.get("end"),
            "total_return": metrics.get("total_return"),
            "annualized_return": metrics.get("annualized_return"),
            "max_drawdown": metrics.get("max_drawdown"),
            "sharpe": metrics.get("sharpe"),
            "benchmark_total_return": metrics.get("benchmark_total_return"),
            "trading_days": metrics.get("trading_days"),
            "trade_count": len(self.trade_rows),
            "rebalance_events": len({row["event_id"] for row in self.record_rows}),
            "fee_total": metrics.get("total_fee"),
        }
        result = {
            "contract": "strategy_result.v1",
            "status": "computed",
            "run_id": self.run_id,
            "summary": summary,
            "output_files": ["metrics.json", "daily_nav.csv", "benchmark_nav.csv",
                             "latest_holdings.csv", "trades.csv", "rebalance_records.csv"],
        }
        write_json(self.staging / "strategy_result.json", result)
        return result

    def _write_benchmark_nav(self) -> None:
        rows: List[Dict[str, object]] = []
        base: Optional[float] = None
        for row in self.nav_rows:
            close = self.inputs.benchmark_close_at_or_before(str(row["date"]))
            if close is not None and base is None:
                base = close
            rows.append({"date": row["date"],
                         "benchmark_nav": f"{close / base:.12f}"
                         if close is not None and base is not None and base > 0 else ""})
        _write_csv(self.staging / "benchmark_nav.csv", ["date", "benchmark_nav"], rows)

    def _write_holdings(self, nav_values: List[float]) -> None:
        date = self.dates[-1] if self.dates else ""
        total = nav_values[-1] / (nav_values[0] or 1.0) if nav_values else 0.0
        rows: List[Dict[str, object]] = []
        if total > 0:
            marked = self.mark(date)
            for ticker in sorted(self.shares):
                price = self.inputs.last_close_at_or_before(ticker, date)
                if price is not None:
                    value = self.shares[ticker] * price
                    rows.append({"ticker": ticker,
                                 "weight": f"{value / marked:.6f}", "as_of": date})
        _write_csv(self.staging / "latest_holdings.csv", ["ticker", "weight", "as_of"], rows)

    def describe(self) -> Dict[str, object]:
        return {
            "id": "cs300_opt_2",
            "name": "沪深300优选策略二（CS300W_C00221_EQ，4因子等权加权月度Top10）",
            "factors": {"1": "F1", "2": "F2", "3": "F3", "4": "F4"},
            "weight_scheme": "等权（EQ），内嵌 wall 表",
            "target_count": TARGET_COUNT,
            "initial_cash": INITIAL_CASH,
            "commission": COMMISSION,
            "tax": TAX,
            "embedded_data": ["data/factors.csv", "data/wall.csv",
                              "data/constituents.csv", "data/limits.csv"],
            "matching": "执行日收盘价整百股撮合（四舍五入；资金不足整单拒单；"
                        "收盘价触涨停的买单与触跌停的卖单不成交），与原始策略一致",
        }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: backtest.py <run_manifest.json>", file=sys.stderr)
        return 2
    backtest = Backtest(sys.argv[1])
    result = backtest.run()
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
