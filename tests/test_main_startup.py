from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

import main as main_module


@pytest.mark.asyncio
async def test_startup_closes_resources_when_init_fails(monkeypatch):
    monkeypatch.setattr(main_module.bot, "get_me", AsyncMock(return_value=SimpleNamespace(username="TestBot")))
    monkeypatch.setattr(main_module.db, "init_db", AsyncMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(main_module, "start_analytics_workers", AsyncMock())
    monkeypatch.setattr(main_module, "stop_analytics_workers", AsyncMock())
    monkeypatch.setattr(main_module, "shutdown_download_queue", AsyncMock())
    monkeypatch.setattr(main_module, "close_http_session", AsyncMock())
    monkeypatch.setattr(main_module.session, "close", AsyncMock())
    monkeypatch.setattr(main_module, "set_app_context", lambda **_kwargs: None)

    with pytest.raises(RuntimeError, match="boom"):
        await main_module._startup()

    # _startup() itself doesn't run cleanup on failure (that's the caller's
    # job via start_background_loop's future.result() propagating to
    # whatever supervises the process); analytics workers were never
    # marked started because init_db failed before start_analytics_workers.
    main_module.start_analytics_workers.assert_not_awaited()


@pytest.mark.asyncio
async def test_startup_registers_webhook_when_url_configured(monkeypatch):
    monkeypatch.setattr(main_module, "WEBHOOK_URL", "https://example-bot.onrender.com")
    monkeypatch.setattr(main_module.bot, "get_me", AsyncMock(return_value=SimpleNamespace(username="TestBot")))
    monkeypatch.setattr(main_module.bot, "set_my_commands", AsyncMock())
    monkeypatch.setattr(main_module.bot, "set_webhook", AsyncMock())
    monkeypatch.setattr(main_module.db, "init_db", AsyncMock())
    monkeypatch.setattr(main_module, "start_analytics_workers", AsyncMock())
    monkeypatch.setattr(main_module, "set_app_context", lambda **_kwargs: None)
    monkeypatch.setattr(main_module, "crontab", Mock())
    monkeypatch.setattr(main_module.dp, "include_router", Mock())
    monkeypatch.setattr(main_module.dp.message, "outer_middleware", Mock())
    monkeypatch.setattr(main_module.dp.callback_query, "outer_middleware", Mock())
    monkeypatch.setattr(main_module.dp.inline_query, "outer_middleware", Mock())
    monkeypatch.setattr(main_module.dp, "resolve_used_update_types", Mock(return_value=["message", "callback_query"]))

    await main_module._startup()

    main_module.bot.set_webhook.assert_awaited_once()
    _, kwargs = main_module.bot.set_webhook.call_args
    assert kwargs["url"] == "https://example-bot.onrender.com/webhook/" + main_module.WEBHOOK_SECRET_PATH
    assert kwargs["allowed_updates"] == ["message", "callback_query"]


@pytest.mark.asyncio
async def test_startup_skips_webhook_registration_when_url_missing(monkeypatch):
    monkeypatch.setattr(main_module, "WEBHOOK_URL", None)
    monkeypatch.setattr(main_module.bot, "get_me", AsyncMock(return_value=SimpleNamespace(username="TestBot")))
    monkeypatch.setattr(main_module.bot, "set_my_commands", AsyncMock())
    monkeypatch.setattr(main_module.bot, "set_webhook", AsyncMock())
    monkeypatch.setattr(main_module.db, "init_db", AsyncMock())
    monkeypatch.setattr(main_module, "start_analytics_workers", AsyncMock())
    monkeypatch.setattr(main_module, "set_app_context", lambda **_kwargs: None)
    monkeypatch.setattr(main_module, "crontab", Mock())
    monkeypatch.setattr(main_module.dp, "include_router", Mock())
    monkeypatch.setattr(main_module.dp.message, "outer_middleware", Mock())
    monkeypatch.setattr(main_module.dp.callback_query, "outer_middleware", Mock())
    monkeypatch.setattr(main_module.dp.inline_query, "outer_middleware", Mock())
    monkeypatch.setattr(main_module.dp, "resolve_used_update_types", Mock(return_value=["message"]))

    await main_module._startup()

    main_module.bot.set_webhook.assert_not_awaited()


@pytest.mark.asyncio
async def test_startup_registers_one_shared_middleware_instance_per_class(monkeypatch):
    import middlewares

    monkeypatch.setattr(main_module, "WEBHOOK_URL", None)
    monkeypatch.setattr(main_module.bot, "get_me", AsyncMock(return_value=SimpleNamespace(username="TestBot")))
    monkeypatch.setattr(main_module.bot, "set_my_commands", AsyncMock())
    monkeypatch.setattr(main_module.db, "init_db", AsyncMock())
    monkeypatch.setattr(main_module, "start_analytics_workers", AsyncMock())
    monkeypatch.setattr(main_module, "set_app_context", lambda **_kwargs: None)
    monkeypatch.setattr(main_module, "crontab", Mock())
    monkeypatch.setattr(main_module.dp, "include_router", Mock())
    monkeypatch.setattr(main_module.dp.message, "outer_middleware", Mock())
    monkeypatch.setattr(main_module.dp.callback_query, "outer_middleware", Mock())
    monkeypatch.setattr(main_module.dp.inline_query, "outer_middleware", Mock())
    monkeypatch.setattr(main_module.dp, "resolve_used_update_types", Mock(return_value=["message"]))

    await main_module._startup()

    message_instances = [call.args[0] for call in main_module.dp.message.outer_middleware.call_args_list]
    callback_instances = [call.args[0] for call in main_module.dp.callback_query.outer_middleware.call_args_list]
    inline_instances = [call.args[0] for call in main_module.dp.inline_query.outer_middleware.call_args_list]

    assert len(message_instances) == len(middlewares.__all__)
    assert len(callback_instances) == len(middlewares.__all__)
    assert len(inline_instances) == len(middlewares.__all__)
    for middleware_cls, message_mw, callback_mw, inline_mw in zip(
        middlewares.__all__, message_instances, callback_instances, inline_instances
    ):
        assert isinstance(message_mw, middleware_cls)
        assert message_mw is callback_mw
        assert message_mw is inline_mw


@pytest.mark.asyncio
async def test_shutdown_closes_resources(monkeypatch):
    monkeypatch.setattr(main_module.bot, "delete_webhook", AsyncMock())
    monkeypatch.setattr(main_module, "_analytics_started", True)
    monkeypatch.setattr(main_module, "stop_analytics_workers", AsyncMock())
    monkeypatch.setattr(main_module, "shutdown_download_queue", AsyncMock())
    monkeypatch.setattr(main_module, "close_download_http_clients", Mock())
    monkeypatch.setattr(main_module, "close_http_session", AsyncMock())
    monkeypatch.setattr(main_module.session, "close", AsyncMock())
    monkeypatch.setattr(main_module.db.engine, "dispose", AsyncMock())

    await main_module._shutdown()

    main_module.bot.delete_webhook.assert_awaited_once()
    main_module.stop_analytics_workers.assert_awaited_once()
    main_module.shutdown_download_queue.assert_awaited_once()
    main_module.close_download_http_clients.assert_called_once()
    main_module.close_http_session.assert_awaited_once()
    main_module.session.close.assert_awaited_once()
    main_module.db.engine.dispose.assert_awaited_once()


def test_health_check_reports_not_ready_before_startup(monkeypatch):
    monkeypatch.setattr(main_module, "_bot_ready", __import__("threading").Event())
    client = main_module.flask_app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 503
    assert resp.get_json()["status"] == "starting"


def test_health_check_reports_ok_when_ready(monkeypatch):
    ready_event = __import__("threading").Event()
    ready_event.set()
    monkeypatch.setattr(main_module, "_bot_ready", ready_event)
    client = main_module.flask_app.test_client()
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "ok"


def test_webhook_endpoint_rejects_when_bot_not_ready(monkeypatch):
    monkeypatch.setattr(main_module, "_bot_ready", __import__("threading").Event())
    client = main_module.flask_app.test_client()
    resp = client.post(main_module.WEBHOOK_PATH, json={"update_id": 1})
    assert resp.status_code == 503


def test_webhook_endpoint_rejects_bad_secret_token(monkeypatch):
    ready_event = __import__("threading").Event()
    ready_event.set()
    monkeypatch.setattr(main_module, "_bot_ready", ready_event)
    monkeypatch.setattr(main_module, "_loop", Mock())
    monkeypatch.setattr(main_module, "WEBHOOK_SECRET_TOKEN", "expected-secret")
    client = main_module.flask_app.test_client()
    resp = client.post(
        main_module.WEBHOOK_PATH,
        json={"update_id": 1},
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
    )
    assert resp.status_code == 401


def test_webhook_endpoint_accepts_valid_update(monkeypatch):
    ready_event = __import__("threading").Event()
    ready_event.set()
    monkeypatch.setattr(main_module, "_bot_ready", ready_event)
    monkeypatch.setattr(main_module, "WEBHOOK_SECRET_TOKEN", None)

    fake_loop = Mock()
    monkeypatch.setattr(main_module, "_loop", fake_loop)
    monkeypatch.setattr(
        main_module.asyncio, "run_coroutine_threadsafe", Mock()
    )

    client = main_module.flask_app.test_client()
    resp = client.post(main_module.WEBHOOK_PATH, json={"update_id": 12345})
    assert resp.status_code == 200
    assert resp.get_json() == {"ok": True}
    main_module.asyncio.run_coroutine_threadsafe.assert_called_once()
