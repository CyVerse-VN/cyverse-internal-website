# AI Research Paper Finder

Prototype tìm paper từ Semantic Scholar, arXiv và OpenAlex. Pipeline không cần database và chưa tải/đọc PDF; toàn bộ kết quả được lưu thành JSON để dễ kiểm tra.

Đọc [ARCHITECTURE.md](ARCHITECTURE.md) để xem sơ đồ và mô tả chi tiết toàn bộ luồng
từ prompt, truy vấn ba nguồn, chuẩn hóa/dedup/ranking đến JSON kết quả cuối.

Yêu cầu: Python 3.10+ và Internet. Không cần cài package ngoài.

## Thiết lập API key

Điền các giá trị có sẵn vào `.env` trong thư mục này:

```dotenv
SEMANTIC_SCHOLAR_API_KEY=
OPENALEX_API_KEY=
OPENALEX_MAILTO=
ARXIV_CONTACT_EMAIL=
LLM_PROVIDER=groq
GROQ_API_KEY=

# Chỉ cần nếu đổi LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=
OPENROUTER_HTTP_REFERER=
OPENROUTER_APP_TITLE=CyVerse AI Research Tool
```

Groq là LLM provider mặc định cho query planner, AI reranking và phần tóm tắt cuối:

- Query planner: `openai/gpt-oss-20b` với strict JSON Schema.
- AI reranker: `qwen/qwen3.6-27b` vì mạnh semantic/đa ngôn ngữ.
- Summary + why-read: `openai/gpt-oss-20b`; đây là MoE 20B nhưng chỉ 3.6B active và hỗ
  trợ strict JSON Schema.
- Fallback chỉ gồm Qwen, GPT-OSS và Compound. Prompt Guard, Safeguard, Whisper và Orpheus
  bị loại vì không phù hợp tác vụ.

Mỗi model có RPM/RPD/TPM/TPD trong `GROQ_MODEL_LIMITS`. Client chỉ dùng 80% quota, giữ
khoảng cách request theo RPM và đọc các header rate-limit của Groq để chờ token reset. Tóm
tắt chạy batch 5 paper, tức 20 paper chỉ cần 4 request khi model chính thành công. Có thể đổi
`AI_ENRICH_BATCH_SIZE`, giới hạn output hoặc danh sách fallback trong `config.py`.

OpenRouter vẫn được giữ làm provider tùy chọn: đặt `LLM_PROVIDER=openrouter` trong `.env`.

- arXiv không cần key.
- Email của OpenAlex/arXiv là tùy chọn, nhưng nên có để nhận diện client lịch sự.
- Không đặt API key trong `config.py` và không commit `.env`.
- Model/provider thực tế, token usage và thời gian chờ rate-limit được ghi trong JSON.

## Chạy pipeline

Từ thư mục gốc repository:

```powershell
python test/test-ai-research-tool/research_pipeline.py "Tìm paper mới về RAG giúp giảm hallucination trong medical LLM"
```

Kết quả mặc định: `test/test-ai-research-tool/results/research_pipeline.json`.

Hai preset mới:

```powershell
# Nhanh, mặc định: tối đa 120 raw → 30 pre-rank → 20 AI → 10 kết quả
python test/test-ai-research-tool/research_pipeline.py "AI agent memory" --search-depth quick

# Phủ rộng hơn: tối đa 250 raw → 80 pre-rank → 30 AI → 15 kết quả
python test/test-ai-research-tool/research_pipeline.py "AI agent memory" --search-depth standard
```

Retrieval thích nghi được bật mặc định: sau số request tối thiểu, query mở rộng sẽ được bỏ qua nếu nguồn đã đạt target unique candidate hoặc query vừa rồi tạo quá ít paper mới.

Ví dụ chủ động giới hạn từng nguồn và các tầng ranking:

```powershell
python test/test-ai-research-tool/research_pipeline.py "RAG giảm hallucination trong medical LLM" `
  --latest-years 2 `
  --s2-per-query 15 `
  --arxiv-per-query 30 `
  --openalex-lexical-per-query 20 `
  --openalex-semantic-per-query 20 `
  --max-candidates 100 `
  --pre-rank-limit 40 `
  --ai-rerank-limit 30 `
  --result-limit 20 `
  --output test/test-ai-research-tool/results/latest_rag.json
```

