from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.orchestration.workflow import app_graph
from app.orchestration.sentinel_agent import SentinelBrainstormer
from app.orchestration.risk_scorer import risk_scorer
from app.orchestration.deep_dive import deep_dive_generator
from app.orchestration.correlation_engine import correlation_engine
from app.orchestration.narrative_generator import narrative_generator
from app.orchestration.scan_memory import scan_memory
from app.services.slack_notifier import notify_slack, notify_slack_narrative
from app.core.config import settings
from app.core.logger import logger, _mission_log_buffer, _sse_event_queue, _mission_meta
from datetime import datetime
import asyncio
import json

router = APIRouter()
brainstormer = SentinelBrainstormer()


# ─── Helper: execute a single mission through the NL2SQL graph ──────────────

async def run_mission(mission: dict) -> dict:
    # Set up per-mission log capture
    log_buf: list = []
    _mission_log_buffer.set(log_buf)
    # Set mission metadata so the log handler can tag SSE entries
    _mission_meta.set({
        "mission_id": mission["id"],
        "mission_name": mission["name"],
        "domain": mission["domain"],
        "severity": mission.get("severity", "MEDIUM"),
    })

    initial_state = {
        "user_question": mission["query"],
        "domain": mission["domain"],
        "conversation_history": [],
        "retry_count": 0,
    }

    try:
        result = await app_graph.ainvoke(initial_state)
        query_results = result.get("query_result") or []

        # Dynamic risk scoring from actual data
        scoring = risk_scorer.score(mission, query_results)

        return {
            "mission_id": mission["id"],
            "mission_name": mission["name"],
            "domain": mission["domain"],
            "severity": scoring["severity"],
            "risk_score": scoring["risk_score"],
            "risk_factors": scoring["factors"],
            "sql": result.get("generated_sql"),
            "data_count": len(query_results),
            "results": query_results,
            "visualization_config": result.get("visualization_config"),
            "insight": result.get("insight"),
            "recommendation": result.get("recommendation"),
            "original_query": mission["query"],
            "depth": mission.get("depth", 0),
            "parent_mission_id": mission.get("parent_mission_id"),
            "rationale": mission.get("rationale", ""),
            "timestamp": "LIVE AUDIT",
            "logs": log_buf,
        }
    except Exception as e:
        logger.error(f"Sentinel Mission {mission['id']} Failed: {str(e)}")
        return {
            "mission_id": mission["id"],
            "mission_name": mission["name"],
            "domain": mission["domain"],
            "severity": mission.get("severity", "MEDIUM"),
            "risk_score": 0,
            "risk_factors": {},
            "error": str(e),
            "depth": mission.get("depth", 0),
            "parent_mission_id": mission.get("parent_mission_id"),
            "data_count": 0,
            "results": [],
            "logs": log_buf,
        }
    finally:
        _mission_log_buffer.set(None)


# ─── SSE Streaming Endpoint ─────────────────────────────────────────────────

