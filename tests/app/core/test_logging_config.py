import logging


def _reset_logging_config_singleton() -> None:
    # Import inside helper so tests can control env first.
    from app.core import logging_config as lc

    lc.LoggingConfig._instance = None
    lc.LoggingConfig._initialized = False


def test_log_format_defaults_to_text(monkeypatch):
    # Be explicit to avoid failures if the runner environment already sets LOG_FORMAT.
    monkeypatch.setenv("LOG_FORMAT", "text")
    _reset_logging_config_singleton()

    from app.core.logging_config import LoggingConfig, JsonLineFormatter

    LoggingConfig()
    app_logger = logging.getLogger("app")
    assert app_logger.handlers, "expected a handler to be installed for 'app' logger"
    assert not isinstance(app_logger.handlers[0].formatter, JsonLineFormatter)


def test_log_format_can_be_json(monkeypatch):
    monkeypatch.setenv("LOG_FORMAT", "json")
    _reset_logging_config_singleton()

    from app.core.logging_config import LoggingConfig, JsonLineFormatter

    LoggingConfig()

    for name in ("app", "uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        assert (
            logger.handlers
        ), f"expected a handler to be installed for '{name}' logger"
        assert any(
            isinstance(h.formatter, JsonLineFormatter) for h in logger.handlers
        ), f"expected JsonLineFormatter for '{name}' logger handlers"
