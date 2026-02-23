#!/usr/bin/env python
"""
Browser smoke checks for production using Playwright.

Usage examples:
    python scripts/playwright_smoke.py --base-url https://lootlink.ru
    python scripts/playwright_smoke.py --base-url https://lootlink.ru --headed
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from typing import Callable
from urllib.parse import urljoin

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str = ""


def normalize_base_url(raw_url: str) -> str:
    value = raw_url.strip()
    if not value:
        raise ValueError("base URL must not be empty")
    if not value.startswith("http://") and not value.startswith("https://"):
        value = f"https://{value}"
    return value.rstrip("/")


def run() -> int:
    parser = argparse.ArgumentParser(description="Playwright browser smoke checks")
    parser.add_argument(
        "--base-url",
        default="https://lootlink.ru",
        help="Base URL for checks, for example: https://lootlink.ru",
    )
    parser.add_argument(
        "--www-url",
        default="https://www.lootlink.ru/",
        help="WWW URL for canonical redirect check",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=30000,
        help="Navigation timeout in milliseconds",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode",
    )
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    expected_home = f"{base_url}/"
    checks: list[CheckResult] = []

    console_warnings: list[str] = []
    console_errors: list[str] = []
    js_errors: list[str] = []
    request_failures: list[str] = []
    same_origin_request_failures: list[str] = []

    def record(result: CheckResult) -> None:
        checks.append(result)
        state = "PASS" if result.ok else "FAIL"
        suffix = f" - {result.detail}" if result.detail else ""
        print(f"[{state}] {result.name}{suffix}")

    def add_visit_check(page, name: str, path: str, verify: Callable[[], tuple[bool, str]] | None = None) -> None:
        url = urljoin(expected_home, path.lstrip("/"))
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            status = response.status if response else None
            if status != 200:
                record(CheckResult(name=name, ok=False, detail=f"status={status}, url={url}"))
                return
            if verify is None:
                record(CheckResult(name=name, ok=True, detail=f"status=200, url={url}"))
                return
            ok, detail = verify()
            record(CheckResult(name=name, ok=ok, detail=detail))
        except PlaywrightError as exc:
            record(CheckResult(name=name, ok=False, detail=f"{url}: {exc}"))

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(ignore_https_errors=True)
        page = context.new_page()

        def on_console(msg) -> None:
            line = f"{msg.type.upper()}: {msg.text}"
            if msg.type == "error":
                console_errors.append(line)
            elif msg.type == "warning":
                console_warnings.append(line)

        def on_request_failed(req) -> None:
            failure = req.failure
            if isinstance(failure, dict):
                reason = failure.get("errorText", "unknown")
            elif isinstance(failure, str):
                reason = failure
            else:
                reason = str(failure) if failure is not None else "unknown"
            line = f"{req.method} {req.url} -> {reason}"
            request_failures.append(line)
            if req.url.startswith(expected_home):
                same_origin_request_failures.append(line)

        page.on("console", on_console)
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))
        page.on("requestfailed", on_request_failed)

        add_visit_check(page, "Home page", "/")
        add_visit_check(page, "Catalog page", "/catalog/")
        add_visit_check(page, "Login page", "/accounts/login/")
        add_visit_check(page, "Register page", "/accounts/register/")

        def verify_home_meta() -> tuple[bool, str]:
            canonical = page.locator("link[rel='canonical']").first.get_attribute("href")
            og_url = page.locator("meta[property='og:url']").first.get_attribute("content")
            manifest = page.locator("link[rel='manifest']").first.get_attribute("href")
            ok = (
                canonical == expected_home
                and og_url == expected_home
                and bool(manifest)
                and "manifest.json" in manifest
            )
            detail = f"canonical={canonical}, og:url={og_url}, manifest={manifest}"
            return ok, detail

        add_visit_check(page, "Home SEO meta", "/", verify=verify_home_meta)

        try:
            redirect_response = context.request.get(args.www_url, max_redirects=0, timeout=args.timeout_ms)
            location = redirect_response.headers.get("location", "")
            redirect_ok = redirect_response.status == 301 and location.startswith(expected_home)
            detail = f"status={redirect_response.status}, location={location}"
            record(CheckResult("WWW redirect", redirect_ok, detail))
        except PlaywrightError as exc:
            record(CheckResult("WWW redirect", False, str(exc)))

        browser.close()

    if console_errors:
        print("\nConsole errors:")
        for item in console_errors[:20]:
            print(f"- {item}")
    if console_warnings:
        print("\nConsole warnings:")
        for item in console_warnings[:20]:
            print(f"- {item}")
    if js_errors:
        print("\nPage errors:")
        for item in js_errors[:20]:
            print(f"- {item}")
    if request_failures:
        print("\nRequest failures:")
        for item in request_failures[:20]:
            print(f"- {item}")

    hard_failures = [c for c in checks if not c.ok]
    if console_errors or js_errors or same_origin_request_failures:
        hard_failures.append(
            CheckResult(
                "Browser runtime health",
                False,
                "console errors, JS exceptions, or same-origin request failures detected",
            )
        )

    print("\nSummary:")
    print(f"- Checks passed: {len(checks) - len([c for c in checks if not c.ok])}/{len(checks)}")
    print(f"- Console errors: {len(console_errors)}")
    print(f"- Console warnings: {len(console_warnings)}")
    print(f"- Page errors: {len(js_errors)}")
    print(f"- Request failures: {len(request_failures)}")
    print(f"- Same-origin request failures: {len(same_origin_request_failures)}")

    if hard_failures:
        print("\nSmoke result: FAILED")
        return 1

    print("\nSmoke result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(run())
