"""
Meta Threads Scraper - Modular Architecture
Cung cấp các module chuyên biệt: Cấu hình, Xác thực, Quản lý Proxy, Trình cào dữ liệu, AI Engine và Lưu trữ.
"""

from .config import load_app_config
from .proxy import get_healthy_proxies, test_proxy_against_threads, format_playwright_proxy
from .auth import auto_login_all_accounts, dismiss_popups
from .ai_engine import expand_search_query, pre_filter_posts, curate_post
from .crawler import WorkerPool, scrape_single_keyword, scrape_post_comments, format_post
from .storage import save_pipeline_run
from .pipeline import execute_pipeline

__all__ = [
    "load_app_config",
    "get_healthy_proxies",
    "test_proxy_against_threads",
    "format_playwright_proxy",
    "auto_login_all_accounts",
    "dismiss_popups",
    "expand_search_query",
    "pre_filter_posts",
    "curate_post",
    "WorkerPool",
    "scrape_single_keyword",
    "scrape_post_comments",
    "format_post",
    "save_pipeline_run",
    "execute_pipeline",
]
