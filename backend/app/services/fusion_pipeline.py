"""
Feature 1 — Fusion Pipeline (dual-layer scoring architecture).

Splits the single synchronous risk-scoring pass into two named stages
that mirror the spec:

  AIStage       -> wraps the existing ai_engine.analyze_intent() call
  ForensicStage -> wraps the existing forensics.analyze_headers() +
                   attachment_scanner.scan_attachments() calls

Both stages are independent of each other's INPUT (AIStage only needs
subject/body text; ForensicStage only needs headers/attachments), so they
run CONCURRENTLY in a thread pool instead of one-after-another — this is
a genuine latency win (the AI call is a network request to Groq/Gemini;
forensic/attachment analysis is local CPU work, so they overlap nicely).

DELIBERATE SAFETY CHOICE: the final decision is only computed once BOTH
stages have finished (see risk_fusion.fuse_risk_with_pipeline). Auto-
quarantine in sync_engine.py always sees the FULL fused score — never a
partial/AI-only one. Redis is used purely as a best-effort cache of each
stage's result (useful later for a "live analysis progress" UI); if
Redis is unreachable, everything still works identically, just without
the cache.
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor

from app.services import ai_engine, forensics, attachment_scanner, url_intel

logger = logging.getLogger("mailtrace.fusion_pipeline")

_redis_client = None


def _get_redis():
    """
    Lazily creates the Redis client on first use. If REDIS_URL is unset
    or unreachable, this raises inside the caller's try/except — it
    never crashes app startup or import.
    """
    global _redis_client
    if _redis_client is None:
        import redis
        from app.config import settings
        _redis_client = redis.from_url(
            settings.REDIS_URL, decode_responses=True, socket_connect_timeout=2
        )
    return _redis_client


def _cache_stage_result(case_id: str, stage_name: str, data: dict) -> None:
    """Best-effort cache write. Never raises — a Redis hiccup must never
    affect email analysis."""
    try:
        client = _get_redis()
        client.hset(f"fusion:{case_id}", stage_name, json.dumps(data, default=str))
        client.expire(f"fusion:{case_id}", 60 * 60 * 24)  # 24h TTL — cache, not system of record
    except Exception as exc:
        logger.warning("Redis cache write skipped (case %s, stage %s): %s", case_id, stage_name, exc)


def get_cached_fusion(case_id: str) -> dict | None:
    """
    Reads back whatever stage results are cached for a case_id. Returns
    None (not an error) if Redis is unavailable or nothing is cached —
    callers should treat this as purely informational.
    """
    try:
        client = _get_redis()
        raw = client.hgetall(f"fusion:{case_id}")
        if not raw:
            return None
        return {stage: json.loads(payload) for stage, payload in raw.items()}
    except Exception as exc:
        logger.warning("Redis cache read skipped (case %s): %s", case_id, exc)
        return None


class AIStage:
    """Text/sender intent classification — same call as before, now named
    and independently cacheable."""

    @staticmethod
    def run(case_id: str, parsed_email: dict) -> dict:
        ai_result = ai_engine.analyze_intent(
            parsed_email["subject"],
            parsed_email["plain_body"] or parsed_email["html_body"],
        )
        _cache_stage_result(case_id, "ai_stage", ai_result)
        return ai_result


class ForensicStage:
    """Header/authentication chain analysis + attachment scanning — same
    calls as before, now named and independently cacheable."""

    @staticmethod
    def run(case_id: str, parsed_email: dict) -> dict:
        forensics_result = forensics.analyze_headers(parsed_email)
        attachment_result = attachment_scanner.scan_attachments(parsed_email["attachments"])

        bundle = {"forensics": forensics_result, "attachments": attachment_result}
        _cache_stage_result(case_id, "forensic_stage", bundle)
        return bundle


def run(case_id: str, parsed_email: dict, resolve_network: bool = True) -> dict:
    """
    Runs AIStage and ForensicStage CONCURRENTLY (thread pool), then URL
    intelligence (kept separate — it doesn't fit either stage name in the
    spec, and network-resolves URLs independently of both).

    Returns the same four result dicts pipeline.py already builds today —
    just assembled through named, cached stages instead of four inline
    sequential calls.
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        ai_future = executor.submit(AIStage.run, case_id, parsed_email)
        forensic_future = executor.submit(ForensicStage.run, case_id, parsed_email)

        ai_result = ai_future.result()
        forensic_bundle = forensic_future.result()

    url_result = url_intel.analyze_urls(parsed_email["urls"], resolve_network=resolve_network)

    return {
        "ai_result": ai_result,
        "forensics_result": forensic_bundle["forensics"],
        "attachment_result": forensic_bundle["attachments"],
        "url_result": url_result,
    }