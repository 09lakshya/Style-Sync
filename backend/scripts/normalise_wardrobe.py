r"""Rewrite stored wardrobe items into the canonical spelling.

Items saved before app/modules/wardrobe/normalise.py existed carry "Maroon"
next to "maroon", "Solid" next to "solid", occasions such as "Office" that the
outfit builder does not know, and types such as "trouser" that never land in
an outfit. New writes are normalised already; this brings old rows in line.

Dry run by default - it prints what would change. Pass --apply to write.

    backend\.venv\Scripts\python.exe backend\scripts\normalise_wardrobe.py
    backend\.venv\Scripts\python.exe backend\scripts\normalise_wardrobe.py --apply
"""

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.core.database import close_db, connect_db, get_session_maker  # noqa: E402
from app.core.models import WardrobeItem  # noqa: E402
from app.modules.wardrobe.normalise import normalise_item  # noqa: E402
from app.modules.wardrobe.repository import wardrobe_repository  # noqa: E402


async def main(apply: bool) -> None:
    await connect_db()
    try:
        async with get_session_maker()() as session:
            rows = (await session.execute(select(WardrobeItem.id, WardrobeItem.user_id))).all()

        changed = 0
        for item_id, user_id in rows:
            item = await wardrobe_repository.get_item_by_id(str(item_id), str(user_id))
            if not item:
                continue
            changes = normalise_item(item)
            if not changes:
                continue
            changed += 1
            summary = ", ".join(f"{field}: {item.get(field)!r} -> {value!r}" for field, value in changes.items())
            print(f"{item.get('name')!s:45.45} {summary}")
            if apply:
                await wardrobe_repository.update_item(str(item_id), str(user_id), changes)

        verb = "Updated" if apply else "Would update"
        print(f"\n{verb} {changed} of {len(rows)} items." + ("" if apply else " Re-run with --apply to write."))
    finally:
        await close_db()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="write the changes (default is a dry run)")
    asyncio.run(main(parser.parse_args().apply))
