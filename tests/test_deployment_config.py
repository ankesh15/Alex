import os
from fastapi.testclient import TestClient
from app.config import Settings
from app.api.main import app
from app.api.v1.endpoints.documents import _safe_file_path


client = TestClient(app)


def test_cors_origins_parsing():
    s = Settings(
        ALLOWED_ORIGINS="https://app.vercel.app, http://localhost:5173",
        FRONTEND_URL="https://custom-domain.com/"
    )
    origins = s.cors_origins
    assert "https://app.vercel.app" in origins
    assert "http://localhost:5173" in origins
    assert "https://custom-domain.com" in origins
    # Ensure trailing slash was stripped
    assert "https://custom-domain.com/" not in origins


def test_cors_origins_deduplication():
    s = Settings(
        ALLOWED_ORIGINS="https://app.vercel.app",
        FRONTEND_URL="https://app.vercel.app"
    )
    origins = s.cors_origins
    assert origins.count("https://app.vercel.app") == 1


def test_database_url_normalization():
    railway_url = "postgres://postgres:securepass@roundhouse.proxy.rlwy.net:12345/railway"
    normalized = railway_url.replace("postgres://", "postgresql://", 1)
    assert normalized.startswith("postgresql://")


def test_health_check_endpoints():
    # Root health check
    res_root = client.get("/")
    assert res_root.status_code == 200
    data_root = res_root.json()
    assert data_root["status"] == "online"
    assert "platform" in data_root

    # Railway / health probe
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"status": "ok"}


def test_safe_file_path_defense():
    # Normal stored UUID filename
    safe_path = _safe_file_path("123e4567-e89b-12d3-a456-426614174000.pdf")
    assert safe_path is not None
    assert safe_path.endswith("123e4567-e89b-12d3-a456-426614174000.pdf")

    # Directory traversal attempts
    assert _safe_file_path("../../etc/passwd") is None
    assert _safe_file_path("../../../app/config.py") is None
    assert _safe_file_path("/etc/shadow") is None
    assert _safe_file_path("") is None
    assert _safe_file_path(None) is None


def test_storage_dir_exists_on_startup():
    from app.config import settings
    assert os.path.exists(settings.STORAGE_DIR)
