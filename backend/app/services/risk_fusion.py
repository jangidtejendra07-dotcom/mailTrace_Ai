"""
Section 8 — Risk Fusion + Response.

Combines AI intent, header/authentication, URL intelligence, attachment,
and sender-anomaly scores into a single explainable final risk score,
then applies a configurable policy to decide ALLOW / QUARANTINE / BLOCK.

    AI intent              w=0.25
    Header/authentication  w=0.20
    URL intelligence       w=0.20
    Attachment             w=0.25
    Sender anomaly         w=0.10
                          ------
    FINAL RISK  (weighted, then boosted by any CRITICAL signal)

Policy engine makes the final action; AI only contributes evidence/score.

Feature 1 (Fusion Pipeline) adds fuse_risk_with_pipeline() below, which
orchestrates the dual-layer fusion_pipeline (AIStage + ForensicStage,
run concurrently, cached to Redis) and then applies THIS SAME fuse_risk()
weighting/decision logic, unchanged, on the results. fuse_risk() itself
is not modified — existing behavior and correctness are identical.
"""

WEIGHTS = {
    "ai": 0.25,
    "headers": 0.20,
    "url": 0.20,
    "attachment": 0.25,
    "sender_anomaly": 0.10,
}

# Configurable thresholds (spec section 8)
THRESHOLDS = {
    "quarantine": 40,   # SUSPICIOUS -> QUARANTINE
    "block": 75,        # HIGH/CRITICAL -> BLOCK
}


def compute_sender_anomaly_score(forensics_result: dict) -> int:
    score = 0
    if forensics_result.get("reply_to_mismatch"):
        score += 60
    if forensics_result.get("spf") == "fail" or forensics_result.get("dmarc") == "fail":
        score += 30
    if not forensics_result.get("candidate_source_ip"):
        score += 10
    return min(100, score)


def fuse_risk(ai_result: dict, forensics_result: dict, url_result: dict,
              attachment_result: dict) -> dict:
    sender_anomaly_score = compute_sender_anomaly_score(forensics_result)

    component_scores = {
        "ai_intent": ai_result["score"],
        "header_authentication": forensics_result["score"],
        "url_intelligence": url_result["score"],
        "attachment": attachment_result["score"],
        "sender_anomaly": sender_anomaly_score,
    }

    weighted_sum = (
        component_scores["ai_intent"] * WEIGHTS["ai"] +
        component_scores["header_authentication"] * WEIGHTS["headers"] +
        component_scores["url_intelligence"] * WEIGHTS["url"] +
        component_scores["attachment"] * WEIGHTS["attachment"] +
        component_scores["sender_anomaly"] * WEIGHTS["sender_anomaly"]
    )

    final_score = round(weighted_sum)

    # A single CRITICAL-severity attachment overrides the weighted average
    # (e.g. invoice.pdf.exe must always BLOCK per acceptance test #3)
    if attachment_result.get("severity") == "CRITICAL":
        final_score = max(final_score, 94)

    final_score = int(min(100, max(0, final_score)))

    if final_score >= THRESHOLDS["block"]:
        decision = "BLOCK"
    elif final_score >= THRESHOLDS["quarantine"]:
        decision = "QUARANTINE"
    else:
        decision = "ALLOW"

    if final_score >= THRESHOLDS["block"]:
        classification = ai_result["category"] if ai_result["category"] != "safe" else "malicious"
    elif final_score >= THRESHOLDS["quarantine"]:
        classification = ai_result["category"] if ai_result["category"] != "safe" else "suspicious"
    else:
        classification = "safe"

    explanation = [
        f"AI intent: {component_scores['ai_intent']} (weight {WEIGHTS['ai']})",
        f"Header/authentication: {component_scores['header_authentication']} (weight {WEIGHTS['headers']})",
        f"URL intelligence: {component_scores['url_intelligence']} (weight {WEIGHTS['url']})",
        f"Attachment: {component_scores['attachment']} (weight {WEIGHTS['attachment']})",
        f"Sender anomaly: {component_scores['sender_anomaly']} (weight {WEIGHTS['sender_anomaly']})",
        f"Weighted total: {round(weighted_sum, 1)} -> Final risk score: {final_score}",
    ]
    if attachment_result.get("severity") == "CRITICAL":
        explanation.append("Override applied: CRITICAL attachment forces a high risk floor regardless of weighted average")

    return {
        "final_risk_score": final_score,
        "decision": decision,
        "classification": classification,
        "component_scores": component_scores,
        "weights": WEIGHTS,
        "thresholds": THRESHOLDS,
        "explanation": explanation,
    }


def fuse_risk_with_pipeline(case_id: str, parsed_email: dict, resolve_network: bool = True) -> dict:
    """
    Feature 1 entry point. Runs the dual-layer fusion_pipeline (AIStage +
    ForensicStage concurrently, results cached to Redis), then applies
    the SAME fuse_risk() above on the results — decision-making logic is
    identical to before, just fed by the new pipeline.

    Returns everything fuse_risk() returns, PLUS the four raw stage
    result dicts (ai_result, forensics_result, url_result,
    attachment_result) merged in, since pipeline.py needs those to build
    the rest of its response (sender info, correlation graph, etc.).
    """
    from app.services import fusion_pipeline

    stage_results = fusion_pipeline.run(case_id, parsed_email, resolve_network=resolve_network)

    fusion_result = fuse_risk(
        stage_results["ai_result"],
        stage_results["forensics_result"],
        stage_results["url_result"],
        stage_results["attachment_result"],
    )

    return {
        **fusion_result,
        "ai_result": stage_results["ai_result"],
        "forensics_result": stage_results["forensics_result"],
        "url_result": stage_results["url_result"],
        "attachment_result": stage_results["attachment_result"],
    }