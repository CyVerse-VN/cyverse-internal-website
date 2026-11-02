from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from modules.config import load_app_config
from modules.proxy import format_playwright_proxy
from modules.storage import save_pipeline_run
from modules.crawler import extract_hierarchical_comments
from modules.ai_engine import format_comments_hierarchy


class ModulesTests(unittest.TestCase):
    def test_format_playwright_proxy(self) -> None:
        p1 = format_playwright_proxy("http://127.0.0.1:8080")
        self.assertEqual(p1, {"server": "http://127.0.0.1:8080"})

        p2 = format_playwright_proxy("http://user:pass@127.0.0.1:8080")
        self.assertEqual(p2, {
            "server": "http://127.0.0.1:8080",
            "username": "user",
            "password": "pass",
        })

        p3 = format_playwright_proxy("")
        self.assertIsNone(p3)

    def test_load_app_config_env_priority(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            env_file = root / ".env"
            env_file.write_text("THREADS_USERNAME=env_user\nTHREADS_PASSWORD=env_pass\n", encoding="utf-8")
            cfg_file = root / "config.json"
            cfg_file.write_text(json.dumps({"max_posts_per_keyword": 42}), encoding="utf-8")

            cfg = load_app_config(config_path=cfg_file, env_path=env_file, accounts_path=root / "acc.json")
            self.assertEqual(cfg["max_posts_per_keyword"], 42)
            self.assertTrue(any(a["username"] == "env_user" for a in cfg["accounts"]))

    def test_load_app_config_py_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            py_file = root / "config.py"
            py_file.write_text(
                "SEARCH_QUERIES = ['cafe chill']\n"
                "MAX_POSTS_PER_KEYWORD = 99\n"
                "BLOCK_MEDIA = False\n"
                "COMMENTS_ENABLED = True\n"
                "MAX_COMMENTS_PER_POST = 50\n",
                encoding="utf-8",
            )
            cfg = load_app_config(config_path=py_file, env_path=root / ".env", accounts_path=root / "acc.json")
            self.assertEqual(cfg["search_queries"], ["cafe chill"])
            self.assertEqual(cfg["max_posts_per_keyword"], 99)
            self.assertFalse(cfg["performance"]["block_media"])
            self.assertEqual(cfg["comments"]["max_comments_per_post"], 50)

    def test_save_pipeline_run_structure(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            posts = [{"post_id": "p1", "text": "hello"}]
            curated = [{"post_id": "p1", "is_relevant": True}]
            output_cfg = {
                "base_dir": "out",
                "runs_dir": "out/runs",
                "json_file": "out/latest_posts.json",
                "curated_file": "out/latest_curated.json",
            }

            res = save_pipeline_run(
                all_posts=posts,
                curated_posts=curated,
                topics=["test topic"],
                total_comments=5,
                duration_seconds=12.3,
                output_cfg=output_cfg,
                repo_root=root,
            )

            self.assertTrue(res["run_dir"].is_dir())
            self.assertTrue(res["summary"].is_file())
            self.assertTrue(res["posts"].is_file())
            self.assertTrue(res["curated"].is_file())
            self.assertTrue(res["latest_posts"].is_file())
            self.assertTrue(res["latest_curated"].is_file())

            summary = json.loads(res["summary"].read_text(encoding="utf-8"))
            self.assertEqual(summary["metadata"]["stats"]["total_posts"], 1)
            self.assertEqual(summary["metadata"]["stats"]["total_comments"], 5)

    def test_extract_hierarchical_comments(self) -> None:
        raw_payload = [
            {
                "data": {
                    "node": {
                        "posts": {
                            "edges": [
                                {
                                    "node": {
                                        "pk": "c1",
                                        "user": {"username": "user_a"},
                                        "caption": {"text": "Quán ngon lắm"},
                                        "like_count": 5,
                                        "text_post_app_info": {"reply_level": 1, "is_reply": True, "reply_to_author": {"username": "root"}},
                                    }
                                },
                                {
                                    "node": {
                                        "pk": "c2",
                                        "user": {"username": "user_b"},
                                        "caption": {"text": "Giá bao nhiêu vậy bạn?"},
                                        "like_count": 1,
                                        "text_post_app_info": {"reply_level": 2, "is_reply": True, "reply_to_author": {"username": "user_a"}},
                                    }
                                },
                                {
                                    "node": {
                                        "pk": "c3",
                                        "user": {"username": "user_a"},
                                        "caption": {"text": "Tầm 50k nha"},
                                        "like_count": 2,
                                        "text_post_app_info": {"reply_level": 3, "is_reply": True, "reply_to_author": {"username": "user_b"}},
                                    }
                                },
                                {
                                    "node": {
                                        "pk": "c4",
                                        "user": {"username": "user_c"},
                                        "caption": {"text": "Mình cũng vote quán này"},
                                        "like_count": 0,
                                        "text_post_app_info": {"reply_level": 1, "is_reply": True, "reply_to_author": {"username": "root"}},
                                    }
                                },
                            ]
                        }
                    }
                }
            }
        ]

        extracted = extract_hierarchical_comments(raw_payload)
        self.assertEqual(len(extracted), 4)

        # Check comment 1
        self.assertEqual(extracted[0]["id"], "c1")
        self.assertEqual(extracted[0]["depth"], 1)
        self.assertIsNone(extracted[0]["parent_id"])
        self.assertEqual(extracted[0]["reply_to_username"], "root")

        # Check comment 2 (reply to c1)
        self.assertEqual(extracted[1]["id"], "c2")
        self.assertEqual(extracted[1]["depth"], 2)
        self.assertEqual(extracted[1]["parent_id"], "c1")
        self.assertEqual(extracted[1]["reply_to_username"], "user_a")

        # Check comment 3 (reply to c2)
        self.assertEqual(extracted[2]["id"], "c3")
        self.assertEqual(extracted[2]["depth"], 3)
        self.assertEqual(extracted[2]["parent_id"], "c2")
        self.assertEqual(extracted[2]["reply_to_username"], "user_b")

        # Check comment 4 (new root comment at depth 1)
        self.assertEqual(extracted[3]["id"], "c4")
        self.assertEqual(extracted[3]["depth"], 1)
        self.assertIsNone(extracted[3]["parent_id"])

    def test_format_comments_hierarchy(self) -> None:
        comments = [
            {"username": "user_a", "text": "Quán ngon lắm", "depth": 1, "like_count": 5},
            {"username": "user_b", "text": "Giá bao nhiêu?", "depth": 2, "reply_to_username": "user_a", "like_count": 0},
        ]
        formatted = format_comments_hierarchy(comments)
        self.assertIn("• [@user_a] (Cấp 1): Quán ngon lắm [❤️ 5]", formatted)
        self.assertIn("└── [@user_b] (Cấp 2, trả lời @user_a): Giá bao nhiêu?", formatted)


if __name__ == "__main__":
    unittest.main()
