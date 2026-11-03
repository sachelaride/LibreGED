import pytest

from app.auth import AVAILABLE_ROLES, has_module_access


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
