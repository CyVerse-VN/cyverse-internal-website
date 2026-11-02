import os, httpx, json, re, sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from modules.config import load_app_config
from modules.ai_engine import curate_post

cfg = load_app_config()
post_text = 'KHÔNG BIẾT CÓ AI GIỐNG TAO KHÔNG, CỨ MỖI LẦN CUỘC SỐNG BẮT ĐẦU ỔN ĐỊNH LÀ TAO LẠI LO. CẢM GIÁC NHƯ CUỘC ĐỜI ĐANG CHUẨN BỊ CHO MÌNH MỘT CÚ PLOT TWIST VẬY. =))))'
comments = [
    {'username': '_nanaiu.__', 'text': 'má t8-9 của t khá trvia nên t rất chill, qua t10 nó dập kh còn cgi lun 😇', 'depth': 1, 'reply_to_username': 'superflixx97'},
    {'username': 'dobt.tengi', 'text': 'Và cú plot twist đến thật :)))', 'depth': 1, 'reply_to_username': 'superflixx97'},
]

key = cfg.get("groq_api_key")
res = curate_post(
    post_text=post_text,
    search_queries=['tâm sự cuộc sống'],
    comments=comments,
    model=cfg.get('groq', {}).get('model', 'qwen/qwen3.8-27b'),
    api_key=key
)
print("Curate_post result:")
print(json.dumps(res, ensure_ascii=False, indent=2))
