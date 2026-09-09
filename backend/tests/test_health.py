from app.core.config import settings


def test_root_endpoint(client):
    """Test that the root endpoint returns 200 OK and expected welcome payload."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "Welcome" in data["message"]
    assert data["version"] == settings.VERSION
    assert data["health"] == "/api/health"


def test_api_health_direct(client):
    """Test the direct /api/health endpoint used by the frontend connectivity check."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION
    assert data["environment"] == settings.ENVIRONMENT
    assert "timestamp" in data


def test_api_v1_health_endpoint(client):
    """Test the versioned /api/v1/health endpoint."""
    response = client.get(f"{settings.API_V1_STR}/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app_name"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION
    assert "timestamp" in data


def test_cors_headers(client):
    """Test that CORS preflight / headers respond properly for frontend origin."""
    response = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
