"""Legacy pipeline tests use a fixed authenticated principal, not anonymous API access.

Auth/security integration tests marked real_auth exercise the complete cookie and CSRF
stack without overriding authentication. Database fixtures still control their own DB.
"""
from datetime import datetime, timezone, timedelta
import pytest
from app.api.main import app
from app.core.auth import AuthContext, get_current_user

TEST_USER_ID = 'test-user'


@pytest.fixture(autouse=True)
def legacy_principal(request):
    if request.node.get_closest_marker('real_auth'):
        yield
        return
    previous = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: AuthContext(
        TEST_USER_ID, 'pipeline@example.test', 'test-session', 'test-csrf',
        datetime.now(timezone.utc) + timedelta(hours=1))
    yield
    if previous is None:
        app.dependency_overrides.pop(get_current_user, None)
    else:
        app.dependency_overrides[get_current_user] = previous
