import pytest
from fastapi import HTTPException
from redis.exceptions import RedisError

from apps.api.routes import auth


class _FakePipeline:
    def __init__(self, store):
        self.store = store
        self.key = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def incr(self, key):
        self.key = key
        return self

    def expire(self, _key, _seconds):
        return self

    def execute(self):
        self.store.counts[self.key] = self.store.counts.get(self.key, 0) + 1
        return [self.store.counts[self.key], True]


class _FakeRateStore:
    def __init__(self):
        self.counts = {}

    def pipeline(self, transaction=True):
        assert transaction is True
        return _FakePipeline(self)

    def delete(self, key):
        self.counts.pop(key, None)


def test_login_limiter_is_shared_by_hashed_account_key(monkeypatch):
    store = _FakeRateStore()
    monkeypatch.setattr(auth, "_login_rate_store", store)

    keys = [auth._enforce_login_rate_limit(" BYET ") for _ in range(5)]
    assert len(set(keys)) == 1
    assert "byet" not in keys[0]

    with pytest.raises(HTTPException) as blocked:
        auth._enforce_login_rate_limit("byet")
    assert blocked.value.status_code == 429

    auth._clear_login_rate_limit(keys[0])
    assert auth._enforce_login_rate_limit("byet") == keys[0]


def test_login_limiter_fails_closed_when_redis_is_unavailable(monkeypatch):
    class _BrokenStore:
        def pipeline(self, transaction=True):
            raise RedisError("offline")

    monkeypatch.setattr(auth, "_login_rate_store", _BrokenStore())
    with pytest.raises(HTTPException) as unavailable:
        auth._enforce_login_rate_limit("byet")
    assert unavailable.value.status_code == 503
