#!/usr/bin/env python3
"""
CLI Tool: Kiểm tra và tải proxy sống từ Proxifly CDN cho Threads.
"""

from __future__ import annotations

import argparse
import asyncio
import json
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
from modules.proxy import get_healthy_proxies, test_proxy_against_threads


async def check_account_proxies(auto_fix: bool = False, protocol: str = "http") -> None:
    config = load_app_config()
    accounts = config.get("accounts", [])
    accounts_file = REPO_ROOT / "accounts.json"

    print("=" * 70)
    print("🔍 KIỂM TRA PROXY CỦA CÁC TÀI KHOẢN VỚI THREADS")
    print("=" * 70)

    dead_indices = []
    for i, acc in enumerate(accounts):
        aid = acc.get("id", f"acc_{i+1:02d}")
        uname = acc.get("username", "")
        p = acc.get("proxy", "").strip()

        if not p:
            print(f"   ℹ️ [{aid}] @{uname}: Kết nối trực tiếp (Direct IP)")
            continue

        print(f"   ⏳ [{aid}] Đang kiểm tra proxy: {p}...", end=" ", flush=True)
        res = await test_proxy_against_threads(p, timeout=5.0)
        if res:
            print(f"-> ✅ HOẠT ĐỘNG TỐT ({res[1]}s)")
        else:
            print("-> ❌ KHÔNG PHẢN HỒI (DEAD)")
            dead_indices.append(i)

    if dead_indices and auto_fix:
        print(f"\n🔄 Tìm thấy {len(dead_indices)} proxy bị chết. Đang tìm proxy mới thay thế...")
        new_proxies = await get_healthy_proxies(needed=len(dead_indices), sample_size=60, protocol=protocol)
        for idx, new_p in zip(dead_indices, new_proxies):
            accounts[idx]["proxy"] = new_p
            print(f"   🔗 Đã đổi {accounts[idx].get('id')} ➡️ {new_p}")
        with open(accounts_file, "w", encoding="utf-8") as f:
            json.dump({"accounts": accounts}, f, ensure_ascii=False, indent=2)
        print("💾 Đã cập nhật accounts.json thành công!")
    elif dead_indices:
        print("\n💡 Gợi ý: Chạy lệnh sau để tự động thay thế các proxy bị chết:")
        print("   python free_proxy_manager.py --check --auto-fix")
    else:
        print("\n🎉 Tất cả proxy của các tài khoản đều đang hoạt động tốt!")


def main():
    parser = argparse.ArgumentParser(description="Proxifly Free Proxy Fetcher & Validator for Threads")
    parser.add_argument("--count", type=int, default=5, help="Số proxy sống cần lấy (mặc định 5)")
    parser.add_argument("--sample", type=int, default=60, help="Số proxy đem ra test (mặc định 60)")
    parser.add_argument("--protocol", choices=["http", "https", "socks5", "all"], default="http", help="Giao thức proxy")
    parser.add_argument("--check", action="store_true", help="Kiểm tra proxy của các tài khoản")
    parser.add_argument("--auto-fix", action="store_true", help="Tự động thay thế proxy bị chết")
    args = parser.parse_args()

    if args.check:
        asyncio.run(check_account_proxies(auto_fix=args.auto_fix, protocol=args.protocol))
    else:
        save_path = REPO_ROOT / "proxies.txt"
        asyncio.run(get_healthy_proxies(needed=args.count, sample_size=args.sample, protocol=args.protocol, save_file=save_path))


if __name__ == "__main__":
    main()
