import pytest
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.exceptions import ConfigurationError

ENV_VARS = [
    "ENVIRONMENT", "LOG_LEVEL", "MONGODB_URI", "DATABASE_NAME", "MONGODB_TIMEOUT_MS",
    "BACKEND_HOST", "BACKEND_PORT", "FRONTEND_URL", "CORS_EXTRA_ORIGINS",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_defaults_work_without_any_environment():
    s = Settings(_env_file=None)
    assert s.mongodb_uri == "mongodb://localhost:27017"
    assert s.database_name == "risk_intelligence"
    assert s.backend_port == 8000
    assert s.frontend_url == "http://localhost:5173"
    assert s.log_level == "INFO"


def test_environment_variables_override_defaults(monkeypatch):
    monkeypatch.setenv("BACKEND_PORT", "9001")
    monkeypatch.setenv("DATABASE_NAME", "custom_db")
    s = Settings(_env_file=None)
    assert s.backend_port == 9001
    assert s.database_name == "custom_db"


@pytest.mark.parametrize("uri", ["", "   ", "localhost:27017", "http://localhost:27017"])
def test_invalid_mongodb_uri_is_rejected(uri):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, mongodb_uri=uri)


@pytest.mark.parametrize("name", ["", "bad name", "a.b", "a/b", 'q"x'])
def test_invalid_database_name_is_rejected(name):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_name=name)


@pytest.mark.parametrize("port", [0, 70000])
def test_invalid_port_is_rejected(port):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, backend_port=port)


def test_log_level_is_normalised_and_validated():
    assert Settings(_env_file=None, log_level="debug").log_level == "DEBUG"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, log_level="LOUD")


def test_cors_origins_are_normalised_and_deduplicated():
    s = Settings(
        _env_file=None,
        frontend_url="https://app.example.com/",
        cors_extra_origins="https://app.example.com, http://localhost:3000/ ",
    )
    assert s.cors_origins == ["https://app.example.com", "http://localhost:3000"]


def test_masked_uri_hides_credentials():
    s = Settings(
        _env_file=None,
        mongodb_uri="mongodb+srv://alice:s3cr3t@cluster0.example.mongodb.net/?retryWrites=true",
    )
    assert "s3cr3t" not in s.masked_mongodb_uri
    assert "alice" not in s.masked_mongodb_uri
    assert "cluster0.example.mongodb.net" in s.masked_mongodb_uri


def test_get_settings_raises_readable_error(monkeypatch):
    monkeypatch.setenv("MONGODB_URI", "not-a-uri")
    with pytest.raises(ConfigurationError) as excinfo:
        get_settings()
    assert "MONGODB_URI" in str(excinfo.value)