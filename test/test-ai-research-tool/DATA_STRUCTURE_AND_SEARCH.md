# Cấu trúc dữ liệu và cơ chế tìm paper: arXiv + OpenAlex + Semantic Scholar

Tài liệu này mô tả hai lớp dữ liệu khác nhau:

1. **Raw response**: dữ liệu nguyên bản API của arXiv/OpenAlex/Semantic Scholar trả về.
2. **Normalized response**: JSON mà các script trong thư mục này chuyển đổi và lưu vào `results/`.

Ba file `results/arxiv.json`, `results/openalex.json` và `results/semantic_scholar.json` là normalized response, không phải raw response đầy đủ.

## 1. Luồng xử lý hiện tại

```text
Query người dùng
    ├── arXiv: search_query=all:"query"   → Atom XML
    ├── OpenAlex: search=query             → JSON
    └── Semantic Scholar: query=query      → JSON
                    ↓
             Parse response
                    ↓
       Chuẩn hóa về cùng paper schema
                    ↓
        results/{arxiv|openalex|semantic_scholar}.json
```

Các file code liên quan:

- `arxiv_test.py`: tạo arXiv query, parse Atom XML.
- `openalex_test.py`: tạo OpenAlex query, dựng lại abstract từ inverted index.
- `semantic_scholar_test.py`: relevance search và xử lý Reader/PDF fallback.
- `common.py`: HTTP retry, chuẩn hóa DOI/arXiv ID và ghi JSON.
- `config.py`: endpoint, query mặc định, limit, timeout và output.

---

## 2. Raw response của arXiv

### 2.1 Định dạng tổng thể

arXiv không trả JSON. API trả một **Atom 1.0 XML feed**. Một response có metadata của truy vấn ở cấp `<feed>` và nhiều paper ở các `<entry>`.

```xml
<?xml version="1.0" encoding="utf-8"?>
<feed
  xmlns="http://www.w3.org/2005/Atom"
  xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/"
  xmlns:arxiv="http://arxiv.org/schemas/atom">

  <!-- Metadata của toàn bộ truy vấn -->
  <title>ArXiv Query: ...</title>
  <id>http://arxiv.org/api/query-id</id>
  <updated>2026-09-09T00:00:00Z</updated>
  <link href="..." rel="self" type="application/atom+xml" />
  <opensearch:totalResults>5869</opensearch:totalResults>
  <opensearch:startIndex>0</opensearch:startIndex>
  <opensearch:itemsPerPage>3</opensearch:itemsPerPage>

  <!-- Một paper; entry lặp lại cho từng kết quả -->
  <entry>
    <id>https://arxiv.org/abs/2411.18583v1</id>
    <updated>2024-11-27T18:27:07Z</updated>
    <published>2024-11-27T18:27:07Z</published>
    <title>Paper title</title>
    <summary>Abstract của paper</summary>

    <author>
      <name>Author name</name>
      <arxiv:affiliation>Institution nếu có</arxiv:affiliation>
    </author>

    <link href="https://arxiv.org/abs/..." rel="alternate" type="text/html" />
    <link href="https://arxiv.org/pdf/..." rel="related" title="pdf"
          type="application/pdf" />
    <link href="https://doi.org/..." rel="related" title="doi" />

    <arxiv:primary_category term="cs.CL" scheme="http://arxiv.org/schemas/atom" />
    <category term="cs.CL" scheme="http://arxiv.org/schemas/atom" />
    <category term="cs.AI" scheme="http://arxiv.org/schemas/atom" />

    <!-- Các field dưới là optional -->
    <arxiv:comment>23 pages, 8 figures</arxiv:comment>
    <arxiv:journal_ref>Journal reference</arxiv:journal_ref>
    <arxiv:doi>10.xxxx/example</arxiv:doi>
  </entry>
</feed>
```

### 2.2 Ý nghĩa field arXiv

| XML element | Kiểu | Ý nghĩa |
|---|---:|---|
| `feed/title` | string | Query đã được arXiv canonicalize |
| `feed/id` | string | ID riêng của truy vấn |
| `feed/updated` | datetime | Thời điểm feed được cập nhật |
| `opensearch:totalResults` | integer | Tổng số kết quả phù hợp |
| `opensearch:startIndex` | integer | Offset hiện tại, bắt đầu từ 0 |
| `opensearch:itemsPerPage` | integer | Số entry trong trang |
| `entry/id` | URL | URL trang abstract, chứa arXiv ID và có thể có version |
| `entry/title` | string | Tiêu đề paper |
| `entry/summary` | string | Abstract |
| `entry/published` | datetime | Ngày version đầu tiên được gửi |
| `entry/updated` | datetime | Ngày version đang trả về được cập nhật |
| `entry/author/name` | string | Tên tác giả; một paper có nhiều author |
| `arxiv:affiliation` | string/null | Affiliation do tác giả cung cấp |
| `entry/link` | object XML | Link abstract, PDF và đôi khi DOI |
| `entry/category` | object XML | Tất cả category của paper |
| `arxiv:primary_category` | object XML | Category chính |
| `arxiv:comment` | string/null | Ghi chú như số trang, figures, conference |
| `arxiv:journal_ref` | string/null | Thông tin xuất bản ở journal nếu có |
| `arxiv:doi` | string/null | DOI nếu tác giả/arXiv đã cung cấp |

arXiv **không cung cấp citation count**, citation graph, relevance score cụ thể hay plain JSON trong API này.

### 2.3 Request arXiv hiện tại tìm như thế nào?

Script đang gửi tương đương:

```text
GET https://export.arxiv.org/api/query
    ?search_query=all:"retrieval augmented generation"
    &start=0
    &max_results=3
    &sortBy=relevance
    &sortOrder=descending
```

- `all:` tìm trong title, author, abstract, comment, journal reference, category và report number.
- Dấu `"..."` biến query thành một cụm từ. Cách hiện tại ưu tiên precision nhưng có thể bỏ sót paper dùng cách diễn đạt khác.
- `sortBy=relevance` dùng relevance ranking mặc định của Apache Lucene theo tài liệu arXiv. Đây là lexical search, không phải embedding/semantic search.

### 2.4 Các cơ chế tìm khác của arXiv

| Cách | Query ví dụ | Khi nên dùng |
|---|---|---|
| Chỉ title | `ti:"retrieval augmented generation"` | Muốn độ chính xác cao |
| Chỉ abstract | `abs:"retrieval augmented generation"` | Chủ đề xuất hiện trong nội dung nhưng không ở title |
| Theo author | `au:"Yoshua Bengio"` | Tìm paper của tác giả |
| Theo category | `cat:cs.AI` | Thu hẹp lĩnh vực |
| Boolean | `ti:RAG OR abs:"retrieval augmented generation"` | Tăng recall bằng từ đồng nghĩa |
| Loại trừ | `all:agent ANDNOT cat:cs.RO` | Bỏ nhóm không mong muốn |
| Khoảng ngày | `submittedDate:[202401010000 TO 202412312359]` | Systematic review theo thời gian |
| Theo arXiv ID | `id_list=2411.18583,2502.00306` | Lấy chính xác paper đã biết |
| Mới nhất | `sortBy=submittedDate&sortOrder=descending` | Theo dõi paper mới |
| Cập nhật gần nhất | `sortBy=lastUpdatedDate` | Theo dõi revision |
| Phân trang | `start=100&max_results=100` | Lấy thêm candidates |
| Bulk metadata | OAI-PMH | Thu thập dữ liệu lớn thay vì search tương tác |

---

## 3. Raw response của OpenAlex

### 3.1 Envelope của API

OpenAlex trả JSON. List/search endpoint có dạng:

```json
{
  "meta": {
    "count": 186765,
    "page": 1,
    "per_page": 3,
    "next_cursor": null,
    "cost_usd": 0.001
  },
  "results": [
    { "... một Work object ...": "..." }
  ],
  "group_by": []
}
```

- `meta.count`: tổng số work phù hợp.
- `meta.page`, `meta.per_page`: thông tin trang.
- `meta.next_cursor`: cursor trang kế tiếp khi dùng cursor paging.
- `meta.cost_usd`: chi phí của request theo API response.
- `results`: danh sách Work objects.
- `group_by`: các bucket khi request dùng `group_by`; bình thường là danh sách rỗng.

### 3.2 Full Work object có những nhóm field nào?

Nếu không truyền `select`, một Work object đầy đủ có dạng tổng quát sau. Nhiều field có thể là `null`, `[]` hoặc vắng mặt tùy paper và thay đổi API:

```json
{
  "id": "https://openalex.org/W4389984066",
  "doi": "https://doi.org/10.48550/arxiv.2312.10997",
  "title": "Paper title",
  "display_name": "Paper title",
  "ids": {
    "openalex": "https://openalex.org/W...",
    "doi": "https://doi.org/...",
    "mag": "...",
    "pmid": "https://pubmed.ncbi.nlm.nih.gov/...",
    "pmcid": "https://www.ncbi.nlm.nih.gov/pmc/articles/..."
  },
  "language": "en",
  "type": "article",
  "publication_year": 2024,
  "publication_date": "2024-03-24",
  "biblio": {
    "volume": "38",
    "issue": "16",
    "first_page": "...",
    "last_page": "..."
  },

  "abstract_inverted_index": {
    "Retrieval": [0, 25],
    "augmented": [1],
    "generation": [2]
  },

  "authorships": [
    {
      "author_position": "first",
      "is_corresponding": true,
      "author": {
        "id": "https://openalex.org/A...",
        "display_name": "Author name",
        "orcid": "https://orcid.org/..."
      },
      "institutions": [
        {
          "id": "https://openalex.org/I...",
          "display_name": "Institution",
          "ror": "https://ror.org/...",
          "country_code": "US",
          "type": "education",
          "lineage": []
        }
      ],
      "countries": ["US"],
      "raw_author_name": "Name as published",
      "raw_affiliation_strings": ["Raw affiliation"]
    }
  ],
  "corresponding_author_ids": ["https://openalex.org/A..."],
  "corresponding_institution_ids": ["https://openalex.org/I..."],
  "institutions": [],
  "countries_distinct_count": 1,
  "institutions_distinct_count": 1,

  "primary_location": {
    "id": "...",
    "is_oa": true,
    "landing_page_url": "https://doi.org/...",
    "pdf_url": "https://example.org/paper.pdf",
    "source": {
      "id": "https://openalex.org/S...",
      "display_name": "Journal or repository",
      "issn_l": "...",
      "issn": [],
      "is_oa": true,
      "is_in_doaj": false,
      "type": "journal"
    },
    "license": "cc-by",
    "license_id": "...",
    "version": "publishedVersion",
    "is_accepted": true,
    "is_published": true
  },
  "locations": [],
  "locations_count": 1,
  "best_oa_location": {},
  "open_access": {
    "is_oa": true,
    "oa_status": "green",
    "oa_url": "https://example.org/paper.pdf",
    "any_repository_has_fulltext": true
  },

  "primary_topic": {},
  "topics": [
    {
      "id": "https://openalex.org/T...",
      "display_name": "Topic name",
      "score": 0.99,
      "subfield": {},
      "field": {},
      "domain": {}
    }
  ],
  "keywords": [{"id": "...", "display_name": "...", "score": 0.8}],
  "concepts": [],
  "mesh": [],
  "sustainable_development_goals": [],

  "cited_by_count": 373,
  "counts_by_year": [{"year": 2025, "cited_by_count": 100}],
  "cited_by_percentile_year": {"min": 99, "max": 100},
  "citation_normalized_percentile": {
    "value": 0.99,
    "is_in_top_1_percent": true,
    "is_in_top_10_percent": true
  },
  "fwci": 12.4,
  "referenced_works_count": 50,
  "referenced_works": ["https://openalex.org/W..."],
  "related_works": ["https://openalex.org/W..."],

  "apc_list": null,
  "apc_paid": null,
  "funders": [],
  "awards": [],
  "has_content": {"pdf": true, "grobid_xml": true},
  "has_fulltext": true,
  "content_urls": {"pdf": "...", "grobid_xml": "..."},
  "is_retracted": false,
  "is_xpac": false,
  "indexed_in": ["arxiv", "crossref"],
  "created_date": "2024-03-25",
  "updated_date": "2026-09-08T...Z"
}
```

Đây là shape minh họa đầy đủ theo **nhóm field**, không phải cam kết mọi record đều có mọi value. Schema OpenAlex có thể bổ sung/deprecate field; nên parser phải chấp nhận `null`, field thiếu và nested object thiếu.

### 3.3 Script hiện tại yêu cầu field nào?

Để phục vụ ranking và đánh giá khả năng đọc, `openalex_test.py` truyền `select` với các nhóm field sau:

```text
id
doi
title
abstract_inverted_index
authorships
publication_year
publication_date
cited_by_count
primary_location
best_oa_location
open_access
topics
keywords
ids
type
language
updated_date
referenced_works_count
counts_by_year
fwci
citation_normalized_percentile
relevance_score
is_retracted
has_fulltext
content_urls
```

Raw response vẫn **không phải full Work object**: `locations` đầy đủ, author/venue detail, các field lớn dành cho graph/discovery như `referenced_works`, `related_works`, funders/awards và dữ liệu phụ không được lấy. Nếu cần enrichment sâu, gọi singleton `/works/{OpenAlex_ID}` cho top candidates. Với production, không nên bỏ `select` trên search hàng loạt.

OpenAlex không trả abstract dạng text thông thường. Nó trả `abstract_inverted_index`, ví dụ:

```json
{
  "abstract_inverted_index": {
    "Retrieval": [0],
    "augmented": [1],
    "generation": [2],
    "uses": [3]
  }
}
```

Script sắp xếp word theo position và dựng lại thành:

```text
Retrieval augmented generation uses
```

### 3.4 Request OpenAlex hiện tại tìm như thế nào?

Script gửi tương đương:

```text
GET https://api.openalex.org/works
    ?search=retrieval augmented generation
    &per_page=3
    &sort=relevance_score:desc
    &select=id,doi,title,...
    &api_key=HIDDEN
```

Default text search của OpenAlex:

- Tìm trong `title`, `abstract` và `fulltext` đã index.
- Bỏ stop words và dùng stemming; ví dụ dạng số nhiều có thể match dạng số ít.
- Các từ không nối bằng toán tử Boolean được hiểu là `AND`.
- Kết quả có `relevance_score` ở raw record nếu field này được yêu cầu.
- Ranking mặc định kết hợp độ giống text với citation count. Vì vậy paper cũ/nhiều trích dẫn có thể đứng cao hơn paper mới dù text match tương đương.

Script vừa `sort=relevance_score:desc` vừa lưu `relevance_score` vào `source_specific.relevance_score`.

### 3.5 Các cơ chế tìm khác của OpenAlex

#### A. Exact/Boolean/proximity/fuzzy lexical search

```text
search.exact="retrieval augmented generation"
search=(RAG OR "retrieval augmented generation") AND evaluation
search="climate change"~5
search=machin~1
search.exact=neural*
```

- `search.exact`: không stemming.
- `AND`, `OR`, `NOT`: query logic.
- `"phrase"`: cụm từ chính xác.
- `~N`: proximity hoặc fuzzy edit distance tùy cách dùng.
- `*`, `?`: wildcard khi dùng `search.exact`.

#### B. Semantic search bằng embedding

```text
search.semantic=How can an AI agent remember facts across long conversations?
```

OpenAlex semantic search embed title + abstract của paper và query thành vector 1.024 chiều bằng GTE Large EN, sau đó xếp theo cosine similarity. Nó phù hợp với câu hỏi dài hoặc khi paper dùng từ khác query.

Các giới hạn được tài liệu hiện tại nêu:

- Query tối đa 2.000 ký tự được dùng để match.
- Tối đa 50 kết quả/query.
- 1 request/giây.
- Một request chỉ dùng một trong `search`, `search.exact`, `search.semantic`.

#### C. Metadata filters

```text
filter=from_publication_date:2023-01-01,is_oa:true,has_abstract:true
filter=publication_year:2025,type:article
filter=cited_by_count:>100
filter=doi:https://doi.org/10.xxxx/example
filter=topics.id:T123456
filter=author.id:A123456
```

OpenAlex hỗ trợ rất nhiều filter theo năm, ngày, type, open access, DOI, author, institution, topic, citation và các thuộc tính khác. Có thể kết hợp `search=...` với `filter=...` trong cùng request.

#### D. ID/DOI lookup

```text
GET /works/W4389984066
GET /works/https://doi.org/10.48550/arxiv.2312.10997
```

Dùng khi đã có ID chính xác; không cần ranking.

#### E. Citation graph và related works

- `referenced_works`: những paper mà paper hiện tại trích dẫn.
- Truy vấn các work có `cites:{work_id}` để tìm paper trích dẫn seed paper.
- `related_works`: các paper gần seed paper theo chủ đề được OpenAlex tính sẵn.

Cách này hữu ích để “snowball”: bắt đầu từ một paper tốt rồi đi ngược references và đi xuôi citations, thay vì chỉ search keyword.

#### F. Pagination/bulk

- `page` + `per_page`: phù hợp với tối đa 10.000 kết quả đầu.
- `cursor=*` rồi dùng `meta.next_cursor`: lấy sâu hơn.
- OpenAlex snapshot: phù hợp tải toàn bộ dataset; không nên cursor qua toàn bộ `/works`.

---

## 4. Raw response của Semantic Scholar

### 4.1 Envelope của relevance search

Semantic Scholar Academic Graph API trả JSON. Endpoint hiện dùng là:

```text
GET https://api.semanticscholar.org/graph/v1/paper/search
```

Response có dạng:

```json
{
  "total": 78162,
  "offset": 0,
  "next": 3,
  "data": [
    { "... một Paper object ...": "..." }
  ]
}
```

| Field | Kiểu | Ý nghĩa |
|---|---:|---|
| `total` | integer | Tổng số paper phù hợp với query |
| `offset` | integer | Vị trí bắt đầu của trang hiện tại |
| `next` | integer/null | Offset cho trang kế tiếp; có thể không có khi hết kết quả |
| `data` | array | Danh sách Paper objects |

### 4.2 Paper object mà script hiện yêu cầu

Semantic Scholar chỉ trả những field được liệt kê trong query parameter `fields`. Script đang yêu cầu:

```text
paperId
corpusId
title
abstract
authors
year
publicationDate
venue
publicationVenue
journal
citationCount
influentialCitationCount
referenceCount
isOpenAccess
url
openAccessPdf
externalIds
fieldsOfStudy
s2FieldsOfStudy
publicationTypes
tldr
```

Nếu `SEMANTIC_SCHOLAR_INCLUDE_EMBEDDING = True`, script yêu cầu thêm `embedding.specter_v2`. Mặc định tắt vì vector làm JSON lớn và chỉ cần ở bước rerank top candidates.

Một raw Paper object tương ứng có shape:

```json
{
  "paperId": "46f9f7b8f88f72e12cbdb21e3311f995eb6e65c5",
  "corpusId": 266359151,
  "externalIds": {
    "ArXiv": "2312.10997",
    "DOI": "10.xxxx/example",
    "CorpusId": 266359151,
    "DBLP": "journals/example/...",
    "PubMed": "..."
  },
  "url": "https://www.semanticscholar.org/paper/46f9...",
  "title": "Retrieval-Augmented Generation for Large Language Models: A Survey",
  "abstract": "Paper abstract or null",
  "authors": [
    {
      "authorId": "123456",
      "name": "Author name"
    }
  ],
  "year": 2023,
  "publicationDate": "2023-12-18",
  "venue": "arXiv.org",
  "citationCount": 4035,
  "influentialCitationCount": 254,
  "openAccessPdf": {
    "url": "https://example.org/paper.pdf",
    "status": "GREEN",
    "license": "CCBY"
  },
  "fieldsOfStudy": ["Computer Science"],
  "publicationTypes": ["JournalArticle", "Review"]
}
```

Các object thực tế có thể trả `null`, chuỗi rỗng, danh sách rỗng hoặc thiếu external ID. Không nên giả định paper nào cũng có abstract, DOI hoặc PDF.

Semantic Scholar còn hỗ trợ nested `citations`, `references` và embedding. Script chỉ lấy citation/reference **count** trong search; danh sách graph nên gọi endpoint riêng cho top candidates để tránh response lớn.

### 4.3 Ý nghĩa các field quan trọng

