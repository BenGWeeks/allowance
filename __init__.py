import asyncio

from fastapi import APIRouter
from loguru import logger

# Monkey-patch WalletTypeInfo to add missing attributes
try:
    from lnbits.core.models.wallets import WalletTypeInfo

    # Add properties that delegate to the wrapped wallet
    def make_property(attr_name):
        def getter(self):
            return (
                getattr(self.wallet, attr_name, None)
                if hasattr(self, "wallet")
                else None
            )

        return property(getter)

    # Add all common wallet attributes
    for attr in ["id", "name", "adminkey", "inkey", "user", "balance_msat"]:
        if not hasattr(WalletTypeInfo, attr):
            setattr(WalletTypeInfo, attr, make_property(attr))

    logger.info("✅ Added wallet properties to WalletTypeInfo")

except ImportError:
    try:
        # Try alternative import path
        from lnbits.core.models import WalletTypeInfo

        # Add properties that delegate to the wrapped wallet
        def make_property(attr_name):
            def getter(self):
                return (
                    getattr(self.wallet, attr_name, None)
                    if hasattr(self, "wallet")
                    else None
                )

            return property(getter)

        # Add all common wallet attributes
        for attr in ["id", "name", "adminkey", "inkey", "user", "balance_msat"]:
            if not hasattr(WalletTypeInfo, attr):
                setattr(WalletTypeInfo, attr, make_property(attr))

        logger.info("✅ Added wallet properties to WalletTypeInfo")
    except ImportError:
        logger.info("WalletTypeInfo not found, skipping patch")
except Exception as e:
    logger.warning(f"Could not patch WalletTypeInfo: {e}")

from .crud import db
from .tasks import check_and_process_allowances
from .views import allowance_generic_router
from .views_api import allowance_api_router

# from .views_lnurl import allowance_lnurl_router  # Disabled - has invalid decorators

logger.debug(
    "This logged message is from allowance/__init__.py, you can debug in your "
    "extension using 'import logger from loguru' and 'logger.debug(<thing-to-log>)'."
)


allowance_ext: APIRouter = APIRouter(prefix="/allowance", tags=["Allowance"])
allowance_ext.include_router(allowance_generic_router)
allowance_ext.include_router(allowance_api_router)
# allowance_ext.include_router(allowance_lnurl_router)  # Disabled

allowance_static_files = [
    {
        "path": "/allowance/static",
        "name": "allowance_static",
    }
]

scheduled_tasks: list[asyncio.Task] = []


def allowance_stop():
    for task in scheduled_tasks:
        try:
            task.cancel()
        except Exception as ex:
            logger.warning(ex)


def allowance_start():
    from lnbits.tasks import create_permanent_unique_task

    # Start the allowance payment scheduler
    scheduler_task = create_permanent_unique_task(
        "ext_allowance_scheduler", check_and_process_allowances
    )
    scheduled_tasks.append(scheduler_task)
    logger.info("🚀 Started allowance payment scheduler")


__all__ = [
    "allowance_ext",
    "allowance_start",
    "allowance_static_files",
    "allowance_stop",
    "db",
]
