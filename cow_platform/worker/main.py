from __future__ import annotations

import argparse
import time

from common.log import logger
from cow_platform.services.job_service import JobService


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the CowAgent platform worker.")
    parser.add_argument("--once", action="store_true", help="只处理一个任务后退出。")
    parser.add_argument("--job-type", default="", help="只消费指定类型的任务。")
    parser.add_argument("--poll-interval", default=1.0, type=float, help="空闲轮询间隔（秒）。")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    service = JobService()

    if args.once:
        result = service.run_once(job_type=args.job_type)
        if result is None:
            logger.info("[PlatformWorker] No pending job found")
        else:
            logger.info(f"[PlatformWorker] Processed job: {result['job_id']} -> {result['status']}")
        return

    logger.info("[PlatformWorker] Worker started")
    while True:
        result = service.run_once(job_type=args.job_type)
        if result is None:
            time.sleep(max(0.1, float(args.poll_interval)))
            continue
        logger.info(f"[PlatformWorker] Processed job: {result['job_id']} -> {result['status']}")


if __name__ == "__main__":
    main()
