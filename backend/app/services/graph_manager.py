"""
Feature 2 — Dynamic Campaign Graphs (Neo4j backend).

Persists each case's correlation graph (already computed by
case_manager.build_correlation_graph() — untouched, still used for the
single-case JSON embedded in each case's evidence package/report) into
Neo4j using MERGE.

Why MERGE matters: if the SAME indicator (IP, domain, ASN, attachment
hash, sender) shows up in a DIFFERENT case later, MERGE reuses the
existing node and just appends the new case_id to it, instead of creating
a duplicate disconnected node. That's the entire mechanism that turns
"one graph per case" into a persistent CROSS-CASE campaign graph — no
extra correlation logic needed, Neo4j's MERGE does it for free.
"""
import logging

from neo4j import GraphDatabase

from app.config import settings

logger = logging.getLogger("mailtrace.graph_manager")

_driver = None


def _get_driver():
    global _driver
    if _driver is None:
        _driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USERNAME, settings.NEO4J_PASSWORD),
        )
    return _driver


def close_driver() -> None:
    global _driver
    if _driver is not None:
        _driver.close()
        _driver = None


def _add_node(tx, node: dict, case_id: str) -> None:
    tx.run(
        """
        MERGE (n:Indicator {id: $id})
        ON CREATE SET n.type = $type, n.label = $label, n.cases = [$case_id]
        ON MATCH SET n.cases = CASE
            WHEN NOT $case_id IN n.cases THEN n.cases + $case_id
            ELSE n.cases
        END
        """,
        id=node["id"], type=node.get("type"), label=node.get("label"), case_id=case_id,
    )


def _add_edge(tx, edge: dict, case_id: str) -> None:
    tx.run(
        """
        MATCH (a:Indicator {id: $from_id})
        MATCH (b:Indicator {id: $to_id})
        MERGE (a)-[r:RELATION {relation: $relation}]->(b)
        ON CREATE SET r.cases = [$case_id]
        ON MATCH SET r.cases = CASE
            WHEN NOT $case_id IN r.cases THEN r.cases + $case_id
            ELSE r.cases
        END
        """,
        from_id=edge["from"], to_id=edge["to"],
        relation=edge.get("relation", "RELATED_TO"), case_id=case_id,
    )


def update_graph(case_id: str, nodes: list[dict], edges: list[dict]) -> None:
    """
    Pushes one case's correlation graph into Neo4j. Safe to call for every
    analyzed case — repeated indicators automatically link into the same
    persistent nodes rather than duplicating (see MERGE note above).
    """
    driver = _get_driver()
    with driver.session() as session:
        for node in nodes:
            session.execute_write(_add_node, node, case_id)
        for edge in edges:
            session.execute_write(_add_edge, edge, case_id)


def get_campaign_graph(case_id: str | None = None) -> dict:
    """
    Returns the full cross-case graph, or (if case_id is given) just the
    subgraph of nodes/edges linked to that one case. Backs the GraphQL API.
    """
    driver = _get_driver()
    with driver.session() as session:
        if case_id:
            result = session.run(
                """
                MATCH (n:Indicator)
                WHERE $case_id IN n.cases
                OPTIONAL MATCH (n)-[r:RELATION]-(m:Indicator)
                WHERE $case_id IN r.cases
                RETURN DISTINCT n, r, m
                """,
                case_id=case_id,
            )
        else:
            result = session.run(
                """
                MATCH (n:Indicator)
                OPTIONAL MATCH (n)-[r:RELATION]->(m:Indicator)
                RETURN DISTINCT n, r, m
                """
            )

        nodes_by_id = {}
        edges = []
        for record in result:
            n = record["n"]
            nodes_by_id[n["id"]] = {
                "id": n["id"], "type": n.get("type"),
                "label": n.get("label"), "cases": n.get("cases", []),
            }
            m, r = record["m"], record["r"]
            if m is not None and r is not None:
                nodes_by_id[m["id"]] = {
                    "id": m["id"], "type": m.get("type"),
                    "label": m.get("label"), "cases": m.get("cases", []),
                }
                edges.append({
                    "from": n["id"], "to": m["id"],
                    "relation": r.get("relation"), "cases": r.get("cases", []),
                })

        return {"nodes": list(nodes_by_id.values()), "edges": edges}