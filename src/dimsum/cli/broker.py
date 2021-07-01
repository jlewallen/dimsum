from typing import Optional, TextIO, List, Dict, Any, TYPE_CHECKING

import logging
import time
import json
import asyncclick as click
import os

import brokers.brokers as brokers

import uvicorn

log = logging.getLogger("dimsum.cli")


def configure_logging():
    with open("logging.json", "r") as file:
        config = json.loads(file.read())  # TODO Parsing logging config JSON
        logging.config.dictConfig(config)


def child(port=45600, **kwargs):
    configure_logging()

    log.info("child: kwargs=%s", kwargs)

    uvicorn.run(
        "dimsum:app",
        host="127.0.0.1",
        port=port,
        log_level="info",
        factory=True,
    )


@click.group()
def commands():
    pass


@commands.command()
async def broker():
    """
    Broker testing ground.
    """

    log.info("broker")

    with brokers.Pool() as pp:
        if True:
            pp.provision(
                config=brokers.ProcessConfig(
                    key="proc-1", target=child, kwargs=dict(port=45600), watching=["./"]
                )
            )
            pp.provision(
                config=brokers.ProcessConfig(
                    key="proc-2", target=child, kwargs=dict(port=45601), watching=["./"]
                )
            )

        if False:
            time.sleep(1)
            pp.remove("proc-1")

        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt as ki:
                log.exception("error")
                break
