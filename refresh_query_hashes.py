from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

PlaywrightTimeoutError = Exception

from api_queries import DEFAULT_QUERY_HASHES, OPERATION_NAMES, QueryType

ROOT = Path(__file__).resolve().parent
QUERY_HASHES_FILE = ROOT / "query_hashes.json"

AUTO_START_URLS = [
    "https://www.racenet.com.au/form-guide/horse-racing",
    "https://www.racenet.com.au/results/horse-racing",
    "https://www.racenet.com.au/horse-racing-tips",
]

DISMISS_MODAL_SELECTORS = [
    ".campaign-modal__overlay",
    ".campaign-modal__close",
    ".np-web-widget-campaign-modal .close",
]

OPERATION_TO_QUERY_TYPE = {
    operation_name: query_type for query_type, operation_name in OPERATION_NAMES.items()
}


def load_existing_hashes() -> dict[QueryType, str]:
    hashes = DEFAULT_QUERY_HASHES.copy()

    try:
        with QUERY_HASHES_FILE.open("r", encoding="utf-8") as hash_file:
            stored_hashes = json.load(hash_file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return hashes

    if not isinstance(stored_hashes, dict):
        return hashes

    for query_type_name, query_hash in stored_hashes.items():
        if not isinstance(query_type_name, str) or not isinstance(query_hash, str):
            continue
        try:
            query_type = QueryType[query_type_name]
        except KeyError:
            continue
        hashes[query_type] = query_hash

    return hashes


def save_hashes(hashes: dict[QueryType, str]) -> None:
    serializable_hashes = {
        query_type.name: hashes[query_type]
        for query_type in QueryType
        if query_type in hashes
    }
    with QUERY_HASHES_FILE.open("w", encoding="utf-8") as hash_file:
        json.dump(serializable_hashes, hash_file, indent=2)
        hash_file.write("\n")


def parse_persisted_query_hash(
    request_url: str, post_data: str | None
) -> tuple[str | None, str | None]:
    operation_name: str | None = None
    query_hash: str | None = None

    parsed_url = urlparse(request_url)
    query_params = parse_qs(parsed_url.query)

    operation_name_values = query_params.get("operationName")
    if operation_name_values:
        operation_name = operation_name_values[0]

    extensions_values = query_params.get("extensions")
    if extensions_values:
        try:
            extensions = json.loads(extensions_values[0])
        except json.JSONDecodeError:
            extensions = None
        if isinstance(extensions, dict):
            persisted_query = extensions.get("persistedQuery")
            if isinstance(persisted_query, dict):
                query_hash = persisted_query.get("sha256Hash")

    if post_data:
        try:
            payload = json.loads(post_data)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            if operation_name is None:
                payload_operation_name = payload.get("operationName")
                if isinstance(payload_operation_name, str):
                    operation_name = payload_operation_name
            if query_hash is None:
                persisted_query = payload.get("extensions", {}).get("persistedQuery")
                if isinstance(persisted_query, dict):
                    payload_hash = persisted_query.get("sha256Hash")
                    if isinstance(payload_hash, str):
                        query_hash = payload_hash

    return operation_name, query_hash


def dismiss_modals(page: Any) -> None:
    for selector in DISMISS_MODAL_SELECTORS:
        try:
            page.locator(selector).first.click(timeout=1_000)
        except (PlaywrightTimeoutError, Exception):
            continue
        except Exception:
            continue

    try:
        page.evaluate(
            """
            () => {
              document
                .querySelectorAll('.np-web-widget-campaign-modal, .campaign-modal, .campaign-modal__overlay')
                .forEach((node) => node.remove());
            }
            """
        )
    except Exception:
        pass


def auto_browse(page: Any) -> None:
    for url in AUTO_START_URLS:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(3_000)
            dismiss_modals(page)
        except (PlaywrightTimeoutError, Exception):
            continue

    try:
        meeting_links = page.locator('a[href*="/all-races/overview"]')
        link_count = min(meeting_links.count(), 3)
        for index in range(link_count):
            href = meeting_links.nth(index).get_attribute("href")
            if not href:
                continue
            page.goto(
                f"https://www.racenet.com.au{href}", wait_until="domcontentloaded"
            )
            page.wait_for_timeout(3_000)
            dismiss_modals(page)
        page.goto(AUTO_START_URLS[0], wait_until="domcontentloaded", timeout=30_000)
    except Exception:
        return


def main() -> int:
    try:
        sync_api = importlib.import_module("playwright.sync_api")
        sync_playwright = sync_api.sync_playwright
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "Playwright is not installed. Run `python -m pip install -r requirements-dev.txt` "
            "and `python -m playwright install chromium` first."
        ) from exc

    parser = argparse.ArgumentParser(
        description=(
            "Capture persisted GraphQL query hashes from Racenet page traffic and "
            "write them to query_hashes.json."
        )
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Launch a visible Chromium window instead of running headless.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Keep the browser open after the auto crawl so you can click through pages manually.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=60,
        help="Maximum number of seconds to wait during interactive capture before finishing.",
    )
    args = parser.parse_args()

    if args.interactive and not args.headed:
        parser.error("--interactive requires --headed so you can browse the site.")

    captured_hashes = load_existing_hashes()
    captured_from_browser: set[QueryType] = set()

    def handle_request(request: Any) -> None:
        if "puntapi.com/graphql-horse-racing" not in request.url:
            return

        operation_name, query_hash = parse_persisted_query_hash(
            request.url, request.post_data
        )
        if not operation_name or not query_hash:
            return

        query_type = OPERATION_TO_QUERY_TYPE.get(operation_name)
        if query_type is None:
            return

        captured_hashes[query_type] = query_hash
        captured_from_browser.add(query_type)
        print(f"Captured {query_type.name}: {query_hash}")

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headed)
        context = browser.new_context()
        page = context.new_page()
        page.on("request", handle_request)

        auto_browse(page)

        if args.interactive:
            print("Interactive capture mode is active.")
            print(
                "Browse Racenet pages in the opened browser, then press Enter here to finish."
            )
            try:
                input()
            except EOFError:
                page.wait_for_timeout(args.timeout_seconds * 1_000)

        browser.close()

    save_hashes(captured_hashes)

    missing_query_types = [
        query_type.name
        for query_type in OPERATION_NAMES
        if query_type not in captured_from_browser
    ]

    if missing_query_types:
        print(
            "Updated query_hashes.json with captured values and kept existing hashes for:"
        )
        for query_type_name in missing_query_types:
            print(f"  - {query_type_name}")
        print(
            "If any of those hashes are stale, rerun with --headed --interactive and browse the missing pages."
        )
    else:
        print("Captured all known persisted query hashes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
