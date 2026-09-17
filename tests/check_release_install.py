"""Exercise native installation in a disposable, offline LNbits container."""

import asyncio
import importlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from lnbits.core.crud import get_db_version
from lnbits.core.helpers import migrate_databases
from lnbits.core.models.extensions import InstallableExtension, Manifest
from lnbits.core.services.extensions import install_extension
from lnbits.settings import settings


def require(condition, message):
    if not condition:
        raise AssertionError(message)


async def install(archive):
    ext = InstallableExtension(id="allowance", name="Allowance", version="test")
    shutil.copyfile(archive, ext.zip_path)
    await install_extension(ext, skip_download=True)
    return ext


async def main():
    require(
        settings.lnbits_data_folder == "/tmp/allowance-install-test",
        "Run only in the disposable installation test container",
    )
    require(
        settings.lnbits_database_url
        in (
            None,
            "",
            "postgres://allowance_install@allowance-install-postgres:5432/allowance_fresh",
            "postgres://allowance_install@allowance-install-postgres:5432/allowance_upgrade",
        ),
        "Only disposable installation test databases are allowed",
    )
    await migrate_databases()
    mode, candidate, previous = sys.argv[1:]
    if mode == "upgrade":
        await install(previous)
        from lnbits.extensions.allowance import crud
        from lnbits.extensions.allowance.models import CreateAllowanceData

        date = datetime(2030, 1, 31, 9, tzinfo=timezone.utc)
        record = await crud.create_allowance(
            CreateAllowanceData(
                name="Upgrade fixture",
                wallet="synthetic-wallet",
                amount=25,
                lightning_address="recipient@example.invalid",
                start_datetime=date,
                next_payment_date=date,
                frequency_type="monthly",
                memo="",
                active=False,
            )
        )
        await crud.db.execute(
            f"UPDATE {crud.db.references_schema}maintable "
            "SET pending_payment_hash = :hash WHERE id = :id",
            {"hash": "synthetic-pending-hash", "id": record.id},
        )
        await crud.db.engine.dispose()
        for name in list(sys.modules):
            if name == "lnbits.extensions.allowance" or name.startswith(
                "lnbits.extensions.allowance."
            ):
                del sys.modules[name]
        importlib.invalidate_caches()
    elif mode != "fresh":
        raise ValueError("Expected fresh or upgrade mode")

    ext = await install(candidate)
    from lnbits.extensions.allowance import crud

    version = await get_db_version("allowance")
    require(version.version == 6, "Expected migrations through m006")
    config = json.loads((ext.ext_dir / "config.json").read_text())
    require(config["min_lnbits_version"] == "1.6.0", "Unexpected compatibility floor")
    manifest = Manifest.parse_raw((ext.ext_dir / "manifest.json").read_text())
    require(manifest.repos[0].id == "allowance", "Invalid repository manifest")
    require(
        (ext.ext_dir / "templates/allowance/index.html").is_file(),
        "Missing UI template",
    )
    require(
        (await crud.get_scheduler_health())["state"] == "starting",
        "Missing scheduler health",
    )
    if mode == "upgrade":
        updated = await crud.get_allowance(record.id)
        require(
            updated.name == record.name and updated.amount == record.amount,
            "Allowance data changed",
        )
        require(
            updated.start_datetime == date and updated.next_payment_date == date,
            "Schedule changed during upgrade",
        )
        require(
            not updated.active and updated.revision == 0, "Activation/revision changed"
        )
        require(
            updated.pending_payment_hash == "synthetic-pending-hash",
            "Pending claim lost",
        )
    await install(candidate)
    require(
        (await get_db_version("allowance")).version == 6,
        "Reinstallation changed migration version",
    )
    print(f"PASS: native {mode} installation and reinstallation")


if __name__ == "__main__":
    asyncio.run(main())
