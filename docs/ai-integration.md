# AI integration

Các tính năng AI gọi qua `AIService` và provider adapter. Prompt dùng chung nằm trong `app/ai/prompts/shared`; prompt riêng được đặt cùng module tool.

Research Tool hỗ trợ Groq và OpenRouter qua structured JSON completion. Planner và reranker có
deterministic fallback; final enrichment bắt buộc response hợp lệ, summary tiếng Việt có dấu và
`why_read_vi` gồm 1–3 phần tử. Title/abstract từ nguồn ngoài được xem là untrusted data trong prompt.
Model list, provider, endpoint và các thông số vận hành AI Research nằm trong typed config tại
`apps/backend/src/app/tools/research/config.py`. Secret chỉ nằm trong backend environment và không
được expose ra frontend.
