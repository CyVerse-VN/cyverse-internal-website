import { createServer } from "node:http";
import { randomUUID } from "node:crypto";

const now = () => new Date().toISOString();
const users = [
  {
    id: "00000000-0000-4000-8000-000000000001",
    username: "admin",
    password: "correct-password",
    display_name: "Nguyen Anh",
    team: "Data Team",
    role: "admin",
    is_active: true,
    token_version: 0,
    created_at: now(),
    updated_at: now(),
  },
];
const researchSessions = [];
const threadsRuns = [];
const threadsDefaults = {
  keywords: [], max_posts_per_keyword: 25, search_type: "recent", include_comments: true,
  max_comment_posts: -1, max_comments_per_post: 25, min_replies: 0,
  expand_query: true, keywords_per_query: 3, pre_filter: false, pre_filter_strictness: "high", curate: false,
  max_accounts: 3, use_proxy: true,
};

function threadsDetail(run) {
  if (run.status !== "cancelled") {
    const elapsed = Date.now() - Date.parse(run.created_at);
    run.status = elapsed > 6000 ? "completed" : elapsed > 1000 ? "running" : "queued";
  }
  const complete = run.status === "completed";
  return {
    ...run,
    visibility: run.visibility ?? run.request.visibility ?? "public",
    owner: { id: users[0].id, display_name: users[0].display_name }, can_manage: true,
    post_count: complete ? 1 : 0, comment_count: complete ? 2 : 0,
    archive_status: complete ? "ready" : "pending", archive_uploaded_at: complete ? now() : null,
    storage_error: null, deletion_requested: false, started_at: run.created_at,
    stage: complete ? "completed" : run.status === "running" ? "curating" : run.status,
    progress: complete ? 1 : run.status === "running" ? 0.8 : 0,
    completed_at: complete || run.status === "cancelled" ? now() : null,
    result: complete ? {
      query: run.request.query, keywords: run.request.keywords.length ? run.request.keywords : ["quiet cafes"],
      curated_post_ids: ["fixture-post"], total_comments: 2, duration_seconds: 6,
      warnings: [], posts: [{
        post_id: "fixture-post", url: "https://www.threads.com/@fixture/post/abcdef1",
        username: "fixture", text: "A quiet cafe with a reading corner and great coffee.",
        published_at: "2026-10-31T10:00:00Z", like_count: 42, reply_count: 5, repost_count: 3,
        images: [], videos: [], search_keywords: ["quiet cafes"],
        comments: [
          { id: "c1", username: "reader", text: "The upstairs corner is peaceful.", like_count: 4, depth: 1, reply_to_username: null, parent_id: null },
          { id: "c2", username: "visitor", text: "Weekday mornings are the quietest.", like_count: 2, depth: 2, reply_to_username: "reader", parent_id: "c1" },
        ],
        ai_analysis: { is_relevant: true, confidence_score: 0.95, topic: "Quiet places to read", summary: "A reading-friendly cafe, best visited on weekday mornings.", recommended_places: [], key_entities: ["reading", "coffee"], sentiment: "positive" },
      }],
    } : null,
  };
}
const researchConfig = {
  schema_version: "1",
  default_visibility: "public",
  sources: ["semantic_scholar", "arxiv", "openalex"],
  publication_types: ["article", "conference", "preprint", "review", "book", "dataset"],
  defaults: {
    sources: ["semantic_scholar", "arxiv", "openalex"],
    raw_limits: { semantic_scholar: 50, arxiv: 50, openalex: 50 },
    result_limit: 20,
    all_years: false,
    year_from: 2024,
    year_to: 2026,
    publication_types: [],
    languages: [],
    open_access_only: false,
    require_abstract: true,
  },
  limits: {
    query_min: 3,
    query_max: 1000,
    year_min: 2020,
    year_max: 2027,
    raw_per_source_max: 100,
    total_raw_max: 300,
    result_max: 50,
  },
};
function safeUser(user) {
  return {
    id: user.id,
    username: user.username,
    display_name: user.display_name,
    team: user.team,
    role: user.role,
    is_active: user.is_active,
    created_at: user.created_at,
    updated_at: user.updated_at,
  };
}

function createToken(type, user) {
  const claims = Buffer.from(
    JSON.stringify({ user_id: user.id, token_version: user.token_version }),
  ).toString("base64url");
  return `${type}.${claims}.${randomUUID()}`;
}

function tokenUser(token, expectedType) {
  const [type, claims] = String(token ?? "").split(".");
  if (type !== expectedType || !claims) return undefined;
  try {
    const payload = JSON.parse(Buffer.from(claims, "base64url").toString("utf8"));
    return users.find(
      (user) =>
        user.id === payload.user_id &&
        user.token_version === payload.token_version &&
        user.is_active,
    );
  } catch {
    return undefined;
  }
}

function tokenPair(user) {
  return {
    access_token: createToken("access", user),
    refresh_token: createToken("refresh", user),
    token_type: "bearer",
    access_expires_at: new Date(Date.now() + 15 * 60000).toISOString(),
    refresh_expires_at: new Date(Date.now() + 30 * 86400000).toISOString(),
  };
}

function send(response, status, body) {
  response.writeHead(status, { "Content-Type": "application/json" });
  response.end(body === undefined ? "" : JSON.stringify(body));
}

async function readJson(request) {
  let body = "";
  for await (const chunk of request) body += chunk;
  return body ? JSON.parse(body) : {};
}

function currentUser(request) {
  const token = request.headers.authorization?.replace(/^Bearer /, "");
  return tokenUser(token, "access");
}

function researchDetail(session) {
  const status = session.status;
  return {
    ...session,
    current_stage: status === "completed" ? "completed" : status === "running" ? "summarizing" : status,
    progress: status === "completed" ? 1 : status === "running" ? 0.82 : 0,
    queue_position: status === "queued" ? 1 : null,
    result_count: status === "completed" ? session.papers.length : 0,
    papers: status === "completed" ? session.papers : [],
    events: [
      {
        sequence: 1,
        stage: "queued",
        status: "completed",
        message: "Research session added to the queue.",
        progress: 0,
        metadata: {},
        created_at: session.created_at,
      },
      ...(status === "running" || status === "completed"
        ? [{ sequence: 2, stage: "summarizing", status: "running", message: "Writing Vietnamese summaries and reading recommendations.", progress: 0.82, metadata: { selected_count: 1 }, created_at: now() }]
        : []),
      ...(status === "completed"
        ? [{ sequence: 3, stage: "completed", status: "completed", message: "Research results are ready.", progress: 1, metadata: {}, created_at: now() }]
        : []),
    ],
  };
}

export async function startFakeBackend() {
  const server = createServer(async (request, response) => {
  const url = new URL(request.url ?? "/", "http://127.0.0.1:4010");
  if (request.method === "POST" && url.pathname === "/api/v1/auth/login") {
    const data = await readJson(request);
    const user = users.find(
      (candidate) =>
        candidate.username === String(data.username).toLowerCase() &&
        candidate.password === data.password &&
        candidate.is_active,
    );
    if (!user) return send(response, 401, { detail: "Invalid username or password" });
    return send(response, 200, {
      ...tokenPair(user),
      user: safeUser(user),
    });
  }

  if (request.method === "POST" && url.pathname === "/api/v1/auth/refresh") {
    const data = await readJson(request);
    const user = tokenUser(data.refresh_token, "refresh");
    return user
      ? send(response, 200, tokenPair(user))
      : send(response, 401, { detail: "Authentication required" });
  }

  const actor = currentUser(request);
  if (request.method === "GET" && url.pathname === "/api/v1/auth/me") {
    return actor
      ? send(response, 200, safeUser(actor))
      : send(response, 401, { detail: "Authentication required" });
  }
  if (!actor) return send(response, 401, { detail: "Authentication required" });

  if (request.method === "PATCH" && url.pathname === "/api/v1/auth/me") {
    const data = await readJson(request);
    actor.display_name = data.display_name;
    actor.team = data.team;
    actor.updated_at = now();
    return send(response, 200, safeUser(actor));
  }
  if (request.method === "POST" && url.pathname === "/api/v1/auth/me/change-password") {
    const data = await readJson(request);
    if (data.current_password !== actor.password) {
      return send(response, 400, { detail: "Current password is incorrect" });
    }
    actor.password = data.new_password;
    actor.token_version += 1;
    return send(response, 200, tokenPair(actor));
  }

  if (request.method === "GET" && url.pathname === "/api/v1/tools/threads/config") {
    return send(response, 200, {
      enabled: true, accounts_ready: true, ai_available: true, cloudinary_ready: true, defaults: threadsDefaults,
      limits: { keywords: 5, posts_per_keyword: 50, comment_posts: 20, comments_per_post: 100 },
    });
  }
  if (url.pathname === "/api/v1/tools/threads/runs") {
    if (request.method === "GET") {
      const offset = Number(url.searchParams.get("offset") ?? 0);
      const limit = Number(url.searchParams.get("limit") ?? 20);
      return send(response, 200, threadsRuns.slice(offset, offset + limit).map((run) => ({ ...threadsDetail(run), result: null })));
    }
    if (request.method === "POST") {
      const run = {
        id: randomUUID(), request: { ...threadsDefaults, ...await readJson(request) },
        status: "queued", stage: "queued", progress: 0, result: null,
        error_code: null, error_message: null, created_at: now(), completed_at: null,
      };
      threadsRuns.unshift(run);
      return send(response, 202, threadsDetail(run));
    }
  }
  const threadsMatch = url.pathname.match(/^\/api\/v1\/tools\/threads\/runs\/([^/]+)(?:\/(cancel|export))?$/);
  if (threadsMatch) {
    const run = threadsRuns.find((item) => item.id === threadsMatch[1]);
    if (!run) return send(response, 404, { detail: "Threads run not found." });
    if (threadsMatch[2] === "cancel" && request.method === "POST") run.status = "cancelled";
    if (!threadsMatch[2] && request.method === "PATCH") {
      run.visibility = (await readJson(request)).visibility;
    }
    if (!threadsMatch[2] && request.method === "DELETE") {
      const detail = threadsDetail(run);
      threadsRuns.splice(threadsRuns.indexOf(run), 1);
      return send(response, 202, { ...detail, deletion_requested: true });
    }
    const detail = threadsDetail(run);
    if (threadsMatch[2] === "export") {
      if (!detail.result) return send(response, 409, { detail: "Result not ready" });
      const format = url.searchParams.get("format") ?? "json";
      response.writeHead(200, {
        "Content-Type": format === "txt" ? "text/plain" : "application/json",
        "Content-Disposition": `attachment; filename="threads-${run.id}.${format}"`,
      });
      return response.end(format === "txt" ? "THREADS SESSION\nFormat: threads-text-v2\nCOLLECTED COMMENTS\n" : JSON.stringify(detail.result));
    }
    return send(response, 200, detail);
  }

  if (request.method === "GET" && url.pathname === "/api/v1/tools/research/config") {
    return send(response, 200, researchConfig);
  }
  if (request.method === "GET" && url.pathname === "/api/v1/tools/research/sessions") {
    return send(response, 200, {
      items: researchSessions.map((session) => ({
        id: session.id,
        query: session.query,
        title: session.title,
        visibility: session.visibility,
        owner: session.owner,
        is_owner: session.is_owner,
        can_manage: session.can_manage,
        status: session.status,
        current_stage: session.status,
        progress: session.status === "completed" ? 1 : 0,
        queue_position: session.status === "queued" ? 1 : null,
        result_count: session.status === "completed" ? session.papers.length : 0,
        created_at: session.created_at,
        updated_at: session.updated_at,
      })),
      next_cursor: null,
    });
  }
  if (request.method === "POST" && url.pathname === "/api/v1/tools/research/sessions") {
    const data = await readJson(request);
    const createdAt = now();
    const session = {
      id: randomUUID(),
      query: data.query,
      title: data.query,
      visibility: data.visibility ?? "public",
      owner: { id: actor.id, display_name: actor.display_name },
      is_owner: true,
      can_manage: true,
      status: "queued",
      effective_settings: data.settings,
      pipeline_version: "3.0.0",
      warnings: [],
      result_stats: {},
      error: null,
      created_at: createdAt,
      updated_at: createdAt,
      poll_count: 0,
      papers: [
        {
          id: randomUUID(),
          rank: 1,
          relevance_score: 0.94,
          read_priority: "high",
          title: "Explainable Deepfake Detection with Multimodal Evidence",
          authors: ["A. Researcher", "B. Scientist"],
          year: 2026,
          published_at: "2026-03-01",
          venue: "CVPR",
          doi: "10.1000/example",
          arxiv_id: null,
          sources: ["openalex"],
          paper_type: "conference",
          fields: ["Computer Vision"],
          citation_count: 12,
          is_open_access: true,
          pdf_url: "https://example.com/paper.pdf",
          landing_url: "https://example.com/paper",
          summary_vi: "Nghiên cứu đề xuất phương pháp giải thích kết quả phát hiện deepfake bằng bằng chứng đa phương thức.",
          why_read_vi: [
            "Cung cấp cơ chế giải thích trực quan cho dự đoán.",
            "Đánh giá thực nghiệm trên nhiều bộ dữ liệu quan trọng.",
          ],
          analysis_basis: "abstract",
        },
      ],
    };
    researchSessions.unshift(session);
    return send(response, 201, researchDetail(session));
  }
  const researchMatch = url.pathname.match(/^\/api\/v1\/tools\/research\/sessions\/([^/]+)(\/cancel)?$/);
  if (researchMatch) {
    const session = researchSessions.find((candidate) => candidate.id === researchMatch[1]);
    if (!session) return send(response, 404, { detail: "Research session not found" });
    if (request.method === "GET") {
      session.poll_count += 1;
      if (session.poll_count === 2) session.status = "running";
      if (session.poll_count >= 3) {
        session.status = "completed";
        session.result_stats = { result_count: session.papers.length };
      }
      session.updated_at = now();
      return send(response, 200, researchDetail(session));
    }
    if (request.method === "PATCH") {
      const data = await readJson(request);
      if (data.visibility !== undefined) session.visibility = data.visibility;
      if (data.title !== undefined) session.title = data.title;
      session.updated_at = now();
      return send(response, 200, researchDetail(session));
    }
    if (request.method === "DELETE") {
      researchSessions.splice(researchSessions.indexOf(session), 1);
      response.writeHead(204);
      return response.end();
    }
    if (request.method === "POST" && researchMatch[2]) {
      session.status = "cancelled";
      session.updated_at = now();
      return send(response, 200, researchDetail(session));
    }
  }

  if (actor.role !== "admin") return send(response, 403, { detail: "Permission denied" });

  if (request.method === "GET" && url.pathname === "/api/v1/admin/users") {
    await new Promise((resolve) => setTimeout(resolve, 400));
    const query = (url.searchParams.get("query") ?? "").toLowerCase();
    const matches = users.filter((user) =>
      [user.username, user.display_name, user.team ?? ""].some((value) =>
        value.toLowerCase().includes(query),
      ),
    );
    return send(response, 200, {
      items: matches.map(safeUser),
      total: matches.length,
      page: Number(url.searchParams.get("page") ?? 1),
      page_size: Number(url.searchParams.get("page_size") ?? 20),
      current_user_id: actor.id,
    });
  }
  if (request.method === "POST" && url.pathname === "/api/v1/admin/users") {
    const data = await readJson(request);
    if (users.some((user) => user.username === data.username)) {
      return send(response, 409, { detail: "Username already exists" });
    }
    const user = {
      id: randomUUID(),
      username: data.username,
      password: data.password,
      display_name: data.display_name,
      team: data.team,
      role: data.role,
      is_active: true,
      token_version: 0,
      created_at: now(),
      updated_at: now(),
    };
    users.push(user);
    return send(response, 201, safeUser(user));
  }

  const match = url.pathname.match(/^\/api\/v1\/admin\/users\/([^/]+)(\/reset-password)?$/);
  if (match && request.method === "PATCH") {
    const user = users.find((candidate) => candidate.id === match[1]);
    if (!user) return send(response, 404, { detail: "User not found" });
    const data = await readJson(request);
    if (user.is_active && data.is_active === false) user.token_version += 1;
    Object.assign(user, data, { updated_at: now() });
    return send(response, 200, safeUser(user));
  }
  if (match?.[2] && request.method === "POST") {
    const user = users.find((candidate) => candidate.id === match[1]);
    if (!user) return send(response, 404, { detail: "User not found" });
    const data = await readJson(request);
    user.password = data.password;
    user.token_version += 1;
    return send(response, 200, safeUser(user));
  }

  return send(response, 404, { detail: "Not found" });
  });

  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(4010, "127.0.0.1", resolve);
  });
  server.unref();

  return function stopFakeBackend() {
    server.closeAllConnections();
    return new Promise((resolve, reject) => {
      server.close((error) => (error ? reject(error) : resolve()));
    });
  };
}
