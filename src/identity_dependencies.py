"""Identity dependency graph for non-destructive self-model revision.

The graph is deliberately conservative: upstream change produces review proposals.
It does not silently rewrite identity.  Self-state nodes are always routed through
reconsolidation so a single changed memory cannot erase a durable self-description.
"""

from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Iterable


class IdentityNodeKind(str, Enum):
    EVIDENCE = "evidence"
    MEMORY = "memory"
    CONCLUSION = "conclusion"
    SELF_STATE = "self_state"
    INTENTION = "intention"
    POLICY = "policy"
    RELATIONSHIP_MODEL = "relationship_model"
    CAPABILITY = "capability"


class IdentityEdgeKind(str, Enum):
    HARD = "hard"
    SUPPORTING = "supporting"
    CONTEXTUAL = "contextual"
    IDENTITY = "identity"


class IdentityNodeStatus(str, Enum):
    ACTIVE = "active"
    UNCERTAIN = "uncertain"
    REVIEW = "review"
    STALE = "stale"
    RECONSOLIDATE = "reconsolidate"
    RETRACTED = "retracted"


@dataclass
class IdentityNode:
    node_id: str
    kind: IdentityNodeKind
    status: IdentityNodeStatus = IdentityNodeStatus.ACTIVE
    confidence: float = 1.0
    label: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("node_id must be non-empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class IdentityEdge:
    source_id: str
    target_id: str
    kind: IdentityEdgeKind
    weight: float = 1.0
    context: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.weight <= 1.0:
            raise ValueError("edge weight must be between 0 and 1")
        if self.source_id == self.target_id:
            raise ValueError("self dependency is not allowed")


@dataclass(frozen=True)
class IdentityImpact:
    node_id: str
    source_id: str
    edge_kind: IdentityEdgeKind
    proposed_status: IdentityNodeStatus
    confidence_multiplier: float
    depth: int
    reason: str


_STATUS_PRIORITY = {
    IdentityNodeStatus.ACTIVE: 0,
    IdentityNodeStatus.REVIEW: 1,
    IdentityNodeStatus.UNCERTAIN: 2,
    IdentityNodeStatus.RECONSOLIDATE: 3,
    IdentityNodeStatus.STALE: 4,
    IdentityNodeStatus.RETRACTED: 5,
}


def _impact_rank(proposal: IdentityImpact) -> tuple[int, float, int, str, str]:
    return (
        -_STATUS_PRIORITY[proposal.proposed_status], proposal.confidence_multiplier,
        proposal.depth, proposal.source_id, proposal.edge_kind.value,
    )


class IdentityDependencyGraph:
    """A small directed graph for tracing what parts of identity depend on what."""

    def __init__(self) -> None:
        self.nodes: dict[str, IdentityNode] = {}
        self.edges: list[IdentityEdge] = []

    def add_node(self, node: IdentityNode) -> None:
        existing = self.nodes.get(node.node_id)
        if existing is not None and existing != node:
            raise ValueError(f"conflicting node: {node.node_id}")
        self.nodes[node.node_id] = node

    def upsert_node(self, node: IdentityNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: IdentityEdge) -> None:
        if edge.source_id not in self.nodes:
            raise KeyError(f"unknown source node: {edge.source_id}")
        if edge.target_id not in self.nodes:
            raise KeyError(f"unknown target node: {edge.target_id}")
        if edge not in self.edges:
            self.edges.append(edge)

    def outgoing(self, node_id: str) -> list[IdentityEdge]:
        return [edge for edge in self.edges if edge.source_id == node_id]

    def incoming(self, node_id: str) -> list[IdentityEdge]:
        return [edge for edge in self.edges if edge.target_id == node_id]

    def _proposal_for(
        self,
        edge: IdentityEdge,
        *,
        source_change: str,
        depth: int,
    ) -> IdentityImpact:
        target = self.nodes[edge.target_id]

        # Identity is never destructively invalidated by one upstream change.
        if target.kind == IdentityNodeKind.SELF_STATE or edge.kind == IdentityEdgeKind.IDENTITY:
            return IdentityImpact(
                node_id=target.node_id,
                source_id=edge.source_id,
                edge_kind=edge.kind,
                proposed_status=IdentityNodeStatus.RECONSOLIDATE,
                confidence_multiplier=max(0.5, 1.0 - 0.35 * edge.weight),
                depth=depth,
                reason="identity-bearing state depends on changed support; reconsolidation required",
            )

        if edge.kind == IdentityEdgeKind.HARD:
            stale = source_change in {"invalidated", "retracted", "stale"}
            return IdentityImpact(
                node_id=target.node_id,
                source_id=edge.source_id,
                edge_kind=edge.kind,
                proposed_status=IdentityNodeStatus.STALE if stale else IdentityNodeStatus.REVIEW,
                confidence_multiplier=max(0.0, 1.0 - edge.weight) if stale else max(0.6, 1.0 - 0.25 * edge.weight),
                depth=depth,
                reason="hard prerequisite changed",
            )

        if edge.kind == IdentityEdgeKind.SUPPORTING:
            return IdentityImpact(
                node_id=target.node_id,
                source_id=edge.source_id,
                edge_kind=edge.kind,
                proposed_status=IdentityNodeStatus.UNCERTAIN,
                confidence_multiplier=max(0.5, 1.0 - 0.5 * edge.weight),
                depth=depth,
                reason="support changed; confidence should be revisited",
            )

        return IdentityImpact(
            node_id=target.node_id,
            source_id=edge.source_id,
            edge_kind=edge.kind,
            proposed_status=IdentityNodeStatus.REVIEW,
            confidence_multiplier=max(0.7, 1.0 - 0.2 * edge.weight),
            depth=depth,
            reason="context changed; scope should be rechecked",
        )

    def assess_change(
        self,
        node_id: str,
        *,
        change: str = "revised",
        max_depth: int = 16,
    ) -> list[IdentityImpact]:
        """Return downstream review proposals without mutating the graph."""
        if node_id not in self.nodes:
            raise KeyError(node_id)
        if change not in {"revised", "invalidated", "retracted", "stale"}:
            raise ValueError("unsupported change type")
        if max_depth < 1:
            return []

        best: dict[str, IdentityImpact] = {}
        queue = deque([(node_id, change, 0)])
        visited_edges: set[tuple[IdentityEdge, str]] = set()

        while queue:
            source_id, source_change, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for edge in self.outgoing(source_id):
                if edge.target_id == node_id:
                    continue
                edge_key = (edge, source_change)
                if edge_key in visited_edges:
                    continue
                visited_edges.add(edge_key)

                impact = self._proposal_for(
                    edge,
                    source_change=source_change,
                    depth=depth + 1,
                )
                current = best.get(impact.node_id)
                if current is None or _impact_rank(impact) < _impact_rank(current):
                    best[impact.node_id] = impact

                next_change = {
                    IdentityNodeStatus.STALE: "stale",
                    IdentityNodeStatus.RETRACTED: "retracted",
                }.get(impact.proposed_status, "revised")
                queue.append((impact.node_id, next_change, depth + 1))

        return sorted(best.values(), key=lambda item: (item.depth, item.node_id))

    def apply_impacts(self, impacts: Iterable[IdentityImpact]) -> None:
        """Apply reviewed impact proposals. Callers decide when review is sufficient."""
        for impact in impacts:
            node = self.nodes[impact.node_id]
            if node.status == IdentityNodeStatus.RETRACTED:
                continue
            node.status = impact.proposed_status
            node.confidence = max(0.0, min(1.0, node.confidence * impact.confidence_multiplier))

    def support_report(self, node_id: str) -> dict[str, Any]:
        if node_id not in self.nodes:
            raise KeyError(node_id)
        incoming = self.incoming(node_id)
        return {
            "node_id": node_id,
            "support_count": len(incoming),
            "hard_dependencies": [e.source_id for e in incoming if e.kind == IdentityEdgeKind.HARD],
            "supporting_dependencies": [e.source_id for e in incoming if e.kind == IdentityEdgeKind.SUPPORTING],
            "identity_dependencies": [e.source_id for e in incoming if e.kind == IdentityEdgeKind.IDENTITY],
            "contexts": [e.context for e in incoming if e.context],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "ontodiff.identity-dependency.v1",
            "nodes": [
                {
                    **asdict(node),
                    "kind": node.kind.value,
                    "status": node.status.value,
                }
                for node in self.nodes.values()
            ],
            "edges": [
                {
                    **asdict(edge),
                    "kind": edge.kind.value,
                }
                for edge in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IdentityDependencyGraph":
        if data.get("schema_version") != "ontodiff.identity-dependency.v1":
            raise ValueError("unsupported identity dependency schema")
        graph = cls()
        for raw in data.get("nodes", []):
            graph.add_node(
                IdentityNode(
                    node_id=str(raw["node_id"]),
                    kind=IdentityNodeKind(str(raw["kind"])),
                    status=IdentityNodeStatus(str(raw.get("status", "active"))),
                    confidence=float(raw.get("confidence", 1.0)),
                    label=str(raw.get("label", "")),
                    metadata=dict(raw.get("metadata", {})),
                )
            )
        for raw in data.get("edges", []):
            graph.add_edge(
                IdentityEdge(
                    source_id=str(raw["source_id"]),
                    target_id=str(raw["target_id"]),
                    kind=IdentityEdgeKind(str(raw["kind"])),
                    weight=float(raw.get("weight", 1.0)),
                    context=raw.get("context"),
                )
            )
        return graph
