"""Cấu hình chung cho các script test nguồn paper.

Bạn có thể sửa trực tiếp các hằng số bên dưới. API key không đặt trong file
này mà được đọc từ .env để tránh commit nhầm secret.
"""

from __future__ import annotations

import os
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

# ---------- Cấu hình tìm kiếm dễ chỉnh ----------
DEFAULT_QUERY = "retrieval augmented generation"
DEFAULT_LIMIT = 3
DEFAULT_TIMEOUT_SECONDS = 25.0
# Tổng số attempt cho mỗi HTTP request: lần đầu + đúng 1 lần retry.
REQUEST_ATTEMPTS = 2
SAVE_RESULTS_BY_DEFAULT = True
OUTPUT_DIR = BASE_DIR / "results"
PAPER_SCHEMA_VERSION = "1.1.0"

# Embedding SPECTER2 hữu ích cho reranking nhưng làm JSON lớn đáng kể.
# Bật khi muốn thử semantic reranking ở bước hai, không cần cho search cơ bản.
SEMANTIC_SCHOLAR_INCLUDE_EMBEDDING = False

# ---------- Endpoint của từng nguồn ----------
SEMANTIC_SCHOLAR_URL = "https://api.semanticscholar.org/graph/v1/paper/search"
ARXIV_URL = "https://export.arxiv.org/api/query"
OPENALEX_URL = "https://api.openalex.org/works"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# ---------- AI query planner / paper assessor ----------
# `groq` là mặc định. Có thể đặt LLM_PROVIDER=openrouter trong .env để quay lại client cũ.
DEFAULT_LLM_PROVIDER = "groq"
GROQ_TASK_MODELS = {
    # GPT-OSS 20B cho strict JSON ổn định; Compound để cuối vì không cần built-in tools.
    "plan_paper_search": (
        "openai/gpt-oss-20b",
        "qwen/qwen3.6-27b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "groq/compound-mini",
        "groq/compound",
    ),
    # Qwen 3.6 mạnh về đa ngôn ngữ/semantic; 20B compact là fallback đầu tiên.
    "rerank_papers": (
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "groq/compound-mini",
        "groq/compound",
    ),
    # GPT-OSS 20B chỉ dùng 3.6B active và hỗ trợ strict JSON Schema.
    "enrich_papers": (
        "openai/gpt-oss-20b",
        "qwen/qwen3.6-27b",
        "qwen/qwen3.8-27b",
        "openai/gpt-oss-120b",
        "groq/compound-mini",
        "groq/compound",
    ),
}
GROQ_MODEL_LIMITS = {
    "groq/compound": {"rpm": 30, "rpd": 250, "tpm": 70000, "tpd": None},
    "groq/compound-mini": {"rpm": 30, "rpd": 250, "tpm": 70000, "tpd": None},
    "openai/gpt-oss-20b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200000},
    "openai/gpt-oss-120b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200000},
    "qwen/qwen3.6-27b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200000},
    "qwen/qwen3.8-27b": {"rpm": 30, "rpd": 1000, "tpm": 8000, "tpd": 200000},
}
GROQ_STRICT_JSON_MODELS = {"openai/gpt-oss-20b", "openai/gpt-oss-120b"}
GROQ_RATE_LIMIT_UTILIZATION = 0.80
GROQ_RATE_LIMIT_WINDOW_SECONDS = 60.0
GROQ_REQUEST_INTERVAL_MARGIN_SECONDS = 0.15
GROQ_TASK_MAX_COMPLETION_TOKENS = {
    "plan_paper_search": 1200,
    "rerank_papers": 1500,
    "enrich_papers": 1800,
}
GROQ_MODEL_MAX_COMPLETION_TOKENS = {
    # Free tier hiện có OTPM riêng 1K cho Qwen; giữ 10% headroom.
    "qwen/qwen3.6-27b": 900,
    "qwen/qwen3.8-27b": 900,
    "openai/gpt-oss-20b": 1800,
    "openai/gpt-oss-120b": 1800,
    "groq/compound-mini": 1600,
    "groq/compound": 1600,
}
OPENROUTER_MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
OPENROUTER_FALLBACK_MODEL = "openrouter/free"
OPENROUTER_DEFAULT_REFERER = "http://localhost"
OPENROUTER_APP_CATEGORIES = "personal-agent"
LLM_TIMEOUT_SECONDS = 35.0
# Tổng số attempt trên mỗi model: lần đầu + đúng 1 lần retry. Sau đó mới fallback model.
LLM_ATTEMPTS = 2
OPENROUTER_FREE_MODEL_MAX_TRIES = 0
OPENROUTER_MIN_CONTEXT_LENGTH = 32768
OPENROUTER_MODEL_CATALOG_TIMEOUT_SECONDS = 25.0
OPENROUTER_MODEL_CATALOG_TTL_SECONDS = 6 * 60 * 60
OPENROUTER_MODEL_CATALOG_CACHE = BASE_DIR / "results" / "cache" / "openrouter_free_models.json"
ENABLE_LLM_CACHE = True
LLM_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60
LLM_CACHE_DIR = BASE_DIR / "results" / "cache" / "llm"

# ---------- Retrieval: số query và số paper của từng nguồn ----------
MAX_QUERY_VARIANTS = 3
MAX_TERMS_PER_CONCEPT = 3
SEMANTIC_SCHOLAR_RESULTS_PER_QUERY = 15
ARXIV_RESULTS_PER_QUERY = 40
OPENALEX_LEXICAL_RESULTS_PER_QUERY = 20
OPENALEX_SEMANTIC_RESULTS_PER_QUERY = 20
SOURCE_MAX_CANDIDATES = {
    "semantic_scholar": 45,
    "arxiv": 40,
    "openalex": 40,
}
# Giữ để tương thích CLI/script cũ; pipeline mới ưu tiên quota riêng ở trên.
RESULTS_PER_QUERY = 20
MAX_CANDIDATES_PER_SOURCE = 45
MAX_TOTAL_CANDIDATES = 120
PRE_RANK_LIMIT = 30
AI_RERANK_LIMIT = 20
AI_RERANK_BATCH_SIZE = 3
AI_ENRICH_LIMIT = 10
AI_ENRICH_BATCH_SIZE = 5
AI_ENRICH_ABSTRACT_MAX_CHARS = 2400
RESULT_LIMIT = 10
MAX_LLM_ASSESS_PAPERS = AI_ENRICH_LIMIT
REQUIRE_ABSTRACT_BY_DEFAULT = True
OPENALEX_ENABLE_SEMANTIC_SEARCH = True
# Khoảng tối thiểu giữa MỌI request/attempt. Margin được cộng vào base để tránh
# request chạm đúng biên rate limit do sai số scheduler/network.
SOURCE_REQUEST_INTERVAL_SECONDS = {
    "semantic_scholar": 1.0,  # API key introductory limit: 1 request/second.
    "arxiv": 3.0,             # arXiv asks clients to wait 3 seconds.
    "openalex": 1.0,          # Conservative because semantic search is 1 request/second.
}
SOURCE_RATE_LIMIT_SAFETY_MARGIN_SECONDS = {
    "semantic_scholar": 0.50,
    "arxiv": 0.50,
    "openalex": 0.50,
}
MAX_RETRY_DELAY_SECONDS = 90.0
RETRY_SAFETY_MARGIN_SECONDS = 0.50
RETRY_MIN_DELAY_BY_SOURCE = {
    "semantic_scholar": 5.0,
    "openalex": 2.0,
    "arxiv": 5.0,
}
PRESERVE_RAW_SOURCE_DATA = True
INCLUDE_SOURCE_RECORDS_IN_OUTPUT = False
INCLUDE_STAGE_RANKINGS_IN_OUTPUT = True

# Preset chỉ đặt default; mọi giá trị vẫn có thể override bằng CLI hoặc run_pipeline().
DEFAULT_SEARCH_DEPTH = "quick"
SEARCH_DEPTH_PRESETS = {
    "quick": {
        "request_limits": {
            "semantic_scholar": SEMANTIC_SCHOLAR_RESULTS_PER_QUERY,
            "arxiv": ARXIV_RESULTS_PER_QUERY,
            "openalex_lexical": OPENALEX_LEXICAL_RESULTS_PER_QUERY,
            "openalex_semantic": OPENALEX_SEMANTIC_RESULTS_PER_QUERY,
        },
        "source_caps": SOURCE_MAX_CANDIDATES,
        "max_candidates": MAX_TOTAL_CANDIDATES,
        "pre_rank_limit": PRE_RANK_LIMIT,
        "ai_rerank_limit": AI_RERANK_LIMIT,
        "ai_enrich_limit": AI_ENRICH_LIMIT,
        "result_limit": RESULT_LIMIT,
    },
    "standard": {
        "request_limits": {
            "semantic_scholar": 40,
            "arxiv": 100,
            "openalex_lexical": 50,
            "openalex_semantic": 50,
        },
        "source_caps": {"semantic_scholar": 80, "arxiv": 100, "openalex": 100},
        "max_candidates": 250,
        "pre_rank_limit": 80,
        "ai_rerank_limit": 30,
        "ai_enrich_limit": 12,
        "result_limit": 15,
    },
}

# Sau số request tối thiểu, query mở rộng chỉ chạy tiếp khi chưa đủ candidate mới.
ENABLE_ADAPTIVE_RETRIEVAL = True
ADAPTIVE_MIN_REQUESTS_BY_SOURCE = {
    "semantic_scholar": 2,
    "openalex": 2,
    "arxiv": 1,
}
ADAPTIVE_TARGET_SOURCE_CAP_RATIO = 0.60
ADAPTIVE_MIN_MARGINAL_UNIQUE_RATIO = 0.10

# ---------- Ranking: mọi trọng số đều có thể chỉnh tại đây ----------
# Mỗi mapping sẽ được code tự normalize, vì vậy không bắt buộc tổng đúng bằng 1.
RRF_K = 60
SOURCE_RRF_WEIGHTS = {
    "semantic_scholar": 1.0,
    "openalex": 1.0,
    "arxiv": 1.0,
}
QUERY_MATCH_WEIGHTS = {
    "source_rrf": 0.45,
    "text_match": 0.45,
    "query_coverage": 0.10,
}
TEXT_MATCH_WEIGHTS = {
    "concept_coverage": 0.50,
    "title_coverage": 0.30,
    "abstract_coverage": 0.20,
}
FINAL_SCORE_WEIGHTS = {
    "balanced": {"query_match": 0.60, "paper_quality": 0.40},
    "latest": {"query_match": 0.55, "paper_quality": 0.45},
    "seminal": {"query_match": 0.50, "paper_quality": 0.50},
    "evidence_review": {"query_match": 0.55, "paper_quality": 0.45},
}
PAPER_QUALITY_WEIGHTS = {
    "balanced": {
        "impact": 0.28, "citation_velocity": 0.15, "recency": 0.18,
        "publication": 0.12, "access": 0.08, "source_agreement": 0.02,
        "metadata_completeness": 0.09,
    },
    "latest": {
        "impact": 0.12, "citation_velocity": 0.12, "recency": 0.45,
        "publication": 0.08, "access": 0.06, "source_agreement": 0.02,
        "metadata_completeness": 0.09,
    },
    "seminal": {
        "impact": 0.50, "citation_velocity": 0.15, "recency": 0.03,
        "publication": 0.12, "access": 0.04, "source_agreement": 0.02,
        "metadata_completeness": 0.08,
    },
    "evidence_review": {
        "impact": 0.30, "citation_velocity": 0.12, "recency": 0.08,
        "publication": 0.18, "access": 0.06, "source_agreement": 0.02,
        "metadata_completeness": 0.14,
    },
}
IMPACT_SIGNAL_WEIGHTS = {
    "citation_count": 0.25,
    "citation_percentile": 0.35,
    "fwci": 0.20,
    "influential_citations": 0.20,
}
RECENCY_HALF_LIFE_YEARS = {
    "balanced": 5.0,
    "latest": 1.5,
    "seminal": 12.0,
    "evidence_review": 6.0,
}
RECENT_CITATION_WINDOW_YEARS = 3
PUBLICATION_TYPE_SCORES = {
    "review": 1.0,
    "journalarticle": 0.90,
    "article": 0.90,
    "conference": 0.90,
    "book": 0.75,
    "preprint": 0.55,
    "unknown": 0.50,
}
ACCESS_SCORES = {
    "direct_pdf": 1.0,
    "open_access": 0.75,
    "metadata_only": 0.25,
}
METADATA_COMPLETENESS_FIELDS = (
    "title", "abstract", "authors", "year", "venue", "doi", "url", "pdf_url",
)

# AI chỉ là một signal; với openrouter/free không nên để trọng số quá cao.
AI_RERANK_WEIGHT = 0.25
AI_RERANK_MIN_CONFIDENCE = 0.30
AI_RERANK_CROSS_MODEL_PENALTY = 0.50
AI_RERANK_ABSTRACT_MAX_CHARS = 1400
AI_RERANK_SIGNAL_WEIGHTS = {
    "relevance": 0.55,
    "intent_match": 0.30,
    "method_match": 0.15,
}

# Không cố lấp đủ result_limit bằng paper yếu. Paper bị loại nếu AI tự tin rằng
# không liên quan, hoặc nếu cả text match và AI relevance đều thấp.
ENABLE_RELEVANCE_GATE = True
MIN_TEXT_MATCH_SCORE = 0.10
MIN_AI_RELEVANCE_SCORE = 0.25
AI_RELEVANCE_GATE_MIN_CONFIDENCE = 0.60
MIN_REQUIRED_CONCEPT_COVERAGE = 1.0
AI_REQUIRED_CONCEPT_OVERRIDE_SCORE = 0.70

# Greedy MMR bằng token similarity, không cần embedding cho MVP.
ENABLE_DIVERSITY_RERANK = True
DIVERSITY_LAMBDA = 0.82
DIVERSITY_POOL_LIMIT = 30
DIVERSITY_TEXT_MAX_CHARS = 2500

# ---------- Cache retrieval ----------
ENABLE_QUERY_CACHE = True
QUERY_CACHE_TTL_SECONDS = 24 * 60 * 60
QUERY_CACHE_TTL_BY_SOURCE = {
    "semantic_scholar": 6 * 60 * 60,
    "openalex": 6 * 60 * 60,
    "arxiv": 24 * 60 * 60,
}
QUERY_CACHE_DIR = BASE_DIR / "results" / "cache"

USER_AGENT_NAME = "CyVerse-AI-Research-Smoke-Test/1.0"


class ConfigError(RuntimeError):
    pass


def load_env_file(path: Path = ENV_FILE) -> list[str]:
    """Nạp .env nhưng không ghi đè biến môi trường đã có của hệ điều hành."""
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError as exc:
        raise ConfigError(f"Không đọc được file env {path}: {exc}") from exc

    loaded: list[str] = []
    for line_number, original_line in enumerate(lines, start=1):
        line = original_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        key = key.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ConfigError(f"Sai cú pháp .env tại {path}:{line_number}")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        else:
            value = re.split(r"\s+#", value, maxsplit=1)[0].rstrip()
        if key not in os.environ:
            os.environ[key] = value
            loaded.append(key)
    return loaded


LOADED_ENV_NAMES = load_env_file()


def secret(name: str) -> str | None:
    """Lấy secret đã nạp, trả None nếu giá trị đang để trống."""
    return os.getenv(name) or None


def llm_provider() -> str:
    value = (secret("LLM_PROVIDER") or DEFAULT_LLM_PROVIDER).strip().casefold()
    return value if value in {"groq", "openrouter"} else DEFAULT_LLM_PROVIDER


def llm_api_key() -> str | None:
    return secret("GROQ_API_KEY") if llm_provider() == "groq" else secret("OPENROUTER_API_KEY")


def llm_primary_model(tool_name: str) -> str:
    if llm_provider() == "groq":
        models = GROQ_TASK_MODELS.get(tool_name) or GROQ_TASK_MODELS["enrich_papers"]
        return models[0]
    return OPENROUTER_MODEL


def contact_email() -> str | None:
    return secret("ARXIV_CONTACT_EMAIL") or secret("OPENALEX_MAILTO")


def user_agent() -> str:
    email = contact_email()
    return f"{USER_AGENT_NAME} ({email})" if email else USER_AGENT_NAME
