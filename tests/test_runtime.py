from quant.runtime import adapt_tick


def test_old_or_future_qualification_cache_cannot_enable_paper_orders():
    tick = {"received_ms": 100_000, "quotes": {},
            "health": {"live_session": True, "healthy": True,
                       "qualification": {"qualified_72h": True, "asof_ms": 50_000}}}
    health, quotes = adapt_tick(tick)
    assert not health["qualified_72h"] and quotes == []
    tick["health"]["qualification"]["asof_ms"] = 100_001
    assert not adapt_tick(tick)[0]["qualified_72h"]
    tick["health"]["qualification"]["asof_ms"] = 99_000
    assert adapt_tick(tick)[0]["qualified_72h"]
