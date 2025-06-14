import pytest
from fastapi import APIRouter

try:
    from .. import allowance_ext
except ImportError:
    # For CI environment, import from relative path
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from __init__ import allowance_ext


# just import router and add it to a test router
@pytest.mark.asyncio
async def test_router():
    router = APIRouter()
    router.include_router(allowance_ext)
