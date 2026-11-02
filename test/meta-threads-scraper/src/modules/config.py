from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

# Xác định thư mục gốc của repository
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def load_env_file(env_path: Path = REPO_ROOT / ".env") -> dict[str, str]:
    """Tự động nạp các biến môi trường từ file .env vào os.environ."""
    env_vars: dict[str, str] = {}
    if not env_path.is_file():
        return env_vars

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key:
                        env_vars[key] = val
                        os.environ[key] = val
    except Exception as exc:
        print(f"⚠️ Lỗi đọc file .env ({exc})")

    return env_vars


def load_json_file(file_path: Path, default: Any = None) -> Any:
    """Đọc an toàn một file JSON UTF-8."""
    if not file_path.is_file():
        return default
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print(f"⚠️ Không đọc được file JSON {file_path.name} ({exc})")
        return default


import runpy


def load_py_config(file_path: Path) -> dict[str, Any]:
    """Nạp cấu hình từ file Python (.py) chứa các hằng số."""
    if not file_path.is_file():
        return {}

    try:
        cfg_vars = runpy.run_path(str(file_path))
    except Exception as exc:
        print(f"⚠️ Lỗi nạp file cấu hình Python {file_path.name} ({exc})")
        return {}

    cfg: dict[str, Any] = {}
    if "to_dict" in cfg_vars and callable(cfg_vars["to_dict"]):
        try:
            cfg = cfg_vars["to_dict"]()
        except Exception as exc:
            print(f"⚠️ Lỗi gọi to_dict() trong {file_path.name} ({exc})")

    # Ánh xạ từ các hằng số viết hoa để đảm bảo nhận diện mọi chỉnh sửa trực tiếp của người dùng
    if "SEARCH_QUERIES" in cfg_vars:
        cfg["search_queries"] = cfg_vars["SEARCH_QUERIES"]
    if "MAX_POSTS_PER_KEYWORD" in cfg_vars:
        cfg["max_posts_per_keyword"] = cfg_vars["MAX_POSTS_PER_KEYWORD"]

    perf = cfg.setdefault("performance", {})
    if "BLOCK_MEDIA" in cfg_vars:
        perf["block_media"] = cfg_vars["BLOCK_MEDIA"]

    auth = cfg.setdefault("auth", {})
    if "AUTH_ENABLED" in cfg_vars:
        auth["enabled"] = cfg_vars["AUTH_ENABLED"]
    if "SESSION_FILE" in cfg_vars:
        auth["session_file"] = cfg_vars["SESSION_FILE"]
    if "SESSIONS_DIR" in cfg_vars:
        auth["sessions_dir"] = cfg_vars["SESSIONS_DIR"]

    if "MAX_ACCOUNTS_TO_USE" in cfg_vars:
        cfg["max_accounts_to_use"] = cfg_vars["MAX_ACCOUNTS_TO_USE"]
    if "ACTIVE_ACCOUNTS" in cfg_vars:
        cfg["active_accounts"] = cfg_vars["ACTIVE_ACCOUNTS"]
    if "ACCOUNT_PROXY_TOGGLE" in cfg_vars:
        cfg["account_proxy_toggle"] = cfg_vars["ACCOUNT_PROXY_TOGGLE"]

    proxy = cfg.setdefault("proxy", {})
    if "PROXY_ENABLED" in cfg_vars:
        proxy["enabled"] = cfg_vars["PROXY_ENABLED"]
    if "PROXY_FILE" in cfg_vars:
        proxy["proxy_file"] = cfg_vars["PROXY_FILE"]
    if "ACCOUNT_PROXY_TOGGLE" in cfg_vars:
        proxy["account_proxy_toggle"] = cfg_vars["ACCOUNT_PROXY_TOGGLE"]

    pre_filter = cfg.setdefault("pre_filter", {})
    if "PRE_FILTER_ENABLED" in cfg_vars:
        pre_filter["enabled"] = cfg_vars["PRE_FILTER_ENABLED"]
    if "PRE_FILTER_BATCH_SIZE" in cfg_vars:
        pre_filter["batch_size"] = cfg_vars["PRE_FILTER_BATCH_SIZE"]
    if "PRE_FILTER_STRICTNESS" in cfg_vars:
        pre_filter["strictness"] = cfg_vars["PRE_FILTER_STRICTNESS"]

    comments = cfg.setdefault("comments", {})
    if "COMMENTS_ENABLED" in cfg_vars:
        comments["enabled"] = cfg_vars["COMMENTS_ENABLED"]
    if "MAX_POSTS_TO_SCRAPE_COMMENTS" in cfg_vars:
        comments["max_posts_to_scrape"] = cfg_vars["MAX_POSTS_TO_SCRAPE_COMMENTS"]
    if "MAX_COMMENTS_PER_POST" in cfg_vars:
        comments["max_comments_per_post"] = cfg_vars["MAX_COMMENTS_PER_POST"]
    if "MIN_REPLIES_THRESHOLD" in cfg_vars:
        comments["min_replies_threshold"] = cfg_vars["MIN_REPLIES_THRESHOLD"]

    anti_ban = cfg.setdefault("anti_ban", {})
    if "MIN_DELAY_SECONDS" in cfg_vars:
        anti_ban["min_delay_seconds"] = cfg_vars["MIN_DELAY_SECONDS"]
    if "MAX_DELAY_SECONDS" in cfg_vars:
        anti_ban["max_delay_seconds"] = cfg_vars["MAX_DELAY_SECONDS"]
    if "RANDOM_MOUSE_MOVEMENT" in cfg_vars:
        anti_ban["random_mouse_movement"] = cfg_vars["RANDOM_MOUSE_MOVEMENT"]

    groq = cfg.setdefault("groq", {})
    if "GROQ_MODEL" in cfg_vars:
        groq["model"] = cfg_vars["GROQ_MODEL"]
    if "ENABLE_AI_FILTERING" in cfg_vars:
        groq["enable_ai_filtering"] = cfg_vars["ENABLE_AI_FILTERING"]
    if "KEYWORDS_PER_QUERY" in cfg_vars:
        groq["keywords_per_query"] = cfg_vars["KEYWORDS_PER_QUERY"]

    out = cfg.setdefault("output", {})
    if "BASE_OUTPUT_DIR" in cfg_vars:
        out["base_dir"] = cfg_vars["BASE_OUTPUT_DIR"]
    if "RUNS_OUTPUT_DIR" in cfg_vars:
        out["runs_dir"] = cfg_vars["RUNS_OUTPUT_DIR"]
    if "LATEST_POSTS_FILE" in cfg_vars:
        out["json_file"] = cfg_vars["LATEST_POSTS_FILE"]
    if "LATEST_TXT_FILE" in cfg_vars:
        out["txt_file"] = cfg_vars["LATEST_TXT_FILE"]
    if "LATEST_CURATED_FILE" in cfg_vars:
        out["curated_file"] = cfg_vars["LATEST_CURATED_FILE"]

    return cfg


def load_app_config(
    config_path: Path | None = None,
    env_path: Path = REPO_ROOT / ".env",
    accounts_path: Path = REPO_ROOT / "accounts.json",
) -> dict[str, Any]:
    """
    Nạp toàn bộ cấu hình hệ thống:
    1. Đọc các thông tin nhạy cảm (Credentials, API Keys) từ .env
    2. Đọc các tham số nghiệp vụ từ config.py (hoặc config.json nếu được chỉ định)
    3. Nạp danh sách tài khoản từ .env (ưu tiên bảo mật cao nhất) và accounts.json
    """
    load_env_file(env_path)

    default_config: dict[str, Any] = {
        "search_queries": ["địa điểm hẹn hò lãng mạn ở Sài Gòn"],
        "max_posts_per_keyword": 30,
        "max_accounts_to_use": -1,
        "active_accounts": [],
        "account_proxy_toggle": {},
        "performance": {"block_media": True},
        "auth": {
            "enabled": True,
            "session_file": "sessions/user_session.json",
            "sessions_dir": "sessions",
        },
        "proxy": {"enabled": False, "proxy_file": "proxies.txt", "account_proxy_toggle": {}},
        "pre_filter": {"enabled": False, "batch_size": 15, "strictness": "high"},
        "comments": {
            "enabled": True,
            "max_posts_to_scrape": 10,
            "max_comments_per_post": 25,
            "min_replies_threshold": 2,
        },
        "anti_ban": {
            "min_delay_seconds": 2.0,
            "max_delay_seconds": 4.0,
            "random_mouse_movement": True,
        },
        "groq": {
            "model": "qwen/qwen3.8-27b",
            "enable_ai_filtering": True,
            "keywords_per_query": 1,
        },
        "output": {
            "base_dir": "output",
            "runs_dir": "output/runs",
            "json_file": "output/threads_posts.json",
            "txt_file": "output/threads_posts.txt",
            "curated_file": "output/curated_places.json",
        },
    }

    if config_path is None:
        py_cfg = REPO_ROOT / "config.py"
        json_cfg = REPO_ROOT / "config.json"
        if py_cfg.is_file():
            config_path = py_cfg
        elif json_cfg.is_file():
            config_path = json_cfg
        else:
            config_path = py_cfg

    if config_path.suffix == ".py":
        user_cfg = load_py_config(config_path)
    else:
        user_cfg = load_json_file(config_path, default={})

    if isinstance(user_cfg, dict):
        for section, val in user_cfg.items():
            if isinstance(val, dict) and section in default_config and isinstance(default_config[section], dict):
                default_config[section].update(val)
            elif not section.startswith("_"):
                default_config[section] = val

    # 1. Nạp danh sách tài khoản từ .env hoặc accounts.json
    accounts: list[dict[str, Any]] = []

    # Ưu tiên tài khoản chính cấu hình trực tiếp trong .env (hỗ trợ cả THREADS_USERNAME_1 và THREADS_USERNAME)
    env_user = (os.getenv("THREADS_USERNAME_1") or os.getenv("THREADS_USERNAME", "")).strip()
    env_pass = (os.getenv("THREADS_PASSWORD_1") or os.getenv("THREADS_PASSWORD", "")).strip()
    env_proxy = (os.getenv("THREADS_PROXY_1") or os.getenv("THREADS_PROXY", "")).strip()

    if env_user and env_pass:
        accounts.append({
            "id": "acc_01",
            "username": env_user,
            "password": env_pass,
            "proxy": env_proxy,
            "enabled": True,
            "source": "env",
        })

    # Hỗ trợ thêm các tài khoản phụ từ .env (THREADS_USERNAME_2, THREADS_USERNAME_3,...)
    for idx in range(2, 10):
        u_env = os.getenv(f"THREADS_USERNAME_{idx}", "").strip()
        p_env = os.getenv(f"THREADS_PASSWORD_{idx}", "").strip()
        px_env = os.getenv(f"THREADS_PROXY_{idx}", "").strip()
        if u_env and p_env:
            accounts.append({
                "id": f"acc_{idx:02d}",
                "username": u_env,
                "password": p_env,
                "proxy": px_env,
                "enabled": True,
                "source": "env",
            })

    # Nạp bổ sung từ accounts.json nếu có
    acc_data = load_json_file(accounts_path, default={})
    if isinstance(acc_data, dict):
        raw_list = acc_data.get("accounts", [])
        if isinstance(raw_list, list):
            for acc in raw_list:
                if not isinstance(acc, dict):
                    continue
                aid = acc.get("id") or f"acc_{len(accounts) + 1:02d}"
                # Tránh trùng nếu đã nạp từ env
                if any(a["id"] == aid or a["username"] == acc.get("username") for a in accounts):
                    continue
                u = acc.get("username", "").strip()
                p = acc.get("password", "").strip()
                if u and not u.startswith("dien_username") and not u.startswith("ten_tai_khoan"):
                    accounts.append({
                        "id": aid,
                        "username": u,
                        "password": p,
                        "proxy": acc.get("proxy", "").strip(),
                        "enabled": acc.get("enabled", True),
                        "source": "accounts.json",
                    })

    proxy_toggle = default_config.get("account_proxy_toggle") or default_config.get("proxy", {}).get("account_proxy_toggle", {})
    global_proxy_enabled = default_config.get("proxy", {}).get("enabled", False)

    for acc in accounts:
        aid = acc.get("id", "").lower()
        if aid in proxy_toggle:
            acc["use_proxy"] = bool(proxy_toggle[aid])
        else:
            acc["use_proxy"] = global_proxy_enabled

    default_config["accounts"] = accounts
    default_config["repo_root"] = REPO_ROOT
    default_config["groq_api_key"] = os.getenv("GROQ_API_KEY", "").strip()

    return default_config
