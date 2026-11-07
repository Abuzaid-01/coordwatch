"""Integration tests for CoordWatch FastAPI routes."""
from fastapi.testclient import TestClient
import pytest

from backend.app.main import app
from backend.app.db import init_db

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def setup_database():
    init_db()


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "coordwatch-fastapi"
    assert "jetstream" in data


def test_topics_list_and_seed():
    resp = client.get("/topics")
    assert resp.status_code == 200
    data = resp.json()
    assert "topics" in data
    assert len(data["topics"]) >= 1
    assert data["topics"][0]["keyword"] == "clean air zone"


def test_topic_summary():
    resp = client.get("/topics/1/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["topicId"] == 1
    assert data["postCount"] > 0
    assert data["clusterCount"] >= 1


def test_topic_graph():
    resp = client.get("/topics/1/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data
    assert "links" in data
    assert len(data["nodes"]) > 0


def test_topic_clusters():
    resp = client.get("/topics/1/clusters")
    assert resp.status_code == 200
    data = resp.json()
    assert "clusters" in data
    assert len(data["clusters"]) >= 1
    first_cluster = data["clusters"][0]
    assert "id" in first_cluster
    assert "score" in first_cluster
    assert "reasons" in first_cluster


def test_topic_timeline():
    resp = client.get("/topics/1/timeline")
    assert resp.status_code == 200
    data = resp.json()
    assert "timeline" in data
    assert isinstance(data["timeline"], list)


def test_evaluation_latest():
    resp = client.get("/evaluation/latest")
    assert resp.status_code == 200
    data = resp.json()
    if data.get("status") == "not_run":
        assert "detail" in data
        return
    assert "precision" in data or "devSummary" in data