Các công tắc hữu ích:

```text
--per-query N                 Ghi đè cùng một limit cho mọi request/nguồn
--search-depth MODE           quick hoặc standard
--s2-per-query N              Paper mỗi query Semantic Scholar
--arxiv-per-query N           Paper cho query Boolean arXiv
--openalex-lexical-per-query N
--openalex-semantic-per-query N (API semantic tự chặn tối đa 50)

--s2-max-candidates N         Trần candidate từ Semantic Scholar
--arxiv-max-candidates N      Trần candidate từ arXiv
--openalex-max-candidates N   Trần candidate từ OpenAlex
--max-candidates N            Trần tổng trước dedup
--pre-rank-limit N            Số paper đi tiếp sau deterministic rank
--ai-rerank-limit N           Số paper tối đa AI rerank
--ai-enrich-limit N           Số paper tối đa được AI tóm tắt
--result-limit N              Số paper cuối cùng

--latest-years N              Lọc N năm lịch gần nhất + profile latest
--year-from YYYY              Ghi đè năm bắt đầu
--year-to YYYY                Ghi đè năm kết thúc
--ranking-profile PROFILE     balanced/latest/seminal/evidence_review
--require-abstract            Bắt buộc paper có abstract
--keep-missing-abstract       Giữ paper thiếu abstract
--no-cache                    Bỏ cache API học thuật và gọi lại nguồn
--no-ai                       Tắt planner, AI rerank và AI enrichment
--no-ai-rerank                Chỉ tắt AI rerank
--no-assess                   Chỉ tắt AI enrichment/tóm tắt cuối
--no-adaptive-retrieval       Luôn chạy mọi query variant đã tạo
--no-diversity                Tắt MMR diversity
--include-source-records      Thêm toàn bộ candidate theo nguồn vào output
--no-source-records           Không thêm candidate theo nguồn vào output
--no-stage-rankings           Không lưu ranking từng stage/ablation
--print-json                  In toàn bộ JSON ra terminal
```

### Rate limit của nguồn học thuật

Mọi HTTP attempt, kể cả retry, đều đi qua `academic_rate_limiter.py`. Các giá trị
được chỉnh trong `config.py` tại `SOURCE_REQUEST_INTERVAL_SECONDS` và
`SOURCE_RATE_LIMIT_SAFETY_MARGIN_SECONDS`:

| Nguồn | Base | Margin | Khoảng thực tế |
|---|---:|---:|---:|
| Semantic Scholar | 1.00s | 0.50s | 1.50s/request |
| arXiv | 3.00s | 0.50s | 3.50s/request |
| OpenAlex | 1.00s | 0.50s | 1.50s/request |

OpenAlex được đặt bảo thủ theo semantic search (1 request/giây), dù trần chung của
API cao hơn. HTTP 429/5xx dùng `Retry-After` nếu server cung cấp; nếu không sẽ
exponential backoff, tối đa 90 giây. Mỗi request thử tối đa 2 attempt (lần đầu + đúng
1 retry). Với AI, mỗi model cũng có 2 attempt; chỉ sau đó pipeline mới chuyển sang
model fallback. Query cache tiếp
tục được ưu tiên để giảm cả áp lực rate limit và usage budget OpenAlex. Cấu hình thực
tế của mỗi lần chạy được ghi vào `runtime_config.academic_rate_limits` trong JSON.

## Pipeline 2.2 hoạt động thế nào

1. AI planner chuyển prompt thành câu hỏi tiếng Anh, intent, concept groups, query variants và filter. Nếu AI lỗi/không có key, rule-based planner vẫn chạy.
2. Query builder biên dịch plan chung thành đúng cú pháp từng nguồn. Ba nguồn chạy song song; nhiều request trong cùng nguồn chạy tuần tự để tôn trọng rate limit.
3. Candidate được lấy round-robin theo nguồn, chuẩn hóa về schema chung, rồi dedup bằng source ID, DOI, arXiv ID, PMID/PMCID/MAG/DBLP/ACL/Corpus ID và title/author/year có kiểm tra tương thích.
4. Filter loại retraction, sai khoảng năm, sai loại publication, thiếu abstract (mặc định), hoặc không đúng open-access nếu prompt yêu cầu.
5. Deterministic pre-rank tách riêng:
   - `query_match_score`: source rank fusion công bằng, text/concept match, query coverage.
   - `paper_quality_score`: citation impact, citation velocity, recency, publication type, access và metadata completeness. Source agreement chỉ còn bonus metadata rất nhỏ (tối đa khoảng 2%).
6. AI rerank chỉ xem câu hỏi + title + abstract của top shortlist. AI không thấy citation/venue, chỉ điều chỉnh một phần `query_match_score` theo confidence; dưới `AI_RERANK_MIN_CONFIDENCE` thì score AI bị bỏ qua. Nếu fallback khiến nhiều batch dùng model khác nhau, trọng số AI tự bị phạt.
7. Relevance gate loại paper khi AI tự tin rằng paper không liên quan, khi cả text/AI evidence đều yếu, hoặc khi thiếu concept bắt buộc mà AI không đủ mạnh để xác nhận. Vì vậy kết quả có thể ít hơn `--result-limit`; pipeline không lấp danh sách bằng paper yếu.
8. Greedy MMR giảm các kết quả quá giống nhau để top list bao phủ nhiều nhánh của chủ đề hơn.
9. AI enrichment chạy theo batch nhỏ trên shortlist cuối, tạo `paper_analysis.summary` và
   `main_contribution` bằng tiếng Việt. `search_analysis.why_read` cũng được assessor cuối
   viết bằng tiếng Việt theo câu hỏi tìm kiếm. Cả hai ghi `evidence_scope=abstract`, không
   tuyên bố đã đọc full text và không làm thay đổi thứ hạng.

Để chỉ tìm paper mới và tăng trọng số độ mới, dùng:

```powershell
python research_pipeline.py "deepfake detection" `
  --latest-years 3 `
  --ranking-profile latest `
  --result-limit 20 `
  --ai-enrich-limit 20 `
  --output results/deepfake_detection_latest_20.json
```

`--latest-years 3` tự tính khoảng từ năm hiện tại lùi 2 năm đến năm hiện tại và truyền bộ
lọc thời gian phù hợp sang cả Semantic Scholar, arXiv và OpenAlex. Có thể dùng chính xác hơn
với `--year-from YYYY --year-to YYYY`.

Nếu retrieval/ranking đã xong nhưng muốn chạy lại riêng phần tóm tắt tiếng Việt mà không gọi
lại ba API paper:

```powershell
python enrich_results.py results/deepfake_detection_latest_20.json
```

Mặc định lệnh tạo file mới có hậu tố `_vi.json`. Validator từ chối summary, contribution hoặc
why-read bằng tiếng Anh/tiếng Việt không dấu và chuyển sang model free tiếp theo.
9. JSON ghi status, timing từng stage, duplicate/filter rate, request lỗi, model/usage thực tế, snapshot trọng số và `stage_rankings` để benchmark ablation.

## Chỉnh toàn bộ công thức trong `config.py`

Nhóm retrieval:

```python
MAX_QUERY_VARIANTS = 3
MAX_TERMS_PER_CONCEPT = 3
DEFAULT_SEARCH_DEPTH = "quick"
SEMANTIC_SCHOLAR_RESULTS_PER_QUERY = 15
ARXIV_RESULTS_PER_QUERY = 40
OPENALEX_LEXICAL_RESULTS_PER_QUERY = 20
OPENALEX_SEMANTIC_RESULTS_PER_QUERY = 20
SOURCE_MAX_CANDIDATES = {"semantic_scholar": 45, "arxiv": 40, "openalex": 40}
MAX_TOTAL_CANDIDATES = 120
PRE_RANK_LIMIT = 30
AI_RERANK_LIMIT = 20
AI_ENRICH_LIMIT = 10
RESULT_LIMIT = 10
SEARCH_DEPTH_PRESETS = {"quick": {...}, "standard": {...}}
ENABLE_ADAPTIVE_RETRIEVAL = True
ADAPTIVE_TARGET_SOURCE_CAP_RATIO = 0.60
ADAPTIVE_MIN_MARGINAL_UNIQUE_RATIO = 0.10
```

Nhóm deterministic ranking:

```python
RRF_K = 60
SOURCE_RRF_WEIGHTS = {...}
QUERY_MATCH_WEIGHTS = {...}
TEXT_MATCH_WEIGHTS = {...}
FINAL_SCORE_WEIGHTS = {...}       # riêng cho 4 profile
PAPER_QUALITY_WEIGHTS = {...}     # riêng cho 4 profile
IMPACT_SIGNAL_WEIGHTS = {...}
RECENCY_HALF_LIFE_YEARS = {...}
PUBLICATION_TYPE_SCORES = {...}
ACCESS_SCORES = {...}
```

Các mapping trọng số tự được normalize, không bắt buộc tổng đúng 1.0. Không đổi tên key trong mapping nếu không sửa code xử lý tương ứng.

Nhóm AI và diversity:

```python
AI_RERANK_WEIGHT = 0.25
AI_RERANK_MIN_CONFIDENCE = 0.30
AI_RERANK_CROSS_MODEL_PENALTY = 0.50
AI_RERANK_BATCH_SIZE = 3
AI_ENRICH_BATCH_SIZE = 5
AI_ENRICH_ABSTRACT_MAX_CHARS = 2400
AI_RERANK_SIGNAL_WEIGHTS = {...}
ENABLE_DIVERSITY_RERANK = True
DIVERSITY_LAMBDA = 0.82
DIVERSITY_POOL_LIMIT = 30
```

`DIVERSITY_LAMBDA` gần 1 ưu tiên score gốc hơn; thấp hơn tăng mức phạt paper giống nhau. Với model miễn phí và fallback, nên giữ `AI_RERANK_WEIGHT` khoảng 0.20–0.30 thay vì để AI quyết định phần lớn final score.

Cache:

```python
ENABLE_QUERY_CACHE = True
QUERY_CACHE_TTL_BY_SOURCE = {"semantic_scholar": 21600, "openalex": 21600, "arxiv": 86400}
ENABLE_LLM_CACHE = True
LLM_CACHE_TTL_SECONDS = 604800
PRESERVE_RAW_SOURCE_DATA = True
INCLUDE_SOURCE_RECORDS_IN_OUTPUT = False
INCLUDE_STAGE_RANKINGS_IN_OUTPUT = True
```

Cache query và cache LLM tách riêng. API key không nằm trong cache key hoặc output.

## Test riêng từng nguồn

```powershell
python test/test-ai-research-tool/semantic_scholar_test.py "AI agent memory" --limit 5
python test/test-ai-research-tool/arxiv_test.py "AI agent memory" --limit 5
python test/test-ai-research-tool/openalex_test.py "AI agent memory" --limit 5
python test/test-ai-research-tool/paper_sources_smoke_test.py "AI agent memory" --limit 3
```

Raw response của mỗi record được giữ trong `source_specific.raw_data` (S2/OpenAlex) hoặc `source_specific.raw_atom` (arXiv) khi `PRESERVE_RAW_SOURCE_DATA=True`. Tắt cờ này nếu muốn JSON nhỏ hơn.

## Test code và đánh giá chất lượng ranking

Chạy unit test:

```powershell
python -m unittest discover -s test/test-ai-research-tool -p "test_*.py" -v
```

Để đo ranking, sao chép `evaluation_labels.example.json`, thay key bằng `dedup_key` thật trong output và gán grade 0–3, rồi chạy:

```powershell
python test/test-ai-research-tool/evaluate_results.py `
  test/test-ai-research-tool/results/research_pipeline.json `
  test/test-ai-research-tool/my_labels.json `
  --k 5 10 20
```

Script trả Precision@K, Recall@K, MRR và NDCG@K cho final result và từng ablation: RRF-only, query-match, deterministic, AI-reranked và diversified. Đây là cách nên dùng để tinh chỉnh trọng số: tạo một tập prompt + nhãn người dùng cố định, thay trọng số, chạy lại và so metric; không nên kết luận công thức tốt chỉ từ vài kết quả nhìn bằng mắt.

Khi có nhiều query, khai báo các cặp result/labels trong `benchmark_manifest.example.json` rồi tổng hợp macro-average và latency p50/p95:

```powershell
python test/test-ai-research-tool/evaluate_benchmark.py `
  test/test-ai-research-tool/benchmark_manifest.example.json `
  --k 5 10 `
  --output test/test-ai-research-tool/results/benchmark_report.json
```

Schema và giải thích raw field chi tiết nằm trong `paper.schema.json` và `DATA_STRUCTURE_AND_SEARCH.md`.