@router.get("/scan/stream")
async def stream_sentinel_scan():
    """
    Server-Sent Events endpoint that streams the full Sentinel v2 pipeline:
    1. Brainstorm missions (adaptive)
    2. Stream each mission result as it completes
    3. Deep-dive follow-ups on high-risk findings
    4. Cross-domain correlation
    5. Executive intelligence brief
    6. Record scan to memory
    """

    async def event_generator():
        all_results = []

        # Unified event queue for real-time log streaming + mission results
        event_queue = asyncio.Queue()
        _sse_event_queue.set(event_queue)

        # ── Phase 1: Brainstorm ──────────────────────────────────────────
        logger.info("SENTINEL v2: Brainstorming adaptive missions...")
        missions = await brainstormer.brainstorm_missions(count_per_domain=2)
        if not missions:
            logger.warning("Brainstorm failed, using fallback.")
            missions = [
                {"id": "fall-001", "name": "Basic Security Audit",
                 "query": "Show users with risk_level HIGH and account_status ACTIVE",
                 "domain": "security", "severity": "HIGH"},
            ]

        adaptive_ctx = scan_memory.get_adaptive_context()
        yield _sse("scan_started", {
            "total_missions": len(missions),
            "missions": [{"id": m["id"], "name": m["name"], "domain": m["domain"]} for m in missions],
            "adaptive_context": {
                "scan_count": adaptive_ctx["scan_count"],
                "domain_weights": adaptive_ctx["domain_weights"],
            },
        })

        # ── Phase 2: Execute missions in parallel, stream as they complete ─
        logger.info(f"SENTINEL v2: Executing {len(missions)} missions...")

        async def run_and_queue(m):
            result = await run_mission(m)
            await event_queue.put(("mission", result))

        tasks = [asyncio.create_task(run_and_queue(m)) for m in missions]

        completed = 0
        total = len(missions)
        while completed < total:
            event_type, data = await event_queue.get()
            if event_type == "log":
                yield _sse("mission_log", data)
            elif event_type == "mission":
                all_results.append(data)
                completed += 1
                yield _sse("mission_complete", data)
                asyncio.create_task(notify_slack(data))

        await asyncio.gather(*tasks, return_exceptions=True)

        # Drain any remaining log events in the queue
        while not event_queue.empty():
            event_type, data = event_queue.get_nowait()
            if event_type == "log":
                yield _sse("mission_log", data)

        yield _sse("scan_complete", {"total": len(all_results)})

        # ── Phase 3: Deep Dive follow-ups ────────────────────────────────
        if settings.DEEP_DIVE_ENABLED:
            deep_dive_missions = []
            for res in list(all_results):
                if await deep_dive_generator.should_deep_dive(res):
                    followups = await deep_dive_generator.generate_followups(res, depth=0)
                    if followups:
                        deep_dive_missions.extend(followups)
                        yield _sse("deep_dive_started", {
                            "parent_mission_id": res["mission_id"],
                            "followup_count": len(followups),
                        })

            if deep_dive_missions:
                logger.info(f"SENTINEL v2: Running {len(deep_dive_missions)} deep-dive follow-ups...")

                async def run_dd(m):
                    result = await run_mission(m)
                    await event_queue.put(("mission", result))

                dd_tasks = [asyncio.create_task(run_dd(m)) for m in deep_dive_missions]

                dd_completed = 0
                dd_total = len(deep_dive_missions)
                while dd_completed < dd_total:
                    event_type, data = await event_queue.get()
                    if event_type == "log":
                        yield _sse("mission_log", data)
                    elif event_type == "mission":
                        all_results.append(data)
                        dd_completed += 1
                        yield _sse("mission_complete", data)
                        asyncio.create_task(notify_slack(data))

                await asyncio.gather(*dd_tasks, return_exceptions=True)

                # Drain remaining logs
                while not event_queue.empty():
                    event_type, data = event_queue.get_nowait()
                    if event_type == "log":
                        yield _sse("mission_log", data)

        # ── Phase 4: Cross-Domain Correlation ────────────────────────────
        clusters = []
        if settings.CORRELATION_ENABLED:
            logger.info("SENTINEL v2: Running cross-domain correlation...")
            yield _sse("correlation_started", {})
            clusters = await correlation_engine.correlate(all_results)
            yield _sse("correlation_complete", {"clusters": clusters})

        # ── Phase 5: Executive Intelligence Brief ────────────────────────
        logger.info("SENTINEL v2: Generating intelligence brief...")
        yield _sse("narrative_started", {})
        narrative = await narrative_generator.generate(
            detections=all_results,
            clusters=clusters,
            scan_metadata={"total_missions": len(all_results), "timestamp": "LIVE"},
        )
        yield _sse("narrative_complete", narrative)
        asyncio.create_task(notify_slack_narrative(narrative))

        # ── Phase 6: Record to scan memory ───────────────────────────────
        scan_memory.record_scan(all_results)
        scan_id = f"scan-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"
        scan_memory.save_full_scan(scan_id, all_results, clusters, narrative)
        logger.info(f"SENTINEL v2: Scan complete. {len(all_results)} total detections recorded. ID: {scan_id}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Original non-streaming endpoint (backward compatible) ──────────────────

@router.get("/scan")
async def run_sentinel_scan():
    """
    Original Sentinel scan — returns all results at once.
    Kept for backward compatibility. Now includes risk scoring + narrative.
    """
    logger.info("SENTINEL: Running non-streaming scan...")

    missions = await brainstormer.brainstorm_missions(count_per_domain=2)
    if not missions:
        missions = [
            {"id": "fall-001", "name": "Basic Security Audit",
             "query": "Show users with risk_level HIGH and account_status ACTIVE",
             "domain": "security", "severity": "HIGH"},
        ]

    tasks = [run_mission(m) for m in missions]
    results = await asyncio.gather(*tasks)
    results_list = list(results)

    # Send Slack alerts for HIGH/CRITICAL findings
    for r in results_list:
        asyncio.create_task(notify_slack(r))

    # Generate narrative and send to Slack
    narrative = await narrative_generator.generate(
        detections=results_list,
        clusters=[],
        scan_metadata={"total_missions": len(results_list), "timestamp": "LIVE"},
    )
    asyncio.create_task(notify_slack_narrative(narrative))

    # Record to scan memory
    scan_memory.record_scan(results_list)
    scan_id = f"scan-{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}"
    scan_memory.save_full_scan(scan_id, results_list, narrative=narrative)

    return {"status": "success", "detections": results_list, "narrative": narrative}


# ─── Scan History Endpoints ─────────────────────────────────────────────────

@router.get("/history")
async def list_scan_history():
    """Return metadata for all persisted scans, newest first."""
    scans = scan_memory.list_scans()
    return {"scans": scans}


@router.get("/history/{scan_id}")
async def get_scan_history(scan_id: str):
    """Return full scan data for a specific scan ID."""
    data = scan_memory.get_scan(scan_id)
    if data is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Scan not found")
    return data


# ─── SSE formatting helper ──────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"