| Raw field | Kiểu | Ý nghĩa |
|---|---:|---|
| `paperId` | string | ID chính của paper trong Semantic Scholar |
| `corpusId` | integer | ID số dùng trong S2 corpus/datasets |
| `externalIds` | object | DOI, arXiv, PubMed, DBLP và ID ngoài khác nếu biết |
| `url` | string | Trang paper trên Semantic Scholar; không phải direct PDF |
| `title` | string | Tiêu đề paper |
| `abstract` | string/null | Abstract nếu Semantic Scholar có dữ liệu |
| `authors` | array | Danh sách `{authorId, name}` |
| `year` | integer/null | Năm xuất bản |
| `publicationDate` | date/null | Ngày xuất bản nếu biết |
| `venue` | string/null | Tên venue rút gọn |
| `citationCount` | integer/null | Tổng citation Semantic Scholar liên kết được |
| `influentialCitationCount` | integer/null | Citation được Semantic Scholar đánh dấu influential |
| `openAccessPdf` | object/null | URL, trạng thái/license PDF open access nếu có |
| `fieldsOfStudy` | array | Lĩnh vực học thuật cấp cao |
| `publicationTypes` | array | JournalArticle, Conference, Review và các loại khác |

### 4.4 Request hiện tại tìm paper như thế nào?

Script gửi request tương đương:

```text
GET https://api.semanticscholar.org/graph/v1/paper/search
    ?query=retrieval augmented generation
    &limit=3
    &fields=paperId,title,abstract,...

x-api-key: HIDDEN
```

- Đây là **paper relevance search** theo plain-text query.
- Endpoint `/paper/search` không hỗ trợ Boolean/special query syntax như arXiv hoặc OpenAlex.
- Script thay dấu `-` trong query bằng khoảng trắng vì tài liệu API cảnh báo từ có gạch nối có thể không match.
- Kết quả được Semantic Scholar xếp theo relevance; API không trả một `relevance_score` số trong response này.
- Relevance search chỉ cho truy cập tối đa 1.000 kết quả được xếp hạng và mỗi response tối đa 10 MB. Nếu cần nhiều hơn, dùng bulk search hoặc dataset.

Có thể bổ sung filter trực tiếp vào request, ví dụ:

```text
year=2020-2026
publicationDateOrYear=2024-01-01:2026-12-31
publicationTypes=Review,JournalArticle
fieldsOfStudy=Computer Science
minCitationCount=10
openAccessPdf
```

### 4.5 Các cơ chế tìm/lấy khác của Semantic Scholar

#### A. Bulk paper search

```text
GET /graph/v1/paper/search/bulk?query=(retrieval | RAG)+evaluation
```

- Dùng để lấy nhiều metadata hơn relevance search.
- Query hỗ trợ Boolean `+` (AND), `|` (OR), `-` (NOT), phrase, prefix wildcard và fuzzy/proximity syntax.
- Dùng continuation `token` để phân trang.
- Phù hợp harvesting candidates; không nhằm cung cấp relevance ranking giống `/paper/search`.

#### B. Best title match

```text
GET /graph/v1/paper/search/match?query=exact paper title
```

Trả paper gần title nhất cùng `matchScore`. Hữu ích khi đã có title từ citation hoặc PDF nhưng chưa có DOI/ID.

#### C. Exact ID/DOI/arXiv lookup

```text
GET /graph/v1/paper/{paper_id}
GET /graph/v1/paper/DOI:10.xxxx/example
GET /graph/v1/paper/ARXIV:2312.10997
GET /graph/v1/paper/CorpusId:266359151
```

Dùng khi đã biết định danh; không qua relevance ranking. Với nhiều ID, dùng `POST /graph/v1/paper/batch` để giảm số request.

#### D. Citation/reference graph

```text
GET /graph/v1/paper/{paper_id}/citations
GET /graph/v1/paper/{paper_id}/references
```

- `citations`: những paper trích dẫn seed paper.
- `references`: những paper được seed paper trích dẫn.

Đây là cơ chế snowball literature review hữu ích sau khi đã có vài seed paper tốt.

#### E. Recommendations API

```text
GET /recommendations/v1/papers/forpaper/{paper_id}
```

Có thể tìm paper tương tự một seed paper. API recommendation dạng batch còn cho phép positive/negative paper IDs để điều khiển hướng đề xuất. Cơ chế này phù hợp khám phá paper lân cận hơn là tìm exact keyword.

#### F. Autocomplete và snippet search

- `/graph/v1/paper/autocomplete`: gợi ý title khi người dùng đang gõ.
- `/graph/v1/snippet/search`: tìm đoạn text phù hợp trong title/abstract/body và trả snippet/score khi endpoint/quyền truy cập hỗ trợ.

### 4.6 URL, Reader và direct PDF fallback

Schema phẳng giữ hai URL chung và các URL kỹ thuật trong `source_specific`:

| Field normalized | Ví dụ | Loại |
|---|---|---|
| `url` | `https://www.semanticscholar.org/paper/{paperId}` | Trang metadata paper |
| `pdf_url` | `openAccessPdf.url` hoặc Reader fallback | URL tốt nhất để người dùng mở đọc |
| `source_specific.reader_url` | `https://www.semanticscholar.org/reader/{paperId}` | Trang Reader HTML |
| `source_specific.direct_pdf_url` | API PDF hoặc PDF arXiv | URL dành cho downloader/PDF parser |

Logic code hiện tại:

```text
openAccessPdf.url có giá trị
    → pdf_url = openAccessPdf.url
    → source_specific.direct_pdf_url = openAccessPdf.url
    → source_specific.pdf_url_origin = api_open_access_pdf

openAccessPdf.url thiếu nhưng có paperId
    → pdf_url = https://www.semanticscholar.org/reader/{paperId}
    → source_specific.reader_url = cùng URL Reader
    → source_specific.direct_pdf_url = PDF arXiv nếu có
    → source_specific.pdf_url_origin = semantic_scholar_reader_fallback
```

Khi tải và parse PDF tự động, dùng `source_specific.direct_pdf_url`; khi mở giao diện cho người dùng, dùng `pdf_url`. Cách này giữ tương thích với JSON cũ nhưng vẫn tránh gửi Reader HTML vào PDF parser.

---

## 5. Normalized schema phẳng dùng chung

Schema máy đọc nằm tại `paper.schema.json`, dùng JSON Schema Draft 2020-12 và giữ gần với ba file JSON ban đầu. `schema_version` hiện là `1.1.0`.

Hai ngày của paper (`published_at`, `updated_at`) luôn được lưu dưới dạng ISO `YYYY-MM-DD`, không có giờ. Nếu API trả datetime có múi giờ, pipeline đổi sang `Asia/Ho_Chi_Minh` (UTC+7) rồi mới lấy ngày. Định dạng ISO được chọn để sắp xếp và lưu database ổn định; giao diện có thể hiển thị lại thành `DD/MM/YYYY`.

Envelope của một script nguồn:

```json
{
  "schema_version": "1.1.0",
  "source": "openalex",
  "ok": true,
  "query": "retrieval augmented generation",
  "limit": 3,
  "fetched_at": "2026-09-10T10:20:05Z",
  "elapsed_seconds": 2.2,
  "total_available": 5869,
  "request_cost_usd": 0.001,
  "papers": []
}
```

`request_cost_usd` chỉ có với OpenAlex. Script tổng trả `papers` phẳng để UI dùng chung và `sources` chỉ chứa trạng thái từng API, không lặp lại paper.

### 5.1 Shape của một paper

```json
{
  "schema_version": "1.1.0",
  "source": "openalex",
  "source_id": "W4389984066",
  "source_rank": 1,
  "title": "Paper title",
  "abstract": "Abstract đã làm sạch hoặc dựng lại",
  "authors": ["Author 1", "Author 2"],
  "year": 2023,
  "published_at": "2023-12-18",
  "updated_at": "2026-09-08",
  "venue": "arXiv",
  "doi": "10.48550/arxiv.2312.10997",
  "arxiv_id": "2312.10997",
  "url": "https://doi.org/10.48550/arxiv.2312.10997",
  "pdf_url": "https://arxiv.org/pdf/2312.10997",
  "citation_count": 732,
  "reference_count": 42,
  "is_open_access": true,
  "fields": ["Retrieval augmented generation", "Large language models"],
  "publication_types": ["preprint"],
  "source_specific": {
    "relevance_score": 4053.67,
    "citations_by_year": [{"year": 2025, "cited_by_count": 361}],
    "is_retracted": false
  }
}
```

### 5.2 Vì sao chỉ giữ các field chung này?

| Field | Lý do giữ |
|---|---|
| `source`, `source_id`, `source_rank` | Truy vết nguồn và giữ thứ tự relevance do nguồn trả |
| `title`, `abstract` | Hiển thị, semantic search và rerank |
| `authors` | Hiển thị/cross-check tên; bỏ author object sâu để JSON gọn |
| `year`, `published_at`, `updated_at` | Recency và revision |
| `venue`, `publication_types` | Phân biệt preprint, conference, journal |
| `doi`, `arxiv_id` | Deduplicate và nối phiên bản |
| `url`, `pdf_url`, `is_open_access` | Quyết định paper có thể mở/đọc/tải không |
| `citation_count`, `reference_count` | Tín hiệu ảnh hưởng và độ rộng tài liệu tham khảo |
| `fields` | Topic/category để filter và rerank |
| `source_specific` | Giữ tín hiệu quý chỉ một nguồn có mà không tạo nhiều field chung luôn null |

`null` ở field chung nghĩa là nguồn không cung cấp, không được đổi thành 0. Ví dụ arXiv không có citation count; điều này không có nghĩa paper có 0 citation.

### 5.3 Field riêng được giữ theo nguồn

`source_specific` tự bỏ `null`, chuỗi rỗng, list rỗng và object rỗng. `False` và `0` vẫn được giữ vì có ý nghĩa.

| Nguồn | Field riêng hữu ích |
|---|---|
| arXiv | `version`, `primary_category`, `comment`, DOI ứng viên suy ra và trạng thái xác minh |
| OpenAlex | `relevance_score`, `fwci`, citation percentile/history, `is_retracted`, language, keyword score, external IDs, OA/license/full-text |
| Semantic Scholar | corpus ID, influential citations, external IDs, TLDR, publication venue/journal, PDF provenance, Reader/direct PDF, OA/license |

Các field normalized vẫn được giữ gọn. Khi `PRESERVE_RAW_SOURCE_DATA=True`, raw record gốc được lưu thêm tại `source_specific.raw_data` (Semantic Scholar/OpenAlex) hoặc `source_specific.raw_atom` (arXiv) để có thể tái xử lý sau này; tắt cấu hình này nếu ưu tiên kích thước JSON.

DOI suy ra từ arXiv ID chỉ nằm trong `source_specific.derived_doi_candidate` với `derived_doi_verified=false`; không dùng như DOI canonical trước khi xác minh DataCite.
---

## 6. Nên dùng cơ chế nào cho AI research tool?

### 6.1 Một request có thể chứa nhiều keyword và trả nhiều paper không?

Có. Cả ba search endpoint đều nhận một query có nhiều từ và trả một danh sách paper. `limit`, `max_results` hoặc `per_page` là số paper trong một response/trang; không phải mỗi keyword chỉ trả một paper.

| Nguồn | Query nhiều keyword | Số paper/trang | Khi cần nhiều query |
|---|---|---|---|
| Semantic Scholar relevance | Một chuỗi plain text gồm nhiều từ/cụm từ | `limit`, sau đó dùng `offset` | Mỗi query variant/synonym formulation thường là request riêng |
| arXiv | Ghép field query bằng `AND`, `OR`, `ANDNOT` | `max_results`, phân trang bằng `start` | Có thể gom synonym trong một Boolean query |
| OpenAlex | Plain text hoặc Boolean `AND/OR/NOT`, phrase/proximity/fuzzy | `per_page`, phân trang bằng `page`/`cursor` | Có thể gom synonym; semantic search là request riêng |

Ví dụ cùng một ý định “RAG giảm hallucination trong medical LLM”:

```text
Nhóm A: "retrieval augmented generation" OR RAG
Nhóm B: hallucination OR factuality
Nhóm C: medical OR clinical
```

Semantic Scholar relevance search không hỗ trợ Boolean syntax ở endpoint đang dùng, nên tạo 2-4 chuỗi tự nhiên và gọi riêng:

```text
query=retrieval augmented generation hallucination medical LLM
query=RAG factuality clinical language models
```

Mỗi request vẫn có thể lấy nhiều paper:

```text
GET /graph/v1/paper/search?query=RAG+factuality+clinical+language+models&limit=50
```

Nếu cần harvesting số lượng lớn và Boolean thay vì relevance ranking, dùng Semantic Scholar bulk search:

```text
GET /graph/v1/paper/search/bulk?query=(RAG|"retrieval augmented generation")+hallucination
```

arXiv có thể biểu diễn các nhóm synonym trong một query:

```text
search_query=(all:"retrieval augmented generation" OR all:RAG)
             AND (all:hallucination OR all:factuality)
             AND (all:medical OR all:clinical)
&start=0
&max_results=50
```

OpenAlex cũng có thể gửi một Boolean expression trong một URL:

```text
GET /works
    ?search=("retrieval augmented generation" OR RAG) AND (hallucination OR factuality) AND (medical OR clinical)
    &per_page=50
    &sort=relevance_score:desc
```

Hoặc dùng một câu hỏi tự nhiên với semantic search:

```text
search.semantic=How does retrieval augmented generation reduce hallucinations in clinical LLMs?
```

Không nên biến mỗi keyword đơn lẻ thành một request vì sẽ tạo nhiều kết quả nhiễu và tốn quota. AI query planner nên tạo **concept groups**, nối synonym bằng `OR`, nối các ý bắt buộc bằng `AND`, rồi sinh 2-4 query variants. Sau đó lấy khoảng 20-50 candidates/variant/source, deduplicate theo DOI → arXiv ID → title, rồi rerank bằng title + abstract.

Code test hiện tại nhận đúng **một query string mỗi lần chạy** và giới hạn CLI ở 20 paper. OpenAlex có thể nhận Boolean trực tiếp; arXiv hiện bọc toàn chuỗi trong `all:"..."` nên chưa nhận Boolean expression từ CLI; Semantic Scholar relevance cần nhiều request nếu muốn nhiều variants. Đây là phần nên tách thành query planner/orchestrator khi chuyển từ smoke test sang tool production.

### 6.2 Pipeline retrieval đề xuất

Không nên chỉ dùng một query keyword duy nhất. Kiến trúc phù hợp hơn là hybrid retrieval:

```text
Câu hỏi người dùng
        ↓
Query understanding / dịch sang English
        ↓
Tạo 2-4 query variants + keywords + synonyms
        ↓
├── arXiv lexical
├── OpenAlex lexical + semantic
└── Semantic Scholar relevance + recommendations
        ↓
Merge + deduplicate theo DOI → arXiv ID → normalized title
        ↓
Filter năm/type/OA/retracted/has abstract
        ↓
Rerank title + abstract theo câu hỏi người dùng
        ↓
Citation/reference expansion từ các seed paper tốt
        ↓
Tải full text hợp lệ → chunk → retrieve evidence → answer có citation
```

### So sánh nhanh

| Cơ chế | Điểm mạnh | Điểm yếu | Dùng cho |
|---|---|---|---|
| Keyword relevance | Nhanh, dễ giải thích | Bỏ sót từ đồng nghĩa | Query ngắn, thuật ngữ rõ |
| Exact/Boolean | Precision cao, kiểm soát tốt | Cần người/LLM viết query tốt | Systematic review |
| Semantic embedding | Match theo ý nghĩa | Có thể trả paper liên quan chung chung | Câu hỏi tự nhiên, query dài |
| Metadata filter | Rất chính xác | Không khám phá nội dung | Năm, author, type, OA, topic |
| Citation graph | Tìm nền tảng và follow-up | Thiên về paper đã có liên kết | Literature review sâu |
| Related works | Mở rộng từ seed tốt | Phụ thuộc chất lượng seed | Khám phá lân cận chủ đề |
| Hybrid + rerank | Recall và precision tốt nhất | Tốn request/compute hơn | AI research tool production |

### Khuyến nghị cụ thể cho code hiện tại

1. Giữ search của cả arXiv, OpenAlex và Semantic Scholar để tạo candidate pool đa nguồn.
2. Thêm OpenAlex `search.semantic` như một nhánh song song, không thay thế lexical hoàn toàn.
3. Bỏ exact phrase bắt buộc ở arXiv cho một số query; tạo thêm query Boolean với acronym/synonym.
4. Dùng Semantic Scholar recommendations và citation/reference graph để mở rộng từ seed paper tốt.
5. Field ranking nhẹ đã được lấy trong search; chỉ enrichment `referenced_works`, `related_works`, citation contexts và embedding cho top candidates.
6. Deduplicate trước khi đưa paper vào LLM.
7. Rerank bằng title + abstract theo đúng câu hỏi, không dùng citation count làm tín hiệu chính vì nó thiên vị paper cũ.
8. Chỉ tạo kết luận từ abstract/full text thực tế; metadata search chỉ là bước tìm candidate.

---

## 7. Pipeline ranking đang được triển khai

Pipeline 2.1 dùng thứ tự: AI query planning → adaptive multi-source retrieval → normalize → dedup → filter → deterministic pre-rank → AI rerank → MMR diversity → AI enrichment.

Hai score lõi không trộn lẫn ý nghĩa:

- `query_match_score`: độ phù hợp với đúng câu hỏi, gồm source RRF, text/concept match và query coverage.
- `paper_quality_score`: tín hiệu paper đáng đọc, gồm citation impact, citation velocity, recency, publication type, access và metadata completeness. `source_agreement` chỉ còn trọng số metadata rất nhỏ vì các nguồn không độc lập với nhau.

Source RRF chỉ lấy best rank một lần cho mỗi nguồn. Vì vậy ba query variants của Semantic Scholar không tự tạo ba phiếu bầu để lấn át một kết quả từ arXiv hay OpenAlex. Số query match được lưu riêng trong `query_coverage`.

AI reranker chỉ nhận câu hỏi, intent, title và abstract; không nhận citation count hoặc venue. AI chỉ pha vào `query_match_score` theo `AI_RERANK_WEIGHT × confidence`, bỏ qua confidence quá thấp và giảm trọng số nếu các batch bị route sang nhiều model khác nhau. `paper_quality_score` vẫn hoàn toàn deterministic. MMR sau đó dùng token similarity để tránh top kết quả chứa nhiều phiên bản gần như cùng một hướng nghiên cứu.

Output enrichment tách `paper_analysis` (summary/contribution độc lập với query) khỏi `search_analysis` (why-read và matched concepts phụ thuộc query). Summary, contribution và why-read của shortlist cuối được yêu cầu bằng tiếng Việt. Cả hai ghi `evidence_scope: abstract` để không tạo cảm giác hệ thống đã đọc full text.

Groq là LLM provider mặc định. Query planning ưu tiên `openai/gpt-oss-20b`, semantic rerank
ưu tiên `qwen/qwen3.6-27b`, còn summary/why-read ưu tiên `openai/gpt-oss-20b` với strict JSON
Schema. Rate limiter giữ 20% headroom cho RPM/TPM/RPD/TPD, đồng thời quan sát các header
remaining/reset/retry-after của Groq. Enrichment xử lý 5 paper/batch; model phải trả đúng
schema, đủ paper và tiếng Việt có dấu. Nếu không, client chuyển model kế tiếp; hết fallback
thì batch dừng và metadata ghi lỗi cùng số paper đã hoàn tất. OpenRouter vẫn dùng được bằng
`LLM_PROVIDER=openrouter`.

Mọi trọng số dùng trong một lượt chạy được chụp vào `runtime_config.ranking`; timing, duplicate rate, filter rejection rate và lỗi từng nguồn nằm trong `timings_seconds`, `metrics` và `retrieval.sources`.

## 8. Tài liệu chính thức

- arXiv API User's Manual: <https://info.arxiv.org/help/api/user-manual.html>
- OpenAlex Search: <https://help.openalex.org/api/searching/>
- OpenAlex Semantic Search: <https://help.openalex.org/api/semantic-search/>
- OpenAlex Filters: <https://help.openalex.org/api/filtering/>
- OpenAlex Paging: <https://help.openalex.org/api/paging/>
- OpenAlex Work attributes: <https://help.openalex.org/data/works/attributes/>
- Semantic Scholar Academic Graph API: <https://api.semanticscholar.org/api-docs/graph>
- Semantic Scholar Recommendations API: <https://api.semanticscholar.org/api-docs/recommendations>
