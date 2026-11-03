from typing import Literal

from app.tools.threads.schemas import ThreadsRunResponse

JsonDetail = Literal["basic", "standard", "full"]


def render_json(run: ThreadsRunResponse, detail: JsonDetail) -> str:
    assert run.result is not None
    if detail == "basic":
        from pydantic import TypeAdapter

        data = {
            "detail_level": "basic",
            "posts": [
                {
                    "post_id": post.post_id,
                    "url": post.url,
                    "username": post.username,
                    "text": post.text,
                    "comments": [
                        {"id": comment.id, "parent_id": comment.parent_id,
                         "username": comment.username, "text": comment.text}
                        for comment in post.comments
                    ],
                }
                for post in run.result.posts
            ],
        }
        return TypeAdapter(dict[str, object]).dump_json(data, indent=2).decode("utf-8")

    if detail == "standard":
        return run.model_dump_json(indent=2, exclude={
            "result": {"posts": {"__all__": {
                "source_data": True, "comments": {"__all__": {"source_data": True}},
            }}}
        })
    return run.model_dump_json(indent=2)
