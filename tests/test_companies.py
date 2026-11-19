"""Тесты эндпоинта организаций: POST /companies, GET /companies?status=."""


def _make_company(client, bin_val="1111111111111", status="new"):
    """Создаёт организацию через API и возвращает JSON-ответ."""
    resp = client.post("/companies", json={
        "name": "Company", "bin": bin_val, "phone": "+77700000000", "status": status
    })
    assert resp.status_code == 201, resp.json()  # Ожидаем успешное создание
    return resp.json()


def test_create_company(client):
    """Создание организации с валидными данными."""
    resp = client.post("/companies", json={
        "name": "ТОО Альфа", "bin": "1234567890123", "phone": "+77777777777"
    })
    assert resp.status_code == 201, resp.json()  # Ожидаем 201 Created
    data = resp.json()
    assert data["name"] == "ТОО Альфа"  # Название сохранено верно
    assert data["bin"] == "1234567890123"  # БИН сохранён верно
    assert data["status"] == "new"  # По умолчанию статус «new»


def test_create_company_duplicate_bin(client):
    """Повторный БИН должен приводить к ошибке уникальности."""
    _make_company(client, bin_val="1111111111111")
    resp = client.post("/companies", json={
        "name": "Другая", "bin": "1111111111111", "phone": "+77700000000"
    })
    assert resp.status_code in (400, 409, 422), resp.json()  # Конфликт уникальности БИН


def test_list_companies_all(client):
    """Список всех организаций без фильтра по статусу."""
    _make_company(client, bin_val="1111111111111")
    _make_company(client, bin_val="2222222222222")
    resp = client.get("/companies")
    assert resp.status_code == 200, resp.json()  # Успешный ответ
    data = resp.json()
    assert len(data["items"]) == 2  # Две организации созданы


def test_list_companies_with_status_filter(client):
    """Фильтрация организаций по статусу."""
    _make_company(client, bin_val="1111111111111", status="new")
    _make_company(client, bin_val="2222222222222", status="closed_won")
    resp = client.get("/companies?status=closed_won")
    assert resp.status_code == 200, resp.json()  # Успешный ответ с фильтром
    data = resp.json()
    assert len(data["items"]) == 1  # Только одна организация со статусом closed_won
    assert data["items"][0]["status"] == "closed_won"  # Статус совпадает

    resp2 = client.get("/companies?status=new")
    assert resp2.status_code == 200
    assert len(resp2.json()["items"]) == 1  # Только одна организация со статусом new