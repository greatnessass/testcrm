"""Тесты эндпоинта звонков: POST /calls."""

from datetime import datetime, timedelta, timezone

ALMATY = timezone(timedelta(hours=5))


def _make_manager(client):
    resp = client.post("/managers", json={
        "name": "Manager", "email": "m@example.com", "phone": "+77700000000"
    })
    assert resp.status_code == 201, resp.json()  # Создали менеджера
    return resp.json()


def _make_company(client):
    resp = client.post("/companies", json={
        "name": "Company", "bin": "1111111111111", "phone": "+77700000000"
    })
    assert resp.status_code == 201, resp.json()  # Создали организацию
    return resp.json()


def _make_meeting(client, manager_id, company_id, scheduled_at_utc):
    resp = client.post("/meetings", json={
        "manager_id": manager_id,
        "company_id": company_id,
        "scheduled_at": scheduled_at_utc,
    })
    assert resp.status_code == 201, resp.json()  # Встреча создана
    return resp.json()


def test_call_meeting_set_without_meeting_id_fails(client):
    """Звонок с результатом meeting_set без meeting_id — ошибка валидации (требование №5)."""
    manager = _make_manager(client)
    company = _make_company(client)
    resp = client.post("/calls", json={
        "company_id": company["id"],
        "manager_id": manager["id"],
        "result": "meeting_set",
    })
    assert resp.status_code == 422, resp.json()  # Ошибка валидации: нет meeting_id


def test_call_meeting_set_with_valid_meeting_succeeds(client):
    """Звонок с meeting_set и существующей встречей — успех."""
    manager = _make_manager(client)
    company = _make_company(client)
    # Среда 2026-11-18, 17:00 Алматы = 12:00 UTC
    meeting = _make_meeting(client, manager["id"], company["id"], "2026-11-18T12:00:00+00:00")
    resp = client.post("/calls", json={
        "company_id": company["id"],
        "manager_id": manager["id"],
        "result": "meeting_set",
        "meeting_id": meeting["id"],
    })
    assert resp.status_code == 201, resp.json()  # Звонок создан со связью на встречу
    assert resp.json()["meeting_id"] == meeting["id"]  # meeting_id сохранён


def test_call_no_answer_succeeds(client):
    """Звонок с результатом no_answer без meeting_id — успех."""
    manager = _make_manager(client)
    company = _make_company(client)
    resp = client.post("/calls", json={
        "company_id": company["id"],
        "manager_id": manager["id"],
        "result": "no_answer",
    })
    assert resp.status_code == 201, resp.json()  # Звонок без встречи допустим


def test_call_refused_succeeds(client):
    """Звонок с результатом refused без meeting_id — успех."""
    manager = _make_manager(client)
    company = _make_company(client)
    resp = client.post("/calls", json={
        "company_id": company["id"],
        "manager_id": manager["id"],
        "result": "refused",
    })
    assert resp.status_code == 201, resp.json()  # Звонок без встречи допустим


def test_call_meeting_set_invalid_meeting_id_fails(client):
    """Звонок meeting_set с несуществующим meeting_id — ошибка валидации."""
    manager = _make_manager(client)
    company = _make_company(client)
    resp = client.post("/calls", json={
        "company_id": company["id"],
        "manager_id": manager["id"],
        "result": "meeting_set",
        "meeting_id": 99999,
    })
    assert resp.status_code == 422, resp.json()  # Встреча не найдена