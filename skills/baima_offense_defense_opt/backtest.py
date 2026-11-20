"""沪深300白马攻防策略（baima_offense_defense_opt）回测入口。

Usage:
    python backtest.py <run_manifest.json>

策略算法、调仓规则与撮合口径详见 SKILL.md；内嵌数据文件位于 data/
（34 期 调仓目标持仓表、调仓日目标股涨跌停价）。

数据口径：交易日历/个股行情/基准由宿主运行时提供（inputs/）；个股
行情为前复权口径（与原始策略撮合/估值口径一致）。
"""

from __future__ import annotations

import csv
import json
import math
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine import Inputs, _write_csv, compute_metrics, write_json  # noqa: E402

# 与源脚本常量一致（写死，不暴露参数）。
INITIAL_CASH = 1_000_000.0
COMMISSION = 0.0003   # 佣金，双边
TAX = 0.0005          # 印花税，仅卖出
DATA_DIR = Path(__file__).resolve().parent / "data"


# ──────────────────────────────────────────────────────────────
# 内嵌数据：调仓目标持仓表 / 涨跌停价
# ──────────────────────────────────────────────────────────────

class EmbeddedModel:
    """data/ 下内嵌文件的只读视图（数据库一次性导出，禁止运行时改写）。"""

    def __init__(self, data_dir: Path):
        # rdate -> [ticker, ...]（保持文件顺序，即源脚本目标顺序）
        self.targets: Dict[str, List[str]] = {}
        with (data_dir / "targets.csv").open("r", encoding="utf-8-sig", newline="") as f:
            rows: List[Tuple[str, int, str]] = []
            for row in csv.DictReader(f):
                rows.append((row["rdate"].strip(), int(row["order"]),
                             row["ticker"].strip()))
            rows.sort(key=lambda r: (r[0], r[1]))
            for rdate, _, ticker in rows:
                self.targets.setdefault(rdate, []).append(ticker)

        # 涨跌停价（前复权口径，仅覆盖调仓日目标股）：
        # (date, ticker) -> (up_limit, down_limit)
        self.limits: Dict[Tuple[str, str], Tuple[float, float]] = {}
        limits_path = data_dir / "limits.csv"
        if limits_path.exists():
            with limits_path.open("r", encoding="utf-8-sig", newline="") as f:
                for row in csv.DictReader(f):
                    self.limits[(row["date"].strip(), row["ticker"].strip())] = (
                        float(row["up_limit"]), float(row["down_limit"]))


def _ddb_round(x: float) -> int:
    """与源脚本整百取整语义一致的四舍五入。"""
    return math.floor(x + 0.5)


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
        targets = self.model.targets.get(date) or []
        if not targets:
            return
        target_set = set(targets)

        def px(ticker: str) -> Optional[float]:
            # 仅当日在册行情可成交（msg.keys() 语义），停牌缺失不得伪造。
            price = self.inputs.close(ticker, date)
            return price if price is not None and price > 0 else None

        self.event_seq += 1
        event_id = f"{date}-scheduled-{self.event_seq:04d}"
        signal_date = self.prev_trading_day(date) or date
        gross = self.cash + sum(
            q * pxv for t, q in self.shares.items() if (pxv := px(t)) is not None)

        # 阶段1：清仓不在目标中的持仓（有当日行情者）。
        for ticker in sorted(self.shares):
            if ticker in target_set:
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
                "trigger_reason": "monthly_rebalance", "ticker": ticker,
                "old_weight": f"{notional / max(gross, 1e-12):.6f}",
                "target_weight": "0.000000", "actual_weight": "0.000000"})

        # 仓位基数：现金 + 非目标持仓按收盘估值（卖出资金当日回笼）。
        total = self.cash + sum(
            q * pxv for t, q in self.shares.items()
            if t not in target_set and (pxv := px(t)) is not None)
        if not math.isfinite(total) or total <= 0:
            return
        target_value = total / len(targets)

        # 阶段2：按目标顺序整百股买入（全新目标股数，持仓自然累加）。
        for ticker in targets:
            price = px(ticker)
            if price is None:
                continue
            qty = _ddb_round(target_value / (price * (1 + COMMISSION)) / 100) * 100
            if qty <= 0:
                continue
            limit = self.model.limits.get((date, ticker))
            if limit is not None and price >= limit[0] - 1e-9:
                # 收盘价触涨停的买单不成交（无现金、无持仓变动），跳过。
                continue
            notional = qty * price
            fee = notional * COMMISSION
            # 资金不足整单拒单（金额+佣金 > 现金即拒）。
            if notional + fee > self.cash:
                continue
            self.cash -= notional + fee
            ex_qty = self.shares.get(ticker, 0.0)
            self.shares[ticker] = ex_qty + qty
            self.trade_rows.append({
                "date": date, "ticker": ticker, "side": "buy",
                "quantity": f"{qty:.4f}", "price": f"{price:.6f}", "fee": f"{fee:.8f}"})
            new_value = self.shares[ticker] * price
            self.record_rows.append({
                "event_id": event_id, "signal_date": signal_date,
                "execution_date": date, "trigger_type": "scheduled",
                "trigger_reason": "monthly_rebalance", "ticker": ticker,
                "old_weight": f"{ex_qty * price / total:.6f}",
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
            if date in self.model.targets:
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
            "id": "baima_offense_defense_opt",
            "name": "沪深300白马攻防策略（市场状态适应选股 · 月度Top5等权）",
            "target_count": 5,
            "initial_cash": INITIAL_CASH,
            "commission": COMMISSION,
            "tax": TAX,
            "embedded_data": ["data/targets.csv", "data/limits.csv"],
            "matching": "执行日收盘价市价撮合（非目标持仓先清仓、卖出资金当日回笼；"
                        "目标股按整百股买入；资金不足整单跳过；收盘价触涨停的买单与"
                        "触跌停的卖单不成交），与原始策略一致",
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
