import sys
import os
import json
import asyncclick as click
import jsondiff
import cli.utils as utils
from typing import List, Dict, Any

from loggers import get_logger
from model import CompiledJson

log = get_logger("dimsum.cli")


@click.group()
def commands():
    pass


@commands.command()
@click.option(
    "--path",
    required=True,
    multiple=True,
    help="Database to diff",
    type=click.Path(exists=True),
)
async def diff(path: List[str]):
    """Display the differences between two databases."""
    if len(path) != 2:
        raise Exception("two (and only two) databases are required")

    domains = [await utils.open_domain(p, read_only=True) for p in path]
    all_keys = [set(await d.store.load_all_keys()) for d in domains]
    keeping = set.intersection(*all_keys)
    added = all_keys[-1].difference(*all_keys[0:-1])
    removed = all_keys[0].difference(*all_keys[1:])

    log.debug("added=%s", added)
    log.debug("updated=%s", keeping)
    log.debug("removed=%s", removed)

    rv: Dict[str, Dict[str, Any]] = {}

    async def load_and_compile(key: str) -> List[CompiledJson]:
        log.debug("load-and-compile %s", key)
        loaded = [await d.store.load_by_key(key) for d in domains]
        return [CompiledJson.compile(l[0].serialized) for l in loaded if len(l) == 1]

    for key in added:
        log.info("added %s", key)
        compiled = await load_and_compile(key)
        rv[key] = compiled[0].compiled

    for key in removed:
        log.info("added %s", key)
        copmiled = await load_and_compile(key)
        rv[key] = {"$delete": True}

    for key in keeping:
        compiled = await load_and_compile(key)
        assert len(compiled) == 2

        d = jsondiff.diff(compiled[0].compiled, compiled[1].compiled, marshal=True)
        if d == {}:
            log.debug("%s empty diff", key)
        else:
            log.info("%s %s", key, d)
            rv[key] = d

    sys.stdout.write(json.dumps(rv))

    for domain in domains:
        await domain.close()
