from __future__ import annotations

import json
import os
import signal
import threading
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import docker
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from sqlalchemy import desc

from .database import SessionLocal
from .main import (
    DBIncident,
    DBServiceActionJob,
    DBService,
    ENV_SHORT,
    SERVICE_ACTION_POLICIES,
    build_service_overview,
    compute_overview,
    record_incident_entry,
)

MONITOR_INTERVAL_SECONDS = int(os.getenv("MONITOR_INTERVAL_SECONDS", "60"))
MONITOR_HEALTH_HOST = os.getenv("MONITOR_HEALTH_HOST", "0.0.0.0")
MONITOR_HEALTH_PORT = int(os.getenv("MONITOR_HEALTH_PORT", "9000"))
MONITOR_PROBES_ENABLED = os.getenv("MONITOR_PROBES_ENABLED", "true").lower() == "true"
MONITOR_SOURCE = "monitor-worker"

# ---------------------------------------------------------------------------
# Prometheus probe metrics
# ---------------------------------------------------------------------------
service_probe_success_total = Counter(
    "service_probe_success_total",
    "Total successful service health probes by worker",
    ["service_name", "environment"],
)
service_probe_failure_total = Counter(
    "service_probe_failure_total",
    "Total failed service health probes by worker",
    ["service_name", "environment"],
)
service_probe_latency_seconds = Histogram(
    "service_probe_latency_seconds",
    "Service health probe round-trip latency in seconds",
    ["service_name"],
    buckets=[0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0],
)
service_state_changes_total = Counter(
    "service_state_changes_total",
    "Total detected service state changes (healthy/unhealthy transitions)",
    ["service_name", "to_state"],
)


def process_pending_action_jobs(db_session) -> None:
    pending_jobs = (
        db_session.query(DBServiceActionJob)
        .filter(DBServiceActionJob.status == "pending")
        .order_by(DBServiceActionJob.id.asc())
        .all()
    )
    if not pending_jobs:
        return

    client = docker.from_env()
    try:
        for job in pending_jobs:
            service = (
                db_session.query(DBService)
                .filter(DBService.id == job.service_id, DBService.is_active.is_(True))
                .first()
            )
            if not service:
                job.status = "failed"
                job.error_detail = "Service not found or inactive."
                job.completed_at = datetime.utcnow()
                db_session.commit()
                continue

            policy = SERVICE_ACTION_POLICIES.get(service.name)
            if not policy or job.action not in policy["allowed_actions"]:
                job.status = "failed"
                job.error_detail = "Action is not permitted for this service."
                job.completed_at = datetime.utcnow()
                db_session.commit()
                continue

            runtime_target = service.runtime_target or policy["runtime_target"]
            job.status = "running"
            job.started_at = datetime.utcnow()
            db_session.commit()

            try:
                container = client.containers.get(runtime_target)
                if job.action == "restart":
                    container.restart(timeout=10)
                    service.status = "running"
                elif job.action == "start":
                    container.start()
                    service.status = "running"
                elif job.action == "stop":
                    container.stop(timeout=10)
                    service.status = "stopped"

                job.status = "completed"
                job.result_detail = f"{job.action} executed for runtime target '{runtime_target}'."
                job.completed_at = datetime.utcnow()
                db_session.commit()

                record_incident_entry(
                    db_session,
                    title=f"{service.name} {job.action} completed",
                    affected_service_id=service.id,
                    severity="low",
                    summary=f"monitor-worker executed {job.action} for {service.name}.",
                    symptoms="A queued service action completed successfully.",
                    recent_changes=f"Runtime target: {runtime_target}",
                    status="resolved",
                    source="service-action",
                    event_type=f"service_{job.action}",
                    overview_snapshot=compute_overview(db_session).model_dump(),
                    analysis={
                        "job_id": job.id,
                        "action": job.action,
                        "runtime_target": runtime_target,
                        "result": "success",
                    },
                )
            except docker.errors.NotFound:
                job.status = "failed"
                job.error_detail = f"Container '{runtime_target}' was not found."
                job.completed_at = datetime.utcnow()
                db_session.commit()
                record_incident_entry(
                    db_session,
                    title=f"{service.name} {job.action} failed",
                    affected_service_id=service.id,
                    severity="high",
                    summary=f"monitor-worker could not find container '{runtime_target}' for {service.name}.",
                    symptoms="Docker reported that the target container was missing.",
                    recent_changes=f"Queued service action job {job.id}.",
                    status="open",
                    source="service-action",
                    event_type=f"service_{job.action}_failed",
                    overview_snapshot=compute_overview(db_session).model_dump(),
                    analysis={
                        "job_id": job.id,
                        "action": job.action,
                        "runtime_target": runtime_target,
                        "result": "container-not-found",
                    },
                )
            except docker.errors.DockerException as exc:
                job.status = "failed"
                job.error_detail = str(exc)
                job.completed_at = datetime.utcnow()
                db_session.commit()
                record_incident_entry(
                    db_session,
                    title=f"{service.name} {job.action} failed",
                    affected_service_id=service.id,
                    severity="high",
                    summary=f"monitor-worker could not execute {job.action} for {service.name}.",
                    symptoms=str(exc),
                    recent_changes=f"Queued service action job {job.id}.",
                    status="open",
                    source="service-action",
                    event_type=f"service_{job.action}_failed",
                    overview_snapshot=compute_overview(db_session).model_dump(),
                    analysis={
                        "job_id": job.id,
                        "action": job.action,
                        "runtime_target": runtime_target,
                        "result": "docker-error",
                    },
                )
    finally:
        client.close()


class MonitorHealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/health"}:
            body = json.dumps({"status": "ok", "service": MONITOR_SOURCE}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path == "/metrics":
            body = generate_latest()
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def build_service_states(db_session) -> dict[str, dict[str, Any]]:
    states: dict[str, dict[str, Any]] = {}
    for service in (
        db_session.query(DBService)
        .filter(
            DBService.is_active.is_(True),
            DBService.environment.in_([ENV_SHORT, "all"]),
        )
        .all()
    ):
        start = time.perf_counter()
        overview = build_service_overview(service)
        duration = time.perf_counter() - start
        service_probe_latency_seconds.labels(service_name=service.name).observe(duration)
        if overview.healthy:
            service_probe_success_total.labels(
                service_name=service.name, environment=service.environment
            ).inc()
        else:
            service_probe_failure_total.labels(
                service_name=service.name, environment=service.environment
            ).inc()
        states[str(service.id)] = {
            "id": service.id,
            "name": service.name,
            "service_type": service.service_type,
            "environment": service.environment,
            "status": service.status,
            "healthy": overview.healthy,
            "detail": overview.detail,
        }
    return states


def load_previous_states(db_session) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    latest_event = (
        db_session.query(DBIncident)
        .filter(DBIncident.source == MONITOR_SOURCE)
        .order_by(desc(DBIncident.id))
        .first()
    )
    if not latest_event or not latest_event.overview_snapshot:
        return {}, {}

    try:
        snapshot = json.loads(latest_event.overview_snapshot)
    except json.JSONDecodeError:
        return {}, {}

    service_states = snapshot.get("service_states") or {}
    if not isinstance(service_states, dict):
        service_states = {}
    return snapshot, service_states


def today_has_summary(db_session) -> bool:
    latest_summary = (
        db_session.query(DBIncident)
        .filter(
            DBIncident.source == MONITOR_SOURCE,
            DBIncident.event_type == "daily_summary",
        )
        .order_by(desc(DBIncident.id))
        .first()
    )
    if not latest_summary or not latest_summary.created_at:
        return False
    return latest_summary.created_at.date() == datetime.utcnow().date()


def classify_change(previous: dict[str, Any], current: dict[str, Any]) -> tuple[str, str]:
    previous_healthy = bool(previous.get("healthy")) if previous else None
    current_healthy = bool(current.get("healthy"))
    service_name = current.get("name", "service")

    if previous_healthy is False and current_healthy is True:
        return (
            f"{service_name} recovered",
            f"monitor-worker observed {service_name} return to a healthy state.",
        )
    if current_healthy is False:
        return (
            f"{service_name} became unhealthy",
            f"monitor-worker detected a failed health target for {service_name}.",
        )
    return (
        f"{service_name} state changed",
        f"monitor-worker recorded a status change for {service_name}.",
    )


def _format_service_list(names: list[str]) -> str:
    """Join names with commas and 'and' before the last item."""
    if len(names) <= 1:
        return names[0] if names else ""
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def log_change_events(db_session, previous_states: dict[str, dict[str, Any]], current_states: dict[str, dict[str, Any]]) -> None:
    if not current_states:
        return

    monitor_service = (
        db_session.query(DBService)
        .filter(DBService.name == "monitor-worker", DBService.is_active.is_(True))
        .first()
    )
    monitor_service_id = monitor_service.id if monitor_service else next(iter(current_states.values()))["id"]

    events_logged = 0
    for service_id, current_state in current_states.items():
        previous_state = previous_states.get(service_id, {})
        if previous_state and previous_state.get("healthy") == current_state.get("healthy") and previous_state.get("status") == current_state.get("status"):
            continue
        if not previous_state and current_state.get("healthy") is True:
            continue

        title, summary = classify_change(previous_state, current_state)
        severity = "high" if current_state.get("healthy") is False else "medium"
        status = "open" if current_state.get("healthy") is False else "resolved"
        to_state = "unhealthy" if current_state.get("healthy") is False else "healthy"
        service_state_changes_total.labels(
            service_name=current_state.get("name", "unknown"),
            to_state=to_state,
        ).inc()
        recent_changes = (
            f"Previous state: healthy={previous_state.get('healthy', 'unknown')}, "
            f"status={previous_state.get('status', 'unknown')}; "
            f"current state: healthy={current_state.get('healthy')}, "
            f"status={current_state.get('status', 'unknown')}"
        )
        record_incident_entry(
            db_session,
            title=title,
            affected_service_id=current_state["id"],
            severity=severity,
            summary=summary,
            symptoms=current_state.get("detail") or "status change detected by monitor-worker",
            recent_changes=recent_changes,
            status=status,
            source=MONITOR_SOURCE,
            event_type="failure" if current_state.get("healthy") is False else "recovery",
            overview_snapshot={
                "generated_at": datetime.utcnow().isoformat(),
                "service_states": current_states,
                "overview": compute_overview(db_session).model_dump(),
            },
            analysis={
                "previous_state": previous_state,
                "current_state": current_state,
            },
        )
        events_logged += 1

    if events_logged == 0 and all(state.get("healthy") is True for state in current_states.values()) and not today_has_summary(db_session):
        record_incident_entry(
            db_session,
            title="Daily platform health summary",
            affected_service_id=monitor_service_id,
            severity="low",
            summary="All monitored platform services were healthy in the latest sweep.",
            symptoms=_format_service_list(
                [state.get("name", "unknown") for state in current_states.values()]
            ) + " checks passed.",
            recent_changes="No state changes detected during the current monitor cycle.",
            status="resolved",
            source=MONITOR_SOURCE,
            event_type="daily_summary",
            overview_snapshot={
                "generated_at": datetime.utcnow().isoformat(),
                "service_states": current_states,
                "overview": compute_overview(db_session).model_dump(),
            },
            analysis={
                "healthy_service_count": sum(1 for state in current_states.values() if state.get("healthy")),
                "total_services": len(current_states),
            },
        )


def monitor_once(enable_probes: bool = True) -> None:
    db_session = SessionLocal()
    try:
        process_pending_action_jobs(db_session)
        if not enable_probes:
            return
        current_states = build_service_states(db_session)
        previous_snapshot, previous_states = load_previous_states(db_session)
        if not previous_snapshot:
            if all(state.get("healthy") is True for state in current_states.values()):
                log_change_events(db_session, {}, current_states)
            else:
                log_change_events(db_session, previous_states, current_states)
            return
        log_change_events(db_session, previous_states, current_states)
    finally:
        db_session.close()


def serve_health_server() -> tuple[ThreadingHTTPServer, threading.Thread]:
    httpd = ThreadingHTTPServer((MONITOR_HEALTH_HOST, MONITOR_HEALTH_PORT), MonitorHealthHandler)
    thread = threading.Thread(target=httpd.serve_forever, kwargs={"poll_interval": 1}, daemon=True)
    thread.start()
    return httpd, thread


def main() -> None:
    stop_event = threading.Event()
    httpd, health_thread = serve_health_server()

    def shutdown_handler(signum: int, frame: Any) -> None:  # noqa: ARG001
        stop_event.set()

    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    try:
        while not stop_event.is_set():
            monitor_once(enable_probes=MONITOR_PROBES_ENABLED)
            stop_event.wait(MONITOR_INTERVAL_SECONDS)
    finally:
        stop_event.set()
        httpd.shutdown()
        health_thread.join(timeout=5)
        httpd.server_close()


if __name__ == "__main__":
    main()
