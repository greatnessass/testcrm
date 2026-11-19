"""Тесты эндпоинта встреч: POST /meetings, PATCH /meetings/{id}.

Критические сценарии:
- граница рабочего дня: 17:30 — отказ, 17:00 — успех, 08:30 — отказ;
- пересечение встреч у менеджера;
- смежные слоты (10:00–11:00 и 11:00–12:00) — не конфликт;
- две активные встречи у одной организации с разными менеджерами — конфликт;
- перенос встречи сохраняет историю (original_scheduled_at).
"""

from datetime import datetime, timedelta, timezone

ALMATY = timezone(timedelta(hours=5))

# Среда 2026-11-18. Проверяем соответствие:
#   17:00 Алматы = 12:00 UTC  (встреча 17:00–18:00, укладывается в 18:00 -> успех)
#   17:30 Алматы = 12:30 UTC  (встреча 17:30–18:30, не укладывается -> отказ)
#   08:30 Алматы = 03:30 UTC  (до 09:00 -> отказ)
#   10:00 Алматы = 05:00 UTC  (встреча 10:00–11:00)
#   11:00 Алматы = 06:00 UTC  (встреча 11:00–12:00, смежная с предыдущей)


def _make_manager(client, email="m@example.com"):
    resp = client.post("/managers", json={
        "name": "Manager", "email": email, "phone": "+77700000000"
    })
    assert resp.status_code == 201, resp.json()  # Создали менеджера
    return resp.json()


def _make_company(client, bin_val="1111111111111"):
    resp = client.post("/companies", json={
        "name": "Company", "bin": bin_val, "phone": "+77700000000"
    })
    assert resp.status_code == 201, resp.json()  # Создали организацию
    return resp.json()


def _make_meeting(client, manager_id, company_id, scheduled_at_utc):
    resp = client.post("/meetings", json={
        "manager_id": manager_id,
        "company_id": company_id,
        "scheduled_at": scheduled_at_utc,
    })
    return resp


def test_meeting_at_1700_succeeds(client):
    """Встреча в 17:00 Алматы (12:00 UTC) успешна — укладывается ровно до 18:00."""
    manager = _make_manager(client)
    company = _make_company(client)
    resp = _make_meeting(client, manager["id"], company["id"], "2026-11-18T12:00:00+00:00")
    assert resp.status_code == 201, resp.json()  # 17:00–18:00 Алматы — в рабочие часы


def test_meeting_at_1730_fails(client):
    """Встреча в 17:30 Алматы (12:30 UTC) — отказ, не укладывается в рабочий день."""
    manager = _make_manager(client)
    company = _make_company(client)
    resp = _make_meeting(client, manager["id"], company["id"], "2026-11-18T12:30:00+00:00")
    assert resp.status_code == 422, resp.json()  # 17:30–18:30 выходит за 18:00 Алматы


def test_meeting_at_0830_fails(client):
    """Встреча в 08:30 Алматы (03:30 UTC) — отказ, начало до 09:00."""
    manager = _make_manager(client)
    company = _make_company(client)
    resp = _make_meeting(client, manager["id"], company["id"], "2026-11-18T03:30:00+00:00")
    assert resp.status_code == 422, resp.json()  # 08:30 до начала рабочего дня


def test_meeting_on_weekend_fails(client):
    """Встреча в субботу — отказ, рабочие дни только пн–пт."""
    # 2026-11-21 — суббота. 10:00 Алматы = 05:00 UTC.
    manager = _make_manager(client)
    company = _make_company(client)
    resp = _make_meeting(client, manager["id"], company["id"], "2026-11-21T05:00:00+00:00")
    assert resp.status_code == 422, resp.json()  # Суббота не рабочий день


def test_manager_overlap_conflict(client):
    """Две пересекающиеся встречи у одного менеджера — вторая отказ 409 (требование №3)."""
    manager = _make_manager(client)
    company1 = _make_company(client, bin_val="1111111111111")
    company2 = _make_company(client, bin_val="2222222222222")

    # Первая встреча 10:00–11:00 Алматы (05:00 UTC)
    resp1 = _make_meeting(client, manager["id"], company1["id"], "2026-11-18T05:00:00+00:00")
    assert resp1.status_code == 201, resp1.json()  # Первая встреча создана

    # Вторая встреча 10:30–11:30 Алматы (05:30 UTC) — пересекается с первой
    resp2 = _make_meeting(client, manager["id"], company2["id"], "2026-11-18T05:30:00+00:00")
    assert resp2.status_code == 409, resp2.json()  # Пересечение с существующей встречей


def test_adjacent_slots_ok(client):
    """Смежные слоты 10:00–11:00 и 11:00–12:00 — не конфликт (требование №3)."""
    manager = _make_manager(client)
    company1 = _make_company(client, bin_val="1111111111111")
    company2 = _make_company(client, bin_val="2222222222222")

    resp1 = _make_meeting(client, manager["id"], company1["id"], "2026-11-18T05:00:00+00:00")
    assert resp1.status_code == 201, resp1.json()  # 10:00–11:00 Алматы

    resp2 = _make_meeting(client, manager["id"], company2["id"], "2026-11-18T06:00:00+00:00")
    assert resp2.status_code == 201, resp2.json()  # 11:00–12:00 Алматы — смежный, не конфликтует


def test_company_conflict_different_managers(client):
    """Две активные встречи у одной организации с разными менеджерами — конфликт (требование №4)."""
    manager1 = _make_manager(client, email="m1@example.com")
    manager2 = _make_manager(client, email="m2@example.com")
    company = _make_company(client, bin_val="1111111111111")

    # Встреча менеджера 1 в 10:00–11:00 Алматы (05:00 UTC)
    resp1 = _make_meeting(client, manager1["id"], company["id"], "2026-11-18T05:00:00+00:00")
    assert resp1.status_code == 201, resp1.json()  # Первая встреча создана

    # Встреча менеджера 2 в 10:30–11:30 Алматы (05:30 UTC) на ту же организацию — конфликт
    resp2 = _make_meeting(client, manager2["id"], company["id"], "2026-11-18T05:30:00+00:00")
    assert resp2.status_code == 409, resp2.json()  # У компании уже активная встреча


def test_reschedule_keeps_history(client):
    """Перенос встречи сохраняет original_scheduled_at и историю (требование №6)."""
    manager = _make_manager(client)
    company = _make_company(client)

    # Создаём встречу в 10:00 Алматы (05:00 UTC)
    resp = _make_meeting(client, manager["id"], company["id"], "2026-11-18T05:00:00+00:00")
    assert resp.status_code == 201, resp.json()
    meeting_id = resp.json()["id"]

    # Переносим на 14:00 Алматы (09:00 UTC)
    resp2 = client.patch(f"/meetings/{meeting_id}", json={
        "action": "reschedule",
        "scheduled_at": "2026-11-18T09:00:00+00:00",
    })
    assert resp2.status_code == 200, resp2.json()  # Перенос успешен
    data = resp2.json()
    assert data["scheduled_at"].startswith("2026-11-18T09:00:00")  # Новое время
    assert data["original_scheduled_at"] is not None  # Сохранено первое время
    assert data["original_scheduled_at"].startswith("2026-11-18T05:00:00")  # Исходное время


def test_cancel_meeting(client):
    """Отмена встречи — успех, статус становится cancelled."""
    manager = _make_manager(client)
    company = _make_company(client)

    resp = _make_meeting(client, manager["id"], company["id"], "2026-11-18T05:00:00+00:00")
    meeting_id = resp.json()["id"]

    resp2 = client.patch(f"/meetings/{meeting_id}", json={"action": "cancel"})
    assert resp2.status_code == 200, resp2.json()  # Отмена успешна
    assert resp2.json()["status"] == "cancelled"  # Статус cancelled