import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

with open("experiments/comment_structure.json", "r", encoding="utf-8") as f:
    data = json.load(f)

extracted = []
seen_ids = set()

def parse_threads_graphql(obj):
    if isinstance(obj, dict):
        if "caption" in obj and "user" in obj and isinstance(obj.get("user"), dict):
            u = obj["user"].get("username")
            caption = obj.get("caption")
            text = caption.get("text") if isinstance(caption, dict) else (caption if isinstance(caption, str) else None)
            pk = str(obj.get("pk") or obj.get("id") or "")
            tp = obj.get("text_post_app_info") or {}

            is_reply = tp.get("is_reply", False) or tp.get("reply_level") is not None
            if u and text and pk and pk not in seen_ids and is_reply:
                seen_ids.add(pk)
                depth = tp.get("reply_level", 1)
                reply_to = tp.get("reply_to_author")
                reply_to_user = reply_to.get("username") if isinstance(reply_to, dict) else (str(reply_to) if reply_to else None)
                extracted.append({
                    "id": pk,
                    "username": u,
                    "text": text.strip(),
                    "like_count": obj.get("like_count", 0) or 0,
                    "depth": depth,
                    "reply_to_username": reply_to_user,
                })
        for v in obj.values():
            parse_threads_graphql(v)
    elif isinstance(obj, list):
        for item in obj:
            parse_threads_graphql(item)

parse_threads_graphql(data.get("graphql", []))

# Reconstruct parent_id using depth stack
depth_stack = []
for c in extracted:
    depth = c["depth"]
    while depth_stack and depth_stack[-1][0] >= depth:
        depth_stack.pop()
    c["parent_id"] = depth_stack[-1][1] if depth_stack else None
    depth_stack.append((depth, c["id"]))

print(f"Total extracted from GraphQL: {len(extracted)}")
for c in extracted:
    indent = "  " * (c["depth"] - 1)
    prefix = f"{indent}└── " if c["depth"] > 1 else "• "
    print(f"{prefix}[{c['id']} -> parent: {c['parent_id']}] @{c['username']} (Cấp {c['depth']}, trả lời: @{c['reply_to_username']}): {c['text'][:50]}")
