"""Exercise native installation in a disposable, offline LNbits container."""

import asyncio
import json
import shutil
import subprocess
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
            "postgres://allowance_install@allowance-install-postgres:5432/allowance_warm_upgrade",
            "postgres://allowance_install@allowance-install-postgres:5432/allowance_cached_upgrade",
        ),
        "Only disposable installation test databases are allowed",
    )
    mode, candidate, previous = sys.argv[1:]
    fixture = Path(settings.lnbits_data_folder) / "upgrade-fixture.json"
    if mode not in {"upgrade", "warm_upgrade"}:
        await migrate_databases()
    if mode == "prepare":
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
            "SET pending_payment_hash = :hash, "
            f"start_datetime = {crud.db.timestamp_placeholder('start')}, "
            f"next_payment_date = {crud.db.timestamp_placeholder('due')} "
            "WHERE id = :id",
            {
                "hash": "synthetic-pending-hash",
                "id": record.id,
                "start": date.timestamp() + 0.25,
                "due": date.timestamp() + 0.75,
            },
        )
        fixture.write_text(json.dumps({"id": record.id, "date": date.isoformat()}))
        await crud.db.engine.dispose()
        return
    if mode not in {
        "fresh",
        "upgrade",
        "warm_upgrade",
        "cached_upgrade",
        "verify_restart",
    }:
        raise ValueError("Expected fresh or upgrade mode")

    if mode in {"warm_upgrade", "cached_upgrade"}:
        from lnbits.extensions.allowance import crud as legacy_crud

        require(not hasattr(legacy_crud, "transaction"), "Expected v1.0.6 cached CRUD")
        cached = "lnbits.extensions.allowance.migrations" in sys.modules
        require(
            cached == (mode == "cached_upgrade"), "Unexpected migration cache state"
        )
        await install(candidate)
        require(
            (await get_db_version("allowance")).version == (4 if cached else 7),
            "Unexpected migration version before restart",
        )
        require(
            sys.modules["lnbits.extensions.allowance.crud"] is legacy_crud,
            "The test must retain the old CRUD module throughout installation",
        )
        await legacy_crud.db.engine.dispose()
        return

    ext = (
        InstallableExtension(id="allowance", name="Allowance", version="test")
        if mode == "verify_restart"
        else await install(candidate)
    )
    from lnbits.extensions.allowance import crud

    version = await get_db_version("allowance")
    require(version.version == 7, "Expected migrations through m007")
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
    if mode in {"upgrade", "verify_restart"}:
        saved = json.loads(fixture.read_text())
        date = datetime.fromisoformat(saved["date"])
        updated = await crud.get_allowance(saved["id"])
        require(
            updated.name == "Upgrade fixture" and updated.amount == 25,
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
        (await get_db_version("allowance")).version == 7,
        "Reinstallation changed migration version",
    )
    print(f"PASS: native {mode} installation and reinstallation")


if __name__ == "__main__":
    if sys.argv[1] in {"upgrade", "warm_upgrade", "cached_upgrade"}:
        subprocess.run([sys.executable, __file__, "prepare", *sys.argv[2:]], check=True)
    asyncio.run(main())
    if sys.argv[1] in {"warm_upgrade", "cached_upgrade"}:
        subprocess.run(
            [sys.executable, __file__, "verify_restart", *sys.argv[2:]], check=True
        )
