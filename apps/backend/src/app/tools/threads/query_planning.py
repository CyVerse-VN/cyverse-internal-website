"""Backward compatibility wrapper for query planner functions."""

from app.tools.threads.discovery_schemas import DiscoveryQuery, DiscoveryQueryPlan
from app.tools.threads.query_planner import merge_query_plan as combine_queries

__all__ = ["DiscoveryQuery", "DiscoveryQueryPlan", "combine_queries"]
