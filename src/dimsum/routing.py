from typing import Dict, List, Optional

import logging
import json
import dataclasses
import subprocess
import jsonpickle

log = logging.getLogger("dimsum")


class Target:
    async def handle(self, query: str) -> str:
        raise NotImplementedError


class Router:
    def __init__(self, targets: List[Target] = None):
        super().__init__()
        self.targets: List[Target] = targets if targets else []

    async def handle(self, query: str) -> str:
        # TODO Parallel
        replies = []
        for target in self.targets:
            try:
                log.info("%s handling", target)
                replies.append(await target.handle(query))
            except:
                log.exception("error")

        if len(replies) == 0:
            raise NoRoutesException()

        return replies[0]


class NoRoutesException(Exception):
    pass


class ProcessTarget(Target):
    def __init__(self, command: List[str] = None):
        super().__init__()
        assert command
        self.command = command

    async def handle(self, query: str) -> str:
        with subprocess.Popen(
            self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE
        ) as proc:
            assert proc.stdin
            assert proc.stdout

            log.info("process-target: writing %d bytes", len(query))
            proc.stdin.write(query.encode("utf-8"))
            proc.stdin.close()

            raw_reply = proc.stdout.read().decode("utf-8")
            log.info("process-target: read %d bytes", len(raw_reply))
            return raw_reply

    def __str__(self):
        return "Process<%s>" % (self.command,)


class HttpTarget(Target):
    pass


class WebSocketsTarget(Target):
    pass


class AlwaysOkTarget(Target):
    async def handle(self, query: str) -> str:
        return json.dumps({"ok": True})
