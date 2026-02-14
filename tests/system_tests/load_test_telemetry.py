"""System test / local load script for the Telemetry API (standard-library only).

Features:
- Performs optional pre-run cleanup of previous `LOAD-` records (use `--no-cleanup` to skip).
- Sends `--total` POST requests (randomized payloads; ~`--error-rate` intentionally invalid).
- Verifies successful creations by querying the API per-satellite.
- Asserts intentionally-invalid POSTs are rejected by the API.
- Uses `satelliteId` + `status` filters to validate per-satellite counts.
- Deletes `healthy` records created by the run and confirms remaining records are `critical`.
- Saves the first paginated page to `first_page_results.csv` (default page size 100; override with `--page-size`).

Run from the project root:

  python tests/system_tests/load_test_telemetry.py --url http://localhost:8000/telemetry --total 1000 --concurrency 100

Flags: `--page-size`, `--no-cleanup`, `--cleanup-prefix`, `--error-rate`, `--sat-count`, `--create-file`
"""

# All imports in python library for maximum compatibility (no external dependencies)
import argparse
import concurrent.futures
import json
import csv
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any, Dict, List


def make_satellite_list(run_id: str, count: int) -> List[str]:
    return [f"LOAD-{run_id}-SAT-{i:03d}" for i in range(count)]


def build_payload(satellite_id: str, make_invalid: bool = False) -> Dict[str, Any]:
    altitude = round(random.uniform(160.0, 35786.0), 3)  # km
    velocity = round(random.uniform(0.5, 8.0), 3)  # km/s
    status = random.choices(["healthy", "critical"], weights=[0.8, 0.2])[0]
    ts = datetime.utcnow().isoformat()

    payload: Dict[str, Any] = {
        "satelliteId": satellite_id,
        "timestamp": ts,
        "altitude": altitude,
        "velocity": velocity,
        "status": status,
    }

    if not make_invalid:
        return payload

    # introduce a random validation error
    err_type = random.choice(["negative_velocity", "bad_status", "long_id", "missing_ts", "zero_altitude"])
    if err_type == "negative_velocity":
        payload["velocity"] = -abs(payload["velocity"])  # invalid (gt=0)
    elif err_type == "bad_status":
        payload["status"] = "unknown_status"
    elif err_type == "long_id":
        payload["satelliteId"] = payload["satelliteId"] + "-" + "X" * 100
    elif err_type == "missing_ts":
        payload.pop("timestamp", None)
    elif err_type == "zero_altitude":
        payload["altitude"] = 0

    return payload


def http_request(method: str, url: str, json_body: Dict[str, Any] = None, timeout: int = 15) -> Dict[str, Any]:
    headers = {"Content-Type": "application/json"} if json_body is not None else {}
    data = (json.dumps(json_body).encode("utf-8")) if json_body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body_bytes = resp.read()
            text = body_bytes.decode("utf-8") if body_bytes else ""
            try:
                body = json.loads(text) if text else {}
            except Exception:
                body = text
            return {"status_code": resp.getcode(), "body": body}
    except urllib.error.HTTPError as e:
        try:
            err_text = e.read().decode("utf-8")
            err_body = json.loads(err_text) if err_text else None
        except Exception:
            err_body = None
        return {"status_code": e.code, "body": err_body, "error": str(e)}
    except Exception as e:
        return {"status_code": None, "error": str(e)}


def post_request(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return http_request("POST", url, json_body=payload)


def get_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    qs = urllib.parse.urlencode(params)
    full = f"{url}?{qs}" if qs else url
    return http_request("GET", full)


def delete_request(url: str) -> Dict[str, Any]:
    return http_request("DELETE", url)


def gather_posts(url: str, total: int, concurrency: int, satellites: List[str], error_rate: float = 0.05):
    """Send POST requests concurrently and tag whether each request was intentionally invalid.

    Returns two lists (successes, failures) where each entry includes an
    `intentionally_invalid` boolean to allow post-run validation.
    """
    successes: List[Dict[str, Any]] = []
    failures: List[Dict[str, Any]] = []

    def worker(i: int):
        sat = random.choice(satellites)
        make_invalid = random.random() < error_rate
        payload = build_payload(sat, make_invalid=make_invalid)
        res = post_request(url, payload)
        if res.get("status_code") == 200:
            body = res.get("body") or {}
            successes.append({
                "id": body.get("id"),
                "satelliteId": payload.get("satelliteId"),
                "status": body.get("status"),
                "intentionally_invalid": make_invalid,
            })
        else:
            failures.append({"payload": payload, "result": res, "intentionally_invalid": make_invalid})

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        list(ex.map(worker, range(total)))

    return successes, failures


def get_total_for_satellite(base_url: str, satellite_id: str) -> int:
    r = get_request(base_url, {"satelliteId": satellite_id, "page": 1, "size": 1})
    if r.get("status_code") and r.get("body"):
        return int(r["body"].get("total", 0))
    return 0


def get_items(base_url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    page = 1
    # use a conservative page `size` that matches the API / pagination limits
    size = params.get("size", 50)
    collected: List[Dict[str, Any]] = []
    while True:
        q = params.copy()
        q.update({"page": page, "size": size})
        r = get_request(base_url, q)
        if not r.get("body"):
            break
        data = r["body"]
        items = data.get("items", [])
        collected.extend(items)
        if len(items) < size:
            break
        page += 1
    return collected


def delete_ids(base_url: str, ids: List[int], concurrency: int = 50) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []

    def _del(iid: int):
        r = delete_request(f"{base_url}/{iid}")
        results.append({"id": iid, "status": r.get("status_code")})

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as ex:
        list(ex.map(_del, ids))

    return results


def cleanup_previous_load_data(base_url: str, prefix: str = "LOAD-", page_size: int = 50) -> int:
    """Delete existing telemetry whose `satelliteId` starts with `prefix`.
    Returns the number of records deleted.
    """
    print(f"Pre-run cleanup: searching for telemetry with satelliteId starting with '{prefix}'")
    all_items = get_items(base_url, {"page": 1, "size": page_size})
    to_delete = [it for it in all_items if it.get("satelliteId", "").startswith(prefix)]
    ids = [it["id"] for it in to_delete if isinstance(it.get("id"), int)]

    if not ids:
        print(f"No existing '{prefix}' records found to clean up.")
        return 0

    print(f"Found {len(ids)} '{prefix}' records — deleting...")
    results = delete_ids(base_url, ids, concurrency=50)
    deleted_count = sum(1 for r in results if r.get("status") == 200)
    print(f"Deleted {deleted_count}/{len(ids)} previous '{prefix}' records.")
    return deleted_count


def main(args):
    base_url = args.url.rstrip("/")
    run_id = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    satellites = make_satellite_list(run_id, args.sat_count)

    print(f"Run id: {run_id} — creating {args.total} telemetry records across {len(satellites)} satellites (error-rate={args.error_rate})")

    t0 = time.time()
    successes, failures = gather_posts(base_url, args.total, args.concurrency, satellites, error_rate=args.error_rate)
    duration = time.time() - t0

    # --- Validation: ensure intentionally-invalid requests were rejected ---
    total_invalid_sent = sum(1 for s in successes if s.get("intentionally_invalid")) + sum(1 for f in failures if f.get("intentionally_invalid"))
    invalid_accepted = sum(1 for s in successes if s.get("intentionally_invalid"))
    invalid_rejected = sum(1 for f in failures if f.get("intentionally_invalid"))

    print(f"Posts finished in {duration:.2f}s — successes={len(successes)} failures={len(failures)}")
    print(f"Invalid requests sent: {total_invalid_sent}  |  invalid accepted: {invalid_accepted}  |  invalid rejected: {invalid_rejected}")

    if invalid_accepted > 0:
        raise AssertionError(f"{invalid_accepted} intentionally-invalid requests were accepted by the API — expected 0")

    # verify via API totals (sum totals for our satellite namespace)
    total_via_api = 0
    for sat in satellites:
        total_via_api += get_total_for_satellite(base_url, sat)

    print(f"Total records for run (via API): {total_via_api}")

    if total_via_api != len(successes):
        print("ERROR: mismatch between successful POST responses and API total for this run")
        print(f"  POST successes: {len(successes)}  |  API-reported: {total_via_api}")
    else:
        print("Count verification PASSED — API total matches successful POSTs")

    # Choose one satellite and verify filter behavior
    chosen = satellites[0]
    expected_by_status = {"healthy": 0, "critical": 0}
    for s in successes:
        if s["satelliteId"] == chosen:
            expected_by_status[s["status"]] = expected_by_status.get(s["status"], 0) + 1

    healthy_total = int(get_request(base_url, {"satelliteId": chosen, "status": "healthy", "page": 1, "size": 1}).get("body", {}).get("total", 0))
    critical_total = int(get_request(base_url, {"satelliteId": chosen, "status": "critical", "page": 1, "size": 1}).get("body", {}).get("total", 0))

    print(f"Satellite {chosen} — expected healthy={expected_by_status['healthy']} critical={expected_by_status['critical']}")
    print(f"API reports healthy={healthy_total} critical={critical_total}")

    if healthy_total == expected_by_status["healthy"] and critical_total == expected_by_status["critical"]:
        print("Filter verification PASSED for chosen satellite")
    else:
        print("Filter verification FAILED for chosen satellite")

    # Delete all healthy telemetries for our run (across all satellites)
    print("Collecting all healthy telemetry ids for deletion...")
    healthy_ids: List[int] = []
    for sat in satellites:
        items = get_items(base_url, {"satelliteId": sat, "status": "healthy", "size": 50})
        healthy_ids.extend([it["id"] for it in items if isinstance(it.get("id"), int)])

    print(f"Found {len(healthy_ids)} healthy records to delete")
    if healthy_ids:
        del_results = delete_ids(base_url, healthy_ids, concurrency=50)
        deleted_count = sum(1 for r in del_results if r.get("status") == 200)
        print(f"Deleted {deleted_count}/{len(healthy_ids)} healthy records")
    else:
        print("No healthy records to delete — skipping deletion")

    # Final verification: none of our satellites should have healthy records left
    final_healthy_total = 0
    final_total = 0
    final_critical_only = True
    for sat in satellites:
        total_for_sat = get_total_for_satellite(base_url, sat)
        final_total += total_for_sat
        healthy_for_sat = int(get_request(base_url, {"satelliteId": sat, "status": "healthy", "page": 1, "size": 1}).get("body", {}).get("total", 0))
        final_healthy_total += healthy_for_sat
        items = get_items(base_url, {"satelliteId": sat, "page": 1, "size": 50})
        for it in items:
            if it.get("status") != "critical":
                final_critical_only = False

    if final_healthy_total == 0 and final_critical_only:
        print("Cleanup verification PASSED — only critical telemetries remain for this run")
    else:
        print("Cleanup verification FAILED — healthy telemetries still present or non-critical items found")

    # --- Fetch only the first page (page size default = 100); optionally save to CSV ---
    # Allow overriding via CLI `--page-size` (clamped to 1..100)
    if getattr(args, "page_size", None) is not None:
        page_size = max(1, min(100, int(args.page_size)))
    else:
        page_size = max(1, min(100, args.total))

    if getattr(args, "create_file", False):
        print(f"Fetching first page (page=1) with page size={page_size} and saving to first_page_results.csv")

        resp = get_request(base_url, {"page": 1, "size": page_size})
        items = resp.get("body", {}).get("items", []) if resp.get("status_code") == 200 else []

        csv_file = "first_page_results.csv"
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            header = ["id", "satelliteId", "timestamp", "altitude", "velocity", "status", "created", "updated"]
            writer.writerow(header)
            for it in items:
                writer.writerow([it.get(h) for h in header])

        print(f"Saved {len(items)} items to {csv_file} (page_size={page_size}).")
        if len(items) == 0:
            print("Warning: first page returned 0 items — verify the API or try a different page_size.")
    else:
        print("Skipping CSV creation (use --create-file to write first_page_results.csv)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load-test the Telemetry API and run assertions")
    parser.add_argument("--url", default="http://localhost:8000/telemetry", help="Telemetry endpoint base URL")
    parser.add_argument("--total", type=int, default=1000, help="Total POST requests to send")
    parser.add_argument("--concurrency", type=int, default=100, help="Concurrent POSTs")
    parser.add_argument("--error-rate", type=float, default=0.05, help="Fraction of requests to make intentionally invalid")
    parser.add_argument("--sat-count", type=int, default=20, help="Number of distinct satelliteId values to use")
    parser.add_argument("--page-size", type=int, default=None, help="Page size for first page (result file) (1-100). If omitted defaults to min(100, --total)")
    parser.add_argument("--create-file", action="store_true", help="Create `first_page_results.csv` (default: false)")
    parser.add_argument("--cleanup-prefix", default="LOAD-", help="Prefix for satelliteId values to remove before running")
    parser.add_argument("--no-cleanup", action="store_true", help="Do not perform pre-run cleanup")
    args = parser.parse_args()

    if args.no_cleanup:
        print("Skipping pre-run cleanup (--no-cleanup)")
    else:
        # perform cleanup of previous load-test records
        cleanup_previous_load_data(args.url.rstrip('/'), prefix=args.cleanup_prefix)

    main(args)
