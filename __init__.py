from fastapi import APIRouter
from lnbits.task_manager import task_manager
from loguru import logger

from .crud import db
from .tasks import check_and_process_allowances
from .views import allowance_generic_router
from .views_api import allowance_api_router

allowance_ext: APIRouter = APIRouter(prefix="/allowance", tags=["Allowance"])
allowance_ext.include_router(allowance_generic_router)
allowance_ext.include_router(allowance_api_router)

allowance_static_files = [
    {
        "path": "/allowance/static",
        "name": "allowance_static",
    }
]

SCHEDULER_TASK_NAME = "ext_allowance_scheduler"


def allowance_stop():
    task = task_manager.get_task(SCHEDULER_TASK_NAME)
    if task:
        task_manager.cancel_task(task)


def allowance_start():
    # Extension reloads replace the named task through LNbits' task manager.
    task_manager.create_permanent_task(
        check_and_process_allowances, name=SCHEDULER_TASK_NAME
    )
    logger.info("Started allowance payment scheduler")


__all__ = [
    "allowance_ext",
    "allowance_start",
    "allowance_static_files",
    "allowance_stop",
    "db",
]
