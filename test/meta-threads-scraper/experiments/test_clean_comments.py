import json
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

with open("scratch/comment_structure.json", "r", encoding="utf-8") as f:
    data = json.load(f)

comments = data["dom_comments"][1:] # skip post 0

cleaned = []
for c in comments:
    username = c["username"]
    nodes = c["text_nodes"]
    content_parts = []
    likes = 0
    for node in nodes:
        node_clean = node.strip()
        if not node_clean:
            continue
        if username and node_clean.lower() == username.lower():
            continue
        if node_clean in ("·", "Tác giả", "Author", "Theo dõi", "Đang theo dõi"):
            continue
        if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", node_clean):
            continue
        if re.match(r"^\d+[hdwmys]$", node_clean):
            continue
        if re.match(r"^\d+$", node_clean):
            # Probably like count or reply count
            try:
                likes = int(node_clean)
            except:
                pass
            continue
        content_parts.append(node_clean)
    
    comment_text = "\n".join(content_parts)
    if comment_text:
        cleaned.append({
            "username": username,
            "text": comment_text,
            "likes": likes
        })

print(f"Cleaned {len(cleaned)} comments:")
for i, c in enumerate(cleaned[:10], 1):
    print(f"{i}. @{c['username']} (Likes: {c['likes']}):\n   {c['text']}")
