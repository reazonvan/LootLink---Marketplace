#!/usr/bin/env python
"""
Authenticated browser user-journey checks for production/staging.

Scenarios:
1. Seller logs in and creates a listing.
2. Buyer opens listing, starts chat, and sends a message.
3. Buyer creates a purchase request for the listing.

Usage:
    python scripts/playwright_user_journey.py --base-url https://lootlink.ru

Credentials can be passed either via arguments or environment variables:
    SMOKE_SELLER_USERNAME / SMOKE_SELLER_PASSWORD
    SMOKE_BUYER_USERNAME / SMOKE_BUYER_PASSWORD
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
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


def first_cookie_value(cookies: Iterable[dict], name_part: str) -> str:
    needle = name_part.lower()
    for cookie in cookies:
        if needle in cookie.get("name", "").lower():
            return cookie.get("value", "")
    return ""


def login(page: Page, base_url: str, username: str, password: str, timeout_ms: int) -> tuple[bool, str]:
    login_url = urljoin(f"{base_url}/", "accounts/login/")
    page.goto(login_url, wait_until="domcontentloaded", timeout=timeout_ms)

    page.locator("input[name='username']").fill(username)
    page.locator("input[name='password']").fill(password)
    with page.expect_navigation(wait_until="domcontentloaded", timeout=timeout_ms):
        page.locator("form[action$='/accounts/login/'] button[type='submit']").click()

    if "/accounts/login/" in page.url:
        error_text = ""
        alert = page.locator(".messages-container .alert").first
        if alert.count():
            error_text = alert.inner_text().strip()
        return False, f"login stayed on {page.url}, alert={error_text}"
    return True, page.url


def logout(page: Page, base_url: str, timeout_ms: int) -> None:
    logout_url = urljoin(f"{base_url}/", "accounts/logout/")
    try:
        page.goto(logout_url, wait_until="domcontentloaded", timeout=timeout_ms)
    except PlaywrightError:
        # Logout is best-effort in automation setup.
        pass


def run() -> int:
    parser = argparse.ArgumentParser(description="Playwright authenticated user journeys")
    parser.add_argument(
        "--base-url",
        default="https://lootlink.ru",
        help="Base URL for checks, for example: https://lootlink.ru",
    )
    parser.add_argument("--timeout-ms", type=int, default=30000, help="Navigation timeout in milliseconds")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed mode")
    parser.add_argument("--seller-username", default=os.getenv("SMOKE_SELLER_USERNAME", ""))
    parser.add_argument("--seller-password", default=os.getenv("SMOKE_SELLER_PASSWORD", ""))
    parser.add_argument("--buyer-username", default=os.getenv("SMOKE_BUYER_USERNAME", ""))
    parser.add_argument("--buyer-password", default=os.getenv("SMOKE_BUYER_PASSWORD", ""))
    args = parser.parse_args()

    missing_args = []
    if not args.seller_username.strip():
        missing_args.append("--seller-username / SMOKE_SELLER_USERNAME")
    if not args.seller_password:
        missing_args.append("--seller-password / SMOKE_SELLER_PASSWORD")
    if not args.buyer_username.strip():
        missing_args.append("--buyer-username / SMOKE_BUYER_USERNAME")
    if not args.buyer_password:
        missing_args.append("--buyer-password / SMOKE_BUYER_PASSWORD")
    if missing_args:
        print("Missing required credentials:")
        for item in missing_args:
            print(f"- {item}")
        return 2

    base_url = normalize_base_url(args.base_url)
    expected_root = f"{base_url}/"

    checks: list[CheckResult] = []
    console_errors: list[str] = []
    js_errors: list[str] = []
    same_origin_request_failures: list[str] = []

    def record(name: str, ok: bool, detail: str = "") -> None:
        checks.append(CheckResult(name=name, ok=ok, detail=detail))
        state = "PASS" if ok else "FAIL"
        suffix = f" - {detail}" if detail else ""
        print(f"[{state}] {name}{suffix}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(
            ignore_https_errors=True,
            viewport={"width": 1366, "height": 900},
        )
        page = context.new_page()

        page.on(
            "console",
            lambda msg: console_errors.append(f"{msg.type.upper()}: {msg.text}") if msg.type == "error" else None,
        )
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))

        def on_request_failed(req) -> None:
            failure = req.failure
            if isinstance(failure, dict):
                reason = failure.get("errorText", "unknown")
            elif isinstance(failure, str):
                reason = failure
            else:
                reason = str(failure) if failure is not None else "unknown"
            if req.url.startswith(expected_root):
                same_origin_request_failures.append(f"{req.method} {req.url} -> {reason}")

        page.on("requestfailed", on_request_failed)

        listing_url = ""
        listing_title = f"[SMOKE] E2E listing {int(time.time())}"

        # Scenario 1: seller login and listing creation
        try:
            logout(page, base_url, args.timeout_ms)
            ok, detail = login(page, base_url, args.seller_username.strip(), args.seller_password, args.timeout_ms)
            record("Seller login", ok, detail)
            if ok:
                create_url = urljoin(expected_root, "listing/create/")
                page.goto(create_url, wait_until="domcontentloaded", timeout=args.timeout_ms)

                if "/accounts/login/" in page.url:
                    record("Seller access listing create", False, f"redirected to login: {page.url}")
                else:
                    game_options = page.locator("select[name='game'] option").evaluate_all(
                        "opts => opts.map(o => ({ value: o.value, label: (o.textContent || '').trim() }))"
                    )
                    game_value = ""
                    for option in game_options:
                        value = (option.get("value") or "").strip()
                        if value:
                            game_value = value
                            break

                    if not game_value:
                        record(
                            "Seller create listing",
                            False,
                            "no active games in listing form (run setup_smoke_data first)",
                        )
                    else:
                        page.locator("select[name='game']").select_option(game_value)
                        page.wait_for_timeout(800)

                        category_options = page.locator("select[name='category'] option").evaluate_all(
                            "opts => opts.map(o => (o.value || '').trim()).filter(v => v)"
                        )
                        if category_options:
                            page.locator("select[name='category']").select_option(category_options[0])

                        page.locator("input[name='title']").fill(listing_title)
                        page.locator("textarea[name='description']").fill(
                            "Smoke e2e listing description with enough length to pass form validation checks."
                        )
                        page.locator("input[name='price']").fill("123.45")

                        with page.expect_navigation(wait_until="domcontentloaded", timeout=args.timeout_ms):
                            page.locator("form button[type='submit']").click()

                        url_ok = re.search(r"/listing/\d+/?$", page.url) is not None
                        title_ok = page.locator(".listing-detail-title", has_text=listing_title).count() > 0
                        scenario_ok = url_ok and title_ok
                        listing_url = page.url if url_ok else ""
                        record("Seller create listing", scenario_ok, f"url={page.url}")
        except PlaywrightError as exc:
            record("Seller journey", False, str(exc))

        # Scenario 2: buyer login + chat
        try:
            if not listing_url:
                record("Buyer open listing", False, "listing URL is missing from seller scenario")
            else:
                logout(page, base_url, args.timeout_ms)
                ok, detail = login(page, base_url, args.buyer_username.strip(), args.buyer_password, args.timeout_ms)
                record("Buyer login", ok, detail)

                if ok:
                    page.goto(listing_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
                    open_ok = page.locator("a.btn.btn-primary", has_text="Написать продавцу").count() > 0
                    record("Buyer open listing", open_ok, f"url={page.url}")

                    if open_ok:
                        with page.expect_navigation(wait_until="domcontentloaded", timeout=args.timeout_ms):
                            page.locator("a.btn.btn-primary", has_text="Написать продавцу").click()

                        in_chat = re.search(r"/chat/conversation/\d+/?$", page.url) is not None
                        if not in_chat:
                            record("Buyer start chat", False, f"unexpected URL: {page.url}")
                        else:
                            record("Buyer start chat", True, f"url={page.url}")

                            message_text = f"Smoke chat ping {int(time.time())}"
                            csrf_token = first_cookie_value(context.cookies(), "csrftoken")
                            response = context.request.post(
                                page.url,
                                form={
                                    "csrfmiddlewaretoken": csrf_token,
                                    "content": message_text,
                                },
                                headers={"Referer": page.url},
                                timeout=args.timeout_ms,
                            )
                            post_ok = response.status in (200, 302)
                            page.reload(wait_until="domcontentloaded", timeout=args.timeout_ms)
                            message_ok = page.locator(".message-bubble-chat", has_text=message_text).count() > 0
                            record(
                                "Buyer send chat message",
                                post_ok and message_ok,
                                f"postStatus={response.status}, visible={message_ok}",
                            )
        except PlaywrightError as exc:
            record("Buyer chat scenario", False, str(exc))

        # Scenario 3: buyer purchase request
        try:
            if not listing_url:
                record("Buyer create purchase request", False, "listing URL is missing from seller scenario")
            else:
                page.goto(listing_url, wait_until="domcontentloaded", timeout=args.timeout_ms)
                buy_button = page.locator("a.btn.btn-success", has_text="Купить сейчас").first
                if buy_button.count() == 0:
                    record("Buyer create purchase request", False, "buy button not found on listing page")
                else:
                    with page.expect_navigation(wait_until="domcontentloaded", timeout=args.timeout_ms):
                        buy_button.click()

                    on_form = re.search(r"/transactions/purchase-request/\d+/create/?$", page.url) is not None
                    if not on_form:
                        record("Buyer create purchase request", False, f"unexpected form URL: {page.url}")
                    else:
                        page.locator("textarea[name='message']").fill(
                            "Smoke purchase request message created by automated journey."
                        )
                        with page.expect_navigation(wait_until="domcontentloaded", timeout=args.timeout_ms):
                            page.locator("form button[type='submit']").click()

                        on_detail = re.search(r"/transactions/purchase-request/\d+/?$", page.url) is not None
                        record("Buyer create purchase request", on_detail, f"url={page.url}")
        except PlaywrightError as exc:
            record("Buyer purchase scenario", False, str(exc))

        browser.close()

    failed = [c for c in checks if not c.ok]
    if console_errors:
        print("\nConsole errors:")
        for item in console_errors[:20]:
            print(f"- {item}")
    if js_errors:
        print("\nPage errors:")
        for item in js_errors[:20]:
            print(f"- {item}")
    if same_origin_request_failures:
        print("\nSame-origin request failures:")
        for item in same_origin_request_failures[:20]:
            print(f"- {item}")

    print("\nSummary:")
    print(f"- Checks passed: {len(checks) - len(failed)}/{len(checks)}")
    print(f"- Failed checks: {len(failed)}")
    print(f"- Console errors: {len(console_errors)}")
    print(f"- Page errors: {len(js_errors)}")
    print(f"- Same-origin request failures: {len(same_origin_request_failures)}")

    if failed or console_errors or js_errors or same_origin_request_failures:
        print("\nUser journey result: FAILED")
        return 1

    print("\nUser journey result: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(run())
