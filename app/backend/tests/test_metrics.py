import os

os.environ["DATABASE_URL"] = "sqlite://"

import pytest


def test_metrics_endpoint_returns_200(client):
    response = client.get("/metrics")
    assert response.status_code == 200


def test_metrics_endpoint_content_type(client):
    response = client.get("/metrics")
    assert "text/plain" in response.headers["content-type"]


def test_metrics_endpoint_contains_http_requests_total(client):
    # Trigger at least one request so the counter exists in the output
    client.get("/health")
    response = client.get("/metrics")
    assert "http_requests_total" in response.text


def test_metrics_endpoint_not_in_openapi_schema(client):
    response = client.get("/openapi.json")
    assert "/metrics" not in response.text


def test_metrics_endpoint_contains_backend_metric_names(client):
    response = client.get("/metrics")
    text = response.text
    assert "incidents_created_total" in text
    assert "service_action_jobs_total" in text
    assert "incident_assistant_requests_total" in text
    assert "http_request_duration_seconds" in text
