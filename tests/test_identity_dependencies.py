from src.identity_dependencies import (
    IdentityDependencyGraph,
    IdentityEdge,
    IdentityEdgeKind,
    IdentityNode,
    IdentityNodeKind,
    IdentityNodeStatus,
)


def graph():
    g = IdentityDependencyGraph()
    g.add_node(IdentityNode("e1", IdentityNodeKind.EVIDENCE, label="observed episode"))
    g.add_node(IdentityNode("c1", IdentityNodeKind.CONCLUSION, label="self conclusion"))
    g.add_node(IdentityNode("s1", IdentityNodeKind.SELF_STATE, label="durable self state"))
    g.add_edge(IdentityEdge("e1", "c1", IdentityEdgeKind.HARD))
    g.add_edge(IdentityEdge("c1", "s1", IdentityEdgeKind.IDENTITY))
    return g


def test_invalidated_evidence_marks_conclusion_stale():
    impacts = graph().assess_change("e1", change="invalidated")
    by_id = {item.node_id: item for item in impacts}
    assert by_id["c1"].proposed_status == IdentityNodeStatus.STALE


def test_identity_is_reconsolidated_not_deleted():
    impacts = graph().assess_change("e1", change="invalidated")
    by_id = {item.node_id: item for item in impacts}
    assert by_id["s1"].proposed_status == IdentityNodeStatus.RECONSOLIDATE


def test_assessment_is_non_destructive_until_applied():
    g = graph()
    impacts = g.assess_change("e1", change="invalidated")
    assert g.nodes["c1"].status == IdentityNodeStatus.ACTIVE
    g.apply_impacts(impacts)
    assert g.nodes["c1"].status == IdentityNodeStatus.STALE
    assert g.nodes["s1"].status == IdentityNodeStatus.RECONSOLIDATE


def test_supporting_dependency_lowers_confidence_without_staling():
    g = IdentityDependencyGraph()
    g.add_node(IdentityNode("e", IdentityNodeKind.EVIDENCE))
    g.add_node(IdentityNode("c", IdentityNodeKind.CONCLUSION, confidence=0.9))
    g.add_edge(IdentityEdge("e", "c", IdentityEdgeKind.SUPPORTING, weight=0.5))
    impact = g.assess_change("e", change="invalidated")[0]
    assert impact.proposed_status == IdentityNodeStatus.UNCERTAIN
    assert 0 < impact.confidence_multiplier < 1

def test_convergent_paths_propagate_the_strongest_change_in_any_order():
    edges = [
        IdentityEdge("source", "soft", IdentityEdgeKind.SUPPORTING),
        IdentityEdge("source", "hard", IdentityEdgeKind.HARD),
        IdentityEdge("soft", "join", IdentityEdgeKind.HARD),
        IdentityEdge("hard", "join", IdentityEdgeKind.HARD),
        IdentityEdge("join", "dependent", IdentityEdgeKind.HARD),
        IdentityEdge("dependent", "source", IdentityEdgeKind.HARD),
    ]
    results = []
    for ordering in (edges, list(reversed(edges))):
        g = IdentityDependencyGraph()
        for name in ("source", "soft", "hard", "join", "dependent"):
            g.add_node(IdentityNode(name, IdentityNodeKind.MEMORY))
        for edge in ordering:
            g.add_edge(edge)
        results.append({impact.node_id: impact for impact in g.assess_change("source", change="invalidated")})
    assert results[0] == results[1]
    assert results[0]["dependent"].proposed_status == IdentityNodeStatus.STALE
    assert "source" not in results[0]
