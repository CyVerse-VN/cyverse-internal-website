import json
import sys

sys.stdout.reconfigure(encoding="utf-8")
with open("output/threads_posts.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total posts: {len(data['posts'])}")
with_comments = [p for p in data["posts"] if len(p.get("comments", [])) > 0]
print(f"Posts with comments: {len(with_comments)}")
for p in with_comments:
    print(f"- @{p['username']} (Replies: {p.get('reply_count')}): {len(p['comments'])} comments scraped")
    for c in p['comments'][:2]:
        print(f"    * @{c.get('username')}: {c.get('text')[:60]}...")
