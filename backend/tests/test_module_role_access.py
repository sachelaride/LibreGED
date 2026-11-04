import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import (
    AVAILABLE_ROLES,
    create_access_token,
    get_current_active_user,
    has_module_access,
    require_module_access,
)
from app.main import app
from app.models import User

client = TestClient(app)


@pytest.mark.parametrize(
    ("role", "module", "expected"),
    [
        ("secretaria", "secretaria", True),
        ("secretaria", "sead", True),
        ("secretaria", "coordenacao", False),
        ("coordenador", "coordenacao", True),
        ("coordenador", "professores", False),
        ("professor", "professores", True),
        ("professor", "secretaria", False),
        ("professor", "ead", True),
        ("tutor", "ead", True),
        ("tutor", "professores", False),
        ("admin_instituicao", "financeiro", True),
        ("role_inexistente", "secretaria", False),
        ("professor", "modulo_inexistente", False),
    ],
)
def test_module_role_access_matrix(role, module, expected):
    assert has_module_access(role, module) is expected


def test_module_names_are_normalized():
    assert has_module_access("tutor", " EAD ")


@pytest.mark.parametrize(
    "role",
    ["secretaria", "coordenador", "professor", "tutor", "admin_global", "admin_instituicao"],
)
def test_operational_roles_can_be_assigned(role):
    assert role in AVAILABLE_ROLES


@pytest.mark.parametrize(
    ("role", "selected_module", "expected_status"),
    [
        ("admin_instituicao", "financeiro", None),
        ("admin_instituicao", "secretaria", 403),
        ("recepcao", "secretaria", 403),
    ],
)
def test_module_guard_enforces_selected_module_and_role(
    role, selected_module, expected_status
):
    user = User(
        id="module-guard-user",
        username="module_guard_user",
        hashed_password="unused",
        role=role,
    )
    token = create_access_token({
        "sub": user.username,
        "role": role,
        "module": selected_module,
    })
    guard = require_module_access("financeiro")

    if expected_status is None:
        assert guard(user=user, token=token) is user
        return

    with pytest.raises(HTTPException) as error:
        guard(user=user, token=token)
    assert error.value.status_code == expected_status


@pytest.mark.parametrize(
    ("path", "required_module"),
    [
        ("/admin/dashboard", "admin"),
        ("/sead/dashboard", "sead"),
        ("/secretaria/dashboard", "secretaria"),
        ("/ead/dashboard", "ead"),
        ("/professores/dashboard", "professores"),
        ("/ged/dashboard", "ged"),
        ("/financeiro/dashboard", "financeiro"),
        ("/coordenacao/dashboard", "coordenacao"),
        ("/aluno/dashboard", "aluno"),
    ],
)
def test_module_routes_reject_tokens_for_another_module(
    path, required_module, monkeypatch
):
    user = User(
        id="module-route-user",
        username="module_route_user",
        hashed_password="unused",
        role="admin_global",
    )
    monkeypatch.setitem(
        app.dependency_overrides,
        get_current_active_user,
        lambda: user,
    )
    token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "module": "modulo_incorreto",
    })

    response = client.get(
        path,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        f"Module mismatch. Required module: {required_module}"
    )


def test_module_route_rejects_unauthorized_role_with_correct_module(monkeypatch):
    user = User(
        id="restricted-module-user",
        username="restricted_module_user",
        hashed_password="unused",
        role="recepcao",
    )
    monkeypatch.setitem(
        app.dependency_overrides,
        get_current_active_user,
        lambda: user,
    )
    token = create_access_token({
        "sub": user.username,
        "role": user.role,
        "module": "financeiro",
    })

    response = client.get(
        "/financeiro/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Module access denied for this role"
