#!/usr/bin/env python3
"""
Tool tự động đăng nhập hàng loạt tài khoản Threads.
Nạp tài khoản từ .env (ưu tiên) hoặc accounts.json.
Lưu phiên làm việc an toàn vào thư mục sessions/.
"""

import asyncio
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from modules.config import load_app_config
from modules.auth import auto_login_all_accounts


async def main():
    config = load_app_config()
    accounts = config.get("accounts", [])
    sessions_dir = REPO_ROOT / config.get("auth", {}).get("sessions_dir", "sessions")

    await auto_login_all_accounts(accounts, sessions_dir=sessions_dir, headless=False)


if __name__ == "__main__":
    asyncio.run(main())
