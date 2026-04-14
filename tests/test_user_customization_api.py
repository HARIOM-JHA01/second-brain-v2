from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from agente_rolplay.db.auth import get_current_user
from agente_rolplay.db.database import get_db
from agente_rolplay.db.models import Profile
from agente_rolplay.routers.users import _CUSTOMIZE_DEFAULTS, router


class FakeQuery:
    def __init__(self, profile):
        self._profile = profile

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self._profile


class FakeDB:
    def __init__(self, profile):
        self.profile = profile
        self.commit_count = 0

    def query(self, model):
        assert model is Profile
        return FakeQuery(self.profile)

    def commit(self):
        self.commit_count += 1

    def refresh(self, _obj):
        return None


def _build_app(fake_db, with_auth=True):
    app = FastAPI()
    app.include_router(router)

    def _override_get_db():
        yield fake_db

    app.dependency_overrides[get_db] = _override_get_db

    if with_auth:
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())

    return app


def test_customization_get_returns_defaults_when_empty():
    profile = SimpleNamespace(settings={})
    app = _build_app(FakeDB(profile), with_auth=True)
    client = TestClient(app)

    res = client.get('/api/users/customization')

    assert res.status_code == 200
    body = res.json()
    for key, expected in _CUSTOMIZE_DEFAULTS.items():
        assert body[key] == expected


def test_customization_put_persists_and_get_returns_saved_values():
    profile = SimpleNamespace(settings={})
    fake_db = FakeDB(profile)
    app = _build_app(fake_db, with_auth=True)
    client = TestClient(app)

    payload = {
        'primary_color': '#112233',
        'secondary_color': '#445566',
        'tertiary_color': '#778899',
        'font_family': 'manrope',
        'font_scale': 'large',
        'theme_mode': 'light',
        'language': 'en',
    }

    save_res = client.put('/api/users/customization', json=payload)
    assert save_res.status_code == 200
    save_body = save_res.json()
    for key, expected in payload.items():
        assert save_body[key] == expected
    assert 'updated_at' in save_body
    assert fake_db.commit_count == 1

    get_res = client.get('/api/users/customization')
    assert get_res.status_code == 200
    get_body = get_res.json()
    for key, expected in payload.items():
        assert get_body[key] == expected


def test_customization_put_rejects_invalid_values_with_400():
    profile = SimpleNamespace(settings={})
    app = _build_app(FakeDB(profile), with_auth=True)
    client = TestClient(app)

    bad_color = dict(_CUSTOMIZE_DEFAULTS)
    bad_color['primary_color'] = 'red'
    res_color = client.put('/api/users/customization', json=bad_color)
    assert res_color.status_code == 400

    bad_enum = dict(_CUSTOMIZE_DEFAULTS)
    bad_enum['font_scale'] = 'xl'
    res_enum = client.put('/api/users/customization', json=bad_enum)
    assert res_enum.status_code == 400


def test_customization_endpoints_require_auth():
    profile = SimpleNamespace(settings={})
    app = _build_app(FakeDB(profile), with_auth=False)
    client = TestClient(app)

    res = client.get('/api/users/customization')
    assert res.status_code == 401
