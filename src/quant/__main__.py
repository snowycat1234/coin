import argparse
import json

from .disk import check


def main():
    from .resources import status as resource_status

    resource_status()
    parser = argparse.ArgumentParser(description="D-hosted Binance quant research")
    sub = parser.add_subparsers(dest="command", required=True)
    guard = sub.add_parser("disk")
    guard.add_argument("--reserve", type=int, default=0)
    download = sub.add_parser("download")
    download.add_argument("--start", default="2022-01")
    download.add_argument("--end", default="2026-08")
    download.add_argument("--sample", action="store_true")
    download.add_argument("--workers", type=int, default=4)
    sub.add_parser("ingest")
    sub.add_parser("freeze")
    sub.add_parser("instruments")
    sub.add_parser("baselines")
    research = sub.add_parser("research")
    research.add_argument("--resume-reason")
    collect = sub.add_parser("collect")
    collect.add_argument("--seconds", type=float)
    sub.add_parser("collector-status")
    sub.add_parser("live-status")
    sub.add_parser("forward-report")
    sub.add_parser("resources")
    args = parser.parse_args()
    if args.command == "disk":
        print(json.dumps(check(args.reserve), indent=2))
    elif args.command == "resources":
        print(json.dumps(resource_status(), indent=2))
    elif args.command == "download":
        from .data import download_months, month_range

        months = ["2022-01", "2025-01"] if args.sample else month_range(args.start, args.end)
        result = download_months(months, args.workers)
        print(json.dumps({"archives": len(result), "compressed_bytes":
                          sum(item["bytes"] for item in result)}, indent=2))
    elif args.command == "ingest":
        from .data import ingest_all

        ingest_all()
    elif args.command == "freeze":
        from .data import freeze_dataset

        print(json.dumps(freeze_dataset(), indent=2))
    elif args.command == "instruments":
        from .data import fetch_instruments

        print(json.dumps(fetch_instruments(), indent=2))
    elif args.command == "baselines":
        from .operations import run_baselines

        run_baselines()
    elif args.command == "research":
        from .operations import run_registered_research

        result = run_registered_research(args.resume_reason)
        print(json.dumps({"status": result["status"],
                          "selected_interval": result["selected_interval"]}, indent=2))
    elif args.command == "collect":
        import asyncio

        from .collector import collect

        asyncio.run(collect(run_seconds=args.seconds))
    elif args.command == "collector-status":
        from .collector import status

        print(json.dumps(status(), indent=2))
    elif args.command == "live-status":
        from .runtime import live_status

        print(json.dumps(live_status(), ensure_ascii=False, indent=2))
    elif args.command == "forward-report":
        from .runtime import forward_report

        print(json.dumps(forward_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

