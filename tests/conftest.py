from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

import src.app as app_module


INITIAL_ACTIVITIES = deepcopy(app_module.activities)


@pytest.fixture(autouse=True)
def isolated_activities(monkeypatch):
    activities = deepcopy(INITIAL_ACTIVITIES)
    monkeypatch.setattr(app_module, "activities", activities)
    return activities


@pytest.fixture
def client(isolated_activities):
    with TestClient(app_module.app) as test_client:
        yield test_client