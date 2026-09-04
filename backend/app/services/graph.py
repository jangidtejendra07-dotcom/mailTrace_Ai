"""
Feature 2 — Campaign Graph GraphQL API.

Exposes the persistent Neo4j campaign graph for querying:
  - campaignGraph(caseId: "...")  -> subgraph linked to one case
  - fullCampaignGraph             -> the entire cross-case graph

Mounted at /graphql in main.py. Visit /graphql in a browser for the
built-in GraphiQL playground. Protected by the SAME JWT bearer auth as
the REST API — reuses get_current_user via context_getter, so an invalid/
missing token is rejected with 401 before any query runs, exactly like
the REST endpoints.
"""
import strawberry
from fastapi import Depends
from strawberry.fastapi import GraphQLRouter

from app.auth.dependencies import get_current_user
from app.models import User
from app.services import graph_manager


@strawberry.type
class GraphNode:
    id: str
    type: str | None
    label: str | None
    cases: list[str]


@strawberry.type
class GraphEdge:
    from_: str = strawberry.field(name="from")
    to: str
    relation: str | None
    cases: list[str]


@strawberry.type
class CampaignGraph:
    nodes: list[GraphNode]
    edges: list[GraphEdge]


def _to_campaign_graph(raw: dict) -> CampaignGraph:
    return CampaignGraph(
        nodes=[
            GraphNode(id=n["id"], type=n.get("type"), label=n.get("label"), cases=n.get("cases", []))
            for n in raw["nodes"]
        ],
        edges=[
            GraphEdge(from_=e["from"], to=e["to"], relation=e.get("relation"), cases=e.get("cases", []))
            for e in raw["edges"]
        ],
    )


@strawberry.type
class Query:
    @strawberry.field(description="Subgraph of indicators/links tied to one case_id.")
    def campaign_graph(self, case_id: str) -> CampaignGraph:
        return _to_campaign_graph(graph_manager.get_campaign_graph(case_id=case_id))

    @strawberry.field(description="The entire cross-case campaign graph.")
    def full_campaign_graph(self) -> CampaignGraph:
        return _to_campaign_graph(graph_manager.get_campaign_graph())


async def get_context(current_user: User = Depends(get_current_user)) -> dict:
    # Depending on get_current_user here means an invalid/missing bearer
    # token raises 401 before the GraphQL query is ever executed — same
    # auth guarantee as every REST endpoint in this app.
    return {"current_user": current_user}


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema, context_getter=get_context)