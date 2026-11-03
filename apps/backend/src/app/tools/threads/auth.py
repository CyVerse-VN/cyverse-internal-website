import argparse
import asyncio
import binascii
import json
import os
import tempfile
from pathlib import Path

import pyotp
from playwright.async_api import BrowserContext, Locator, Page, async_playwright
from playwright.async_api import Error as PlaywrightError

from app.tools.threads.config import ThreadsAccount, ThreadsConfig, threads_config
from app.tools.threads.crawler import playwright_proxy
from app.tools.threads.errors import ThreadsError
from app.tools.threads.session import create_session_bundle


async def first_visible(page: Page, selectors: str, timeout_seconds: float = 20) -> Locator:
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        inputs = page.locator(selectors)
        for index in range(await inputs.count()):
            locator = inputs.nth(index)
            if await locator.is_visible():
                return locator
        await page.wait_for_timeout(250)
    raise ThreadsError("LOGIN_FIELD_NOT_FOUND", "The Threads login form was not found.")


async def submit_credentials(page: Page, account: ThreadsAccount) -> None:
    if not account.username or not account.password:
        raise ThreadsError(
            "LOGIN_CREDENTIALS_REQUIRED",
            "Configure the account username and password or use --manual.",
        )
    username = await first_visible(
        page,
        'input[autocomplete="username"], input[name="username"], input[type="text"]',
        timeout_seconds=30,
    )
    password = await first_visible(
        page,
        'input[autocomplete="current-password"], input[name="password"], input[type="password"]',
        timeout_seconds=30,
    )
    await username.fill(account.username.get_secret_value())
    await password.fill(account.password.get_secret_value())
    await password.press("Enter")
    if account.totp_secret:
        try:
            code_field = await first_visible(
                page,
                'input[name="verificationCode"], input[name="approvals_code"], '
                'input[autocomplete="one-time-code"]',
                timeout_seconds=15,
            )
        except ThreadsError as error:
            if error.code != "LOGIN_FIELD_NOT_FOUND":
                raise
            # Existing trusted devices can skip the MFA form entirely.
            return
        try:
            code = pyotp.TOTP(account.totp_secret.get_secret_value().replace(" ", "")).now()
        except (ValueError, TypeError, binascii.Error):
            raise ThreadsError(
                "INVALID_TOTP_SECRET", "Configure a valid Threads TOTP secret."
            ) from None
        await code_field.fill(code)
        await code_field.press("Enter")


def bundle_local_sessions(config: ThreadsConfig) -> Path:
    """Bundle all available local session files into threads_sessions.json."""
    sessions: dict[str, dict[str, object]] = {}
    for account in config.accounts:
        account_path = config.session_path(account)
        if account_path.is_file():
            try:
                data = json.loads(account_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "cookies" in data:
                    sessions[account.id] = data
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                continue

    bundle = create_session_bundle(sessions)
    bundle_path = config.sessions_dir / "threads_sessions.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(bundle, indent=2, ensure_ascii=False)
    bundle_path.write_text(content, encoding="utf-8")
    if sessions:
        try:
            Path("threads_sessions.json").write_text(content, encoding="utf-8")
        except OSError:
            pass
    return bundle_path


async def save_session(context: BrowserContext, path: Path) -> None:
    state = await context.storage_state()
    authenticated = any(
        cookie["name"] == "sessionid"
        and cookie["value"]
        and cookie["domain"].lstrip(".") in {"threads.com", "threads.net", "instagram.com"}
        for cookie in state["cookies"]
    )
    if not authenticated:
        raise ThreadsError(
            "THREADS_REAUTH_REQUIRED", "The browser has no authenticated Threads session."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        if os.name != "nt":
            os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


async def login_in_context(
    page: Page, context: BrowserContext, account: ThreadsAccount, path: Path,
    *, manual: bool = False, timeout_seconds: int = 180,
) -> None:
    await page.goto("https://www.threads.com/login", wait_until="domcontentloaded", timeout=45000)
    if not manual:
        await submit_credentials(page, account)
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        cookies = await context.cookies()
        if any(cookie["name"] == "sessionid" and cookie["value"] for cookie in cookies):
            await page.goto("https://www.threads.com/", wait_until="domcontentloaded", timeout=30000)
            if "/login" not in page.url and "/challenge" not in page.url:
                await save_session(context, path)
                return
        await page.wait_for_timeout(1000)
    raise ThreadsError("LOGIN_TIMEOUT", "Complete login and any verification prompts before retrying.")


async def login_account(
    config: ThreadsConfig, account_id: str, *, manual: bool, headless: bool, timeout_seconds: int
) -> None:
    account = next((item for item in config.accounts if item.id == account_id), None)
    if account is None:
        raise ThreadsError(
            "ACCOUNT_NOT_FOUND", "The account ID is not configured in THREADS_ACCOUNTS."
        )
    if manual and headless:
        raise ThreadsError("INVALID_LOGIN_MODE", "Manual login requires a visible browser.")
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=headless)
            try:
                context = await browser.new_context(
                    proxy=playwright_proxy(account.proxy.get_secret_value())
                    if account.proxy
                    else None,
                    locale="en-US",
                    viewport={"width": 1280, "height": 900},
                )
                page = await context.new_page()
                await login_in_context(page, context, account, config.session_path(account),
                                       manual=manual, timeout_seconds=timeout_seconds)
                bundle_local_sessions(config)
            finally:
                await browser.close()
    except (PlaywrightError, OSError, ValueError):
        raise ThreadsError(
            "LOGIN_FAILED", "Threads login failed. Check Chromium, credentials, and proxy settings."
        ) from None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a Threads session using the shared backend environment."
    )
    parser.add_argument("account_id", nargs="?", default=None, help="Account ID from THREADS_ACCOUNTS")
    parser.add_argument(
        "--bundle", action="store_true", help="Bundle existing local sessions into threads_sessions.json"
    )
    parser.add_argument(
        "--manual", action="store_true", help="Complete login in the browser manually"
    )
    parser.add_argument(
        "--headless", action="store_true", help="Run credential login without a visible browser"
    )
    parser.add_argument(
        "--timeout", type=int, default=180, help="Seconds allowed for login and verification"
    )
    args = parser.parse_args()
    if args.bundle:
        bundle_path = bundle_local_sessions(threads_config)
        print(f"Threads sessions bundled into {bundle_path}.")
        return

    if not args.account_id:
        parser.error("account_id is required unless --bundle is specified")

    if not 10 <= args.timeout <= 600:
        parser.error("--timeout must be between 10 and 600 seconds")
    try:
        asyncio.run(
            login_account(
                threads_config,
                args.account_id,
                manual=args.manual,
                headless=args.headless,
                timeout_seconds=args.timeout,
            )
        )
    except ThreadsError as error:
        raise SystemExit(error.detail) from None
    print("Threads login session saved.")



if __name__ == "__main__":
    main()
