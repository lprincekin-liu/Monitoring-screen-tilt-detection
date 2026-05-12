from __future__ import annotations

import argparse
import base64
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib import request
from urllib.error import HTTPError, URLError


def post_body(url: str, body: bytes, content_type: str, timeout: float) -> tuple[bool, float, str]:
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": content_type},
        method="POST",
    )
    start = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            resp.read()
            return 200 <= resp.status < 300, (time.perf_counter() - start) * 1000, ""
    except HTTPError as exc:
        return False, (time.perf_counter() - start) * 1000, f"HTTP {exc.code}"
    except URLError as exc:
        return False, (time.perf_counter() - start) * 1000, str(exc.reason)


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    values = sorted(values)
    index = min(len(values) - 1, int(round((pct / 100) * (len(values) - 1))))
    return values[index]


def main() -> None:
    parser = argparse.ArgumentParser(description="Local pressure test for tilt API")
    parser.add_argument("--image", required=True, help="Path to local test image")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8881/detect_tilt",
        help="Detect API URL",
    )
    parser.add_argument("--requests", type=int, default=100)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=30)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Send JSON body instead of raw base64 text",
    )
    args = parser.parse_args()

    image_base64 = base64.b64encode(Path(args.image).read_bytes()).decode("utf-8")
    if args.json:
        body = json.dumps({"image_base64": image_base64}).encode("utf-8")
        content_type = "application/json"
    else:
        body = image_base64.encode("utf-8")
        content_type = "text/plain"

    started = time.perf_counter()
    latencies: list[float] = []
    errors: list[str] = []
    ok_count = 0

    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [
            pool.submit(post_body, args.url, body, content_type, args.timeout)
            for _ in range(args.requests)
        ]
        for future in as_completed(futures):
            ok, latency_ms, error = future.result()
            latencies.append(latency_ms)
            if ok:
                ok_count += 1
            else:
                errors.append(error)

    total_seconds = time.perf_counter() - started
    failed = args.requests - ok_count
    result = {
        "url": args.url,
        "requests": args.requests,
        "concurrency": args.concurrency,
        "success": ok_count,
        "failed": failed,
        "qps": round(args.requests / total_seconds, 2) if total_seconds else 0,
        "latency_ms": {
            "avg": round(statistics.mean(latencies), 2) if latencies else 0,
            "min": round(min(latencies), 2) if latencies else 0,
            "max": round(max(latencies), 2) if latencies else 0,
            "p50": round(percentile(latencies, 50), 2),
            "p90": round(percentile(latencies, 90), 2),
            "p95": round(percentile(latencies, 95), 2),
            "p99": round(percentile(latencies, 99), 2),
        },
        "sample_errors": errors[:5],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
