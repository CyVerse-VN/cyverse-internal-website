#!/usr/bin/env python3
"""
Meta Threads Scraper - Unified Management CLI
Trung tâm điều khiển duy nhất cho toàn bộ hệ thống Threads Scraper & AI Curation.

Cách sử dụng:
  python main.py                            # Chạy cào dữ liệu theo config.py
  python main.py "quán cafe vintage"        # Chạy cào từ khóa trực tiếp
  python main.py run --query "..."          # Lệnh run tương đương
  python main.py login                      # Tự động đăng nhập lưu session từ .env
  python main.py login --manual             # Mở trình duyệt đăng nhập thủ công
  python main.py proxy                      # Kiểm tra & làm mới proxy miễn phí từ CDN
  python main.py test                       # Chạy toàn bộ bộ kiểm thử tự động
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đảm bảo import từ src/
REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from modules.config import load_app_config
from modules.pipeline import execute_pipeline


def cmd_run(args: argparse.Namespace) -> None:
    query = args.query or args.positional_query
    asyncio.run(execute_pipeline(custom_query=query))


def cmd_login(args: argparse.Namespace) -> None:
    if args.manual:
        from scripts.manual_login import manual_login
        asyncio.run(manual_login())
    else:
        from modules.auth import auto_login_all_accounts
        config = load_app_config()
        accounts = config.get("accounts", [])
        sessions_dir = REPO_ROOT / config.get("auth", {}).get("sessions_dir", "sessions")
        asyncio.run(auto_login_all_accounts(accounts, sessions_dir=sessions_dir, headless=not args.headed))


def cmd_proxy(args: argparse.Namespace) -> None:
    from modules.proxy import get_healthy_proxies
    from scripts.manage_proxies import check_account_proxies

    if args.check:
        asyncio.run(check_account_proxies(auto_fix=args.auto_fix))
    else:
        async def refresh():
            print(f"🔄 Đang tải và kiểm tra {args.limit} proxy hoạt động tốt từ Proxifly CDN...")
            proxies = await get_healthy_proxies(needed=args.limit, sample_size=args.limit * 3)
            out_file = REPO_ROOT / "proxies.txt"
            if proxies:
                out_file.write_text("\n".join(proxies) + "\n", encoding="utf-8")
                print(f"✅ Đã lưu {len(proxies)} proxy sống vào file: {out_file.resolve().as_posix()}")
            else:
                print("⚠️ Không tìm thấy proxy khả dụng vào lúc này.")

        asyncio.run(refresh())


def cmd_chat(_args: argparse.Namespace) -> None:
    print("=" * 75)
    print("🤖 THREADS AI CHATBOT - TRỢ LÝ TÌM KIẾM THẢO LUẬN & REVIEW THREADS")
    print("=" * 75)
    print("💡 Hãy nhập bất kỳ câu hỏi hoặc nhu cầu tìm kiếm tự nhiên nào.")
    print("   Ví dụ: 'tôi muốn tìm kiếm các địa điểm du lịch ít người biết'")
    print("   Ví dụ: 'quán cafe vintage có đàn piano acoustic ở Sài Gòn'")
    print("   (Gõ 'exit' hoặc 'quit' để thoát)\n")
    while True:
        try:
            user_input = input("💬 Bạn: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Tạm biệt bạn!")
            break
        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q", "thoat"):
            print("👋 Tạm biệt bạn!")
            break

        asyncio.run(execute_pipeline(custom_query=user_input))
        print("\n" + "-" * 75)
        print("💡 Bạn có muốn tìm kiếm thêm câu hỏi nào khác không? (gõ câu hỏi tiếp theo hoặc 'exit' để thoát)\n")


def cmd_test(_args: argparse.Namespace) -> None:
    print("🧪 Đang thực thi bộ kiểm thử tự động pytest...")
    ret = subprocess.run([sys.executable, "-m", "pytest", "-o", "pythonpath=src", "-q"], cwd=REPO_ROOT)
    sys.exit(ret.returncode)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Meta Threads Scraper - Unified Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="subcommand", help="Lệnh chức năng")

    # 1. Subcommand: run / crawl
    p_run = subparsers.add_parser("run", aliases=["crawl"], help="Chạy cào dữ liệu & phân tích AI")
    p_run.add_argument("positional_query", nargs="?", default=None, help="Từ khóa tìm kiếm")
    p_run.add_argument("--query", "-q", dest="query", default=None, help="Chỉ định từ khóa tìm kiếm")
    p_run.set_defaults(func=cmd_run)

    # 2. Subcommand: chat / ask / bot (Interactive Chatbot Mode)
    p_chat = subparsers.add_parser("chat", aliases=["ask", "bot"], help="Chế độ Chatbot trò chuyện tương tác tự nhiên")
    p_chat.set_defaults(func=cmd_chat)

    # 3. Subcommand: login
    p_login = subparsers.add_parser("login", help="Quản lý phiên đăng nhập Threads")
    p_login.add_argument("--manual", "-m", action="store_true", help="Mở cửa sổ trình duyệt đăng nhập thủ công")
    p_login.add_argument("--headed", action="store_true", help="Hiển thị trình duyệt khi tự động đăng nhập")
    p_login.set_defaults(func=cmd_login)

    # 4. Subcommand: proxy
    p_proxy = subparsers.add_parser("proxy", help="Quản lý và kiểm tra proxy miễn phí")
    p_proxy.add_argument("--check", "-c", action="store_true", help="Kiểm tra proxy của các tài khoản hiện tại")
    p_proxy.add_argument("--auto-fix", action="store_true", help="Tự động thay thế proxy nếu bị chết")
    p_proxy.add_argument("--limit", "-l", type=int, default=15, help="Số lượng proxy sống cần làm mới")
    p_proxy.set_defaults(func=cmd_proxy)

    # 5. Subcommand: test
    p_test = subparsers.add_parser("test", help="Chạy bộ kiểm thử tự động pytest")
    p_test.set_defaults(func=cmd_test)

    # Hỗ trợ chạy trực tiếp: `python main.py "từ khóa"` hoặc `python main.py`
    # Nếu đối số đầu tiên không phải là subcommand hợp lệ, xử lý như lệnh run
    known_subcommands = {"run", "crawl", "chat", "ask", "bot", "login", "proxy", "test", "-h", "--help"}
    raw_args = sys.argv[1:]

    if not raw_args:
        # Mặc định chạy pipeline với config.py
        asyncio.run(execute_pipeline())
        return

    first_arg = raw_args[0]
    if first_arg not in known_subcommands and not first_arg.startswith("-"):
        # Người dùng truyền thẳng câu hỏi tự nhiên: python main.py "tôi muốn tìm kiếm..."
        asyncio.run(execute_pipeline(custom_query=first_arg))
        return

    if first_arg in ("--query", "-q"):
        # Người dùng truyền cờ query trực tiếp: python main.py --query "quán cafe"
        parsed = parser.parse_args(["run"] + raw_args)
        parsed.func(parsed)
        return

    args = parser.parse_args(raw_args)
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
