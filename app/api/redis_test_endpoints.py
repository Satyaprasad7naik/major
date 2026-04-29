"""
Redis / Valkey connectivity test endpoints.
Mount once and hit the endpoints to verify your connection is working.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import redis

from app.core.config import settings

router = APIRouter(prefix="/redis-test", tags=["Redis Test"])

# Module-level client (lazy; created on first request)
_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    """Return a shared Redis client, creating one if needed."""
    global _client
    if _client is None:
        _client = redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    return _client


@router.get("/ping")
async def redis_ping():
    """
    Basic connectivity check — sends PING and returns PONG.
    """
    try:
        client = _get_client()
        result = client.ping()  # returns True on success
        return {
            "status": "ok",
            "ping": "PONG" if result else "FAIL",
            "redis_url": _mask_url(settings.REDIS_URL),
        }
    except (redis.ConnectionError, redis.TimeoutError) as e:
        raise HTTPException(status_code=503, detail=f"Redis connection failed: {e}")
    except redis.AuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Redis auth failed: {e}")


@router.get("/read-write")
async def redis_read_write():
    """
    Write a test key, read it back, then delete it.
    Confirms full read/write access.
    """
    test_key = "deriv:redis_test"
    test_value = f"hello-{datetime.now(timezone.utc).isoformat()}"

    try:
        client = _get_client()
        client.set(test_key, test_value, ex=30)  # 30s TTL
        read_back = client.get(test_key)
        client.delete(test_key)

        return {
            "status": "ok",
            "wrote": test_value,
            "read_back": read_back,
            "match": read_back == test_value,
        }
    except (redis.ConnectionError, redis.TimeoutError) as e:
        raise HTTPException(status_code=503, detail=f"Redis connection failed: {e}")
    except redis.AuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Redis auth failed: {e}")


@router.get("/info")
async def redis_info():
    """
    Return a subset of Redis INFO useful for quick diagnostics.
    """
    try:
        client = _get_client()
        info = client.info(section="server")
        return {
            "status": "ok",
            "redis_version": info.get("redis_version"),
            "uptime_seconds": info.get("uptime_in_seconds"),
            "connected_clients": client.info(section="clients").get("connected_clients"),
            "used_memory_human": client.info(section="memory").get("used_memory_human"),
        }
    except (redis.ConnectionError, redis.TimeoutError) as e:
        raise HTTPException(status_code=503, detail=f"Redis connection failed: {e}")
    except redis.AuthenticationError as e:
        raise HTTPException(status_code=401, detail=f"Redis auth failed: {e}")


# --------------- helpers ---------------

def _mask_url(url: str) -> str:
    """Mask password in a Redis URL for safe display."""
    try:
        # rediss://:SECRET@host:port/db  ->  rediss://:*****@host:port/db
        if "@" in url:
            scheme_auth, rest = url.rsplit("@", 1)
            scheme, _ = scheme_auth.split("://", 1)
            return f"{scheme}://:*****@{rest}"
    except Exception:
        pass
    return url
