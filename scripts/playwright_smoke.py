#!/usr/bin/env python
"""
Browser smoke checks for production using Playwright.

Usage examples:
    python scripts/playwright_smoke.py --base-url https://lootlink.ru
    python scripts/playwright_smoke.py --base-url https://lootlink.ru --headed
    python scripts/playwright_smoke.py --login-username user --login-password pass
"""

from __future__ import annotations

import argparse
import os
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


def parse_numeric_value(raw: str) -> int:
    digits = "".join(ch for ch in raw if ch.isdigit())
    if not digits:
        raise ValueError(f"could not parse numeric value from: {raw!r}")
    return int(digits)


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
    parser.add_argument(
        "--login-username",
        default=os.getenv("SMOKE_LOGIN_USERNAME", ""),
        help="Optional username/email for authenticated checks",
    )
    parser.add_argument(
        "--login-password",
        default=os.getenv("SMOKE_LOGIN_PASSWORD", ""),
        help="Password for --login-username",
    )
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    expected_home = f"{base_url}/"
    expected_login_url = urljoin(expected_home, "accounts/login/")
    expected_my_listings_url = urljoin(expected_home, "accounts/my-listings/")
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
        context = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1366, "height": 900},
        )
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

        def verify_no_horizontal_overflow() -> tuple[bool, str]:
            metrics = page.evaluate(
                """
                () => ({
                    clientWidth: document.documentElement.clientWidth,
                    scrollWidth: document.documentElement.scrollWidth,
                    bodyScrollWidth: document.body ? document.body.scrollWidth : 0
                })
                """
            )
            ok = metrics["scrollWidth"] <= metrics["clientWidth"] + 1
            detail = (
                f"client={metrics['clientWidth']}, "
                f"scroll={metrics['scrollWidth']}, "
                f"bodyScroll={metrics['bodyScrollWidth']}"
            )
            return ok, detail

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
        add_visit_check(page, "Login layout desktop", "/accounts/login/", verify=verify_no_horizontal_overflow)

        # Mobile layout check to catch form stretching or horizontal scroll regressions.
        try:
            page.set_viewport_size({"width": 390, "height": 844})
            response = page.goto(expected_login_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            status = response.status if response else None
            if status != 200:
                record(CheckResult("Login layout mobile", False, f"status={status}, url={expected_login_url}"))
            else:
                ok, detail = verify_no_horizontal_overflow()
                record(CheckResult("Login layout mobile", ok, detail))
        except PlaywrightError as exc:
            record(CheckResult("Login layout mobile", False, str(exc)))
        finally:
            page.set_viewport_size({"width": 1366, "height": 900})

        # Invalid login should keep user on login page and show visible error alert.
        try:
            page.goto(expected_login_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            page.locator("input[name='username']").fill("__smoke_invalid__")
            page.locator("input[name='password']").fill("__smoke_invalid__")
            with page.expect_navigation(wait_until="domcontentloaded", timeout=args.timeout_ms):
                page.locator("form[action$='/accounts/login/'] button[type='submit']").click()

            alert = page.locator(".messages-container .alert.alert-danger").first
            alert_count = page.locator(".messages-container .alert.alert-danger").count()
            alert_text = alert.inner_text().strip() if alert_count else ""
            alert_visible = alert.is_visible() if alert_count else False
            stays_on_login = "/accounts/login/" in page.url
            has_error_hint = any(token in alert_text.lower() for token in ("невер", "ошиб", "invalid"))

            ok = stays_on_login and alert_visible and has_error_hint
            detail = f"url={page.url}, alertVisible={alert_visible}, alertText={alert_text[:80]}"
            record(CheckResult("Invalid login feedback", ok, detail))
        except PlaywrightError as exc:
            record(CheckResult("Invalid login feedback", False, str(exc)))

        # Same counter should be shown on home/login for active users.
        try:
            page.goto(expected_home, wait_until="domcontentloaded", timeout=args.timeout_ms)
            home_item = page.locator(".hero-stats .stat-item", has_text="Активных пользователей").first
            home_count = home_item.count()
            if home_count == 0:
                raise ValueError("active users block not found on home page")
            home_users = parse_numeric_value(home_item.locator(".stat-value").first.inner_text())

            page.goto(expected_login_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
            login_item = page.locator(".info-stats .info-stat-item", has_text="Активных пользователей").first
            login_count = login_item.count()
            if login_count == 0:
                raise ValueError("active users block not found on login page")
            login_users = parse_numeric_value(login_item.locator(".info-stat-value").first.inner_text())

            users_ok = home_users == login_users
            record(
                CheckResult(
                    "Active users counter consistency",
                    users_ok,
                    f"home={home_users}, login={login_users}",
                )
            )
        except (PlaywrightError, ValueError) as exc:
            record(CheckResult("Active users counter consistency", False, str(exc)))

        # Optional authenticated check for real login redirect behavior.
        login_username = args.login_username.strip()
        login_password = args.login_password
        if login_username and login_password:
            try:
                target = f"{expected_login_url}?next=/accounts/my-listings/"
                page.goto(target, wait_until="domcontentloaded", timeout=args.timeout_ms)
                page.locator("input[name='username']").fill(login_username)
                page.locator("input[name='password']").fill(login_password)
                with page.expect_navigation(wait_until="domcontentloaded", timeout=args.timeout_ms):
                    page.locator("form[action$='/accounts/login/'] button[type='submit']").click()

                current_url = page.url
                auth_redirect_ok = current_url.startswith(expected_my_listings_url)
                record(CheckResult("Auth login redirect", auth_redirect_ok, f"url={current_url}"))
            except PlaywrightError as exc:
                record(CheckResult("Auth login redirect", False, str(exc)))
        else:
            record(
                CheckResult(
                    "Auth login redirect",
                    True,
                    "skipped (provide --login-username and --login-password for this check)",
                )
            )

        try:
            redirect_response = context.request.get(args.www_url, max_redirects=0, timeout=args.timeout_ms)
            location = redirect_response.headers.get("location", "")
            redirect_ok = redirect_response.status == 308 and location.startswith(expected_home)
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
