"""Тесты эндпоинта расписания: GET /managers/{id}/schedule?date=."""


def _make_manager(client):
    resp = client.post("/managers", json={
        "name": "Manager", "email": "m@example.com", "phone": "+77700000000"
    })
    assert resp.status_code == 201, resp.json()  # Создали менеджера
    return resp.json()


def _make_company(client, bin_val="1111111111111"):
    resp = client.post("/companies", json={
        "name": "Company", "bin": bin_val, "phone": "+77700000000"
    })
    assert resp.status_code == 201, resp.json()  # Создали организацию
    return resp.json()


def test_schedule_empty(client):
    """Расписание менеджера без встреч — пустой список."""
    manager = _make_manager(client)
    resp = client.get(f"/managers/{manager['id']}/schedule?date=2026-11-18")
    assert resp.status_code == 200, resp.json()  # Успешный ответ
    data = resp.json()
    assert data["manager_id"] == manager["id"]  # ID менеджера в ответе
    assert data["date"] == "2026-11-18"  # Запрашиваемая дата
    assert data["meetings"] == []  # Нет встреч


def test_schedule_returns_meetings(client):
    """Расписание возвращает встречи менеджера на указанную дату."""
    manager = _make_manager(client)
    company = _make_company(client)

    # Встреча в 10:00 Алматы = 05:00 UTC на 2026-11-18
    client.post("/meetings", json={
        "manager_id": manager["id"],
        "company_id": company["id"],
        "scheduled_at": "2026-11-18T05:00:00+00:00",
    })

    resp = client.get(f"/managers/{manager['id']}/schedule?date=2026-11-18")
    assert resp.status_code == 200, resp.json()  # Успешный ответ
    data = resp.json()
    assert len(data["meetings"]) == 1  # Одна встреча на день
    # 05:00 UTC = 10:00 Алматы
    assert data["meetings"][0]["scheduled_at_almaty"].startswith("2026-11-18T10:00")  # Время в Алматы


def test_schedule_only_scheduled_meetings(client):
    """Отменённые встречи не попадают в расписание."""
    manager = _make_manager(client)
    company = _make_company(client)

    resp = client.post("/meetings", json={
        "manager_id": manager["id"],
        "company_id": company["id"],
        "scheduled_at": "2026-11-18T05:00:00+00:00",
    })
    meeting_id = resp.json()["id"]

    # Отменяем встречу
    client.patch(f"/meetings/{meeting_id}", json={"action": "cancel"})

    resp = client.get(f"/managers/{manager['id']}/schedule?date=2026-11-18")
    assert resp.status_code == 200, resp.json()
    data = resp.json()
    assert len(data["meetings"]) == 0  # Отменённая встреча не в расписании


def test_schedule_wrong_date_format_fails(client):
    """Неверный формат date — ошибка 422."""
    manager = _make_manager(client)
    resp = client.get(f"/managers/{manager['id']}/schedule?date=18-11-2026")
    assert resp.status_code == 422, resp.json()  # Неверный формат даты


def test_schedule_manager_not_found(client):
    """Расписание несуществующего менеджера — 404."""
    resp = client.get("/managers/99999/schedule?date=2026-11-18")
    assert resp.status_code == 404, resp.json()  # Менеджер не найден