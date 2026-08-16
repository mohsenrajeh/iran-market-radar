"""200-Cycle Stress and Invariant Verification Suite for Iran Market Radar."""
import sys
import time
import json
import random
import urllib.request
import urllib.error
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_BASE = "http://127.0.0.1:8892/api/v1"
WEB_BASE = "http://127.0.0.1:3892"

SYMBOLS = ["فولاد", "فملی", "خودرو", "خساپا", "وبملت", "شپنا", "شبندر", "شستا", "کچاد", "فارس"]
HORIZONS = ["3d", "5d", "10d"]
GRADES = ["A+", "A", "B", "C"]


def http_get(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "StressTester200/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def http_post(url: str, payload: dict):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "StressTester200/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def run_200_stress_tests():
    print("================================================================================")
    print("🚀 Starting 200-Cycle Comprehensive Stress & Invariant Verification Suite")
    print(f"API Target: {API_BASE} | Web Target: {WEB_BASE}")
    print("================================================================================")

    passed = 0
    failed = 0
    errors = []
    latencies = []

    start_all = time.time()

    for cycle in range(1, 201):
        t0 = time.time()
        try:
            # Test 1: Health & Overview
            s_health, d_health = http_get(f"{API_BASE}/health")
            assert s_health == 200 and d_health.get("status") == "ok", f"Cycle {cycle}: Health check failed"

            s_over, d_over = http_get(f"{API_BASE}/market/overview")
            assert s_over == 200 and "market_regime" in d_over, f"Cycle {cycle}: Overview check failed"

            # Test 2: Opportunities & Invariant Range Checks
            s_opps, d_opps = http_get(f"{API_BASE}/opportunities?actionable_only=false")
            assert s_opps == 200 and isinstance(d_opps, list), f"Cycle {cycle}: Opportunities failed"
            for opp in d_opps:
                assert 0.0 <= opp["p_profit"] <= 1.0, f"Cycle {cycle}: p_profit out of bounds: {opp['p_profit']}"
                assert 0.0 <= opp["confidence"] <= 100.0, f"Cycle {cycle}: confidence out of bounds: {opp['confidence']}"
                assert 0.0 <= opp["signal_strength"] <= 100.0, f"Cycle {cycle}: signal_strength out of bounds"
                assert 0.0 <= opp["opportunity_score"] <= 100.0, f"Cycle {cycle}: score out of bounds"
                assert "entry_zone" in opp and opp["entry_zone"]["low"] <= opp["entry_zone"]["high"]

            # Test 3: Sectors Matrix
            s_sec, d_sec = http_get(f"{API_BASE}/market/sectors")
            assert s_sec == 200 and len(d_sec) > 0, f"Cycle {cycle}: Sectors failed"

            # Test 4: Random Symbol Candlestick & Indicator Check
            sym = random.choice(SYMBOLS)
            s_chart, d_chart = http_get(f"{API_BASE}/symbols/{urllib.parse.quote(sym)}/chart?limit=60")
            assert s_chart == 200 and len(d_chart.get("bars", [])) > 0, f"Cycle {cycle}: Chart failed for {sym}"

            # Test 5: Strategies Catalog
            s_strat, d_strat = http_get(f"{API_BASE}/strategies")
            assert s_strat == 200 and len(d_strat) >= 5, f"Cycle {cycle}: Strategies failed"

            # Test 6: Paper Trading Lifecycle
            s_port, d_port = http_get(f"{API_BASE}/paper/portfolio")
            assert s_port == 200 and d_port.get("cash") >= 0, f"Cycle {cycle}: Portfolio failed"

            # Order from Signal (Every 10 cycles, place a paper order if opportunities exist)
            if cycle % 10 == 0 and len(d_opps) > 0:
                target_sig = random.choice(d_opps)
                try:
                    s_ord, d_ord = http_post(f"{API_BASE}/paper/orders/from-signal", {"signal_id": target_sig["id"]})
                    assert s_ord == 200 and d_ord.get("success") is True, f"Cycle {cycle}: Paper order placement failed"
                except urllib.error.HTTPError as e:
                    # In case of risk limit reached (e.g. max positions or single stock limit)
                    err_body = e.read().decode("utf-8")
                    assert "limit" in err_body or "ریسک" in err_body or e.code == 400, f"Unexpected error: {err_body}"

            # Test 7: Kill-Switch Toggle & Restore (Cycle 50, 100, 150)
            if cycle in [50, 100, 150]:
                s_ks1, d_ks1 = http_post(f"{API_BASE}/paper/kill-switch", {"active": True})
                assert s_ks1 == 200 and d_ks1.get("kill_switch_active") is True, "Kill switch activate failed"
                s_ks2, d_ks2 = http_post(f"{API_BASE}/paper/kill-switch", {"active": False})
                assert s_ks2 == 200 and d_ks2.get("kill_switch_active") is False, "Kill switch deactivate failed"

            # Test 8: Backtest Simulation (Every 25 cycles)
            if cycle % 25 == 0:
                h = random.choice(HORIZONS)
                cap = random.choice([500_000_000, 1_000_000_000, 2_000_000_000])
                s_bt, d_bt = http_post(
                    f"{API_BASE}/backtests",
                    {
                        "name": f"Stress Test {cycle}",
                        "strategy_key": "cross_sectional_momentum",
                        "horizon": h,
                        "initial_capital": float(cap),
                    },
                )
                assert s_bt == 200 and "sharpe_ratio" in d_bt, f"Cycle {cycle}: Backtest failed"

            # Test 9: Web Frontend Rendering (Every 5 cycles)
            if cycle % 5 == 0:
                with urllib.request.urlopen(WEB_BASE, timeout=10) as resp_web:
                    assert resp_web.status == 200, f"Cycle {cycle}: Web frontend failed"

            latency_ms = (time.time() - t0) * 1000
            latencies.append(latency_ms)
            passed += 1

            if cycle % 20 == 0 or cycle == 200 or cycle == 1:
                print(f"  [Cycle {cycle:03d}/200] ✅ PASSED | Latency: {latency_ms:.1f}ms | Avg: {sum(latencies)/len(latencies):.1f}ms")

        except Exception as ex:
            failed += 1
            errors.append(f"Cycle {cycle}: {str(ex)}")
            print(f"  [Cycle {cycle:03d}/200] ❌ FAILED: {ex}")

    total_time = time.time() - start_all
    avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0.0

    print("================================================================================")
    print("📊 200-Cycle Test Execution Summary:")
    print(f"  Total Cycles: 200")
    print(f"  Passed: {passed} ({(passed/200)*100:.1f}%)")
    print(f"  Failed: {failed}")
    print(f"  Total Elapsed Time: {total_time:.2f}s")
    print(f"  Average Cycle Latency: {avg_latency:.1f}ms")
    print(f"  P95 Latency: {p95_latency:.1f}ms")
    print("================================================================================")

    if failed > 0:
        print("\n❌ Errors encountered:")
        for err in errors[:10]:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("\n🎉 ALL 200 TEST CYCLES PASSED WITH ZERO DEFECTS!")
        sys.exit(0)


if __name__ == "__main__":
    run_200_stress_tests()
