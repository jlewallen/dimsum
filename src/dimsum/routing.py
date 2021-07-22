import json
import subprocess
from typing import List, Optional

from loggers import get_logger

log = get_logger("dimsum")


class Target:
    def __init__(self, name: Optional[str] = None):
        super().__init__()
        self.name: str = name if name else "unknown"

    async def handle(self, query: str) -> str:
        raise NotImplementedError


class Router:
    def __init__(self, targets: Optional[List[Target]] = None):
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
                log.exception("error", exc_info=True)

        if len(replies) == 0:
            raise NoRoutesException()

        return replies[0]


class Broker:
    def __init__(self, targets: Optional[List[Target]] = None):
        super().__init__()
        self.router = Router(targets=targets)

    def get_targets(self):
        return self.router.targets


class NoRoutesException(Exception):
    pass


class ProcessTarget(Target):
    def __init__(self, command: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
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
