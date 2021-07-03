from typing import Any, List, Union, TextIO, Dict

import asyncio
import asyncssh
import dataclasses
import time
import crypt
import sys
import logging

import rich
import rich.console
import rich.control
import rich.segment
import rich.live
import rich.table

log = logging.getLogger("dimsum.sshd")


class CommandHandler:
    async def handle(self, line: str):
        raise NotImplementedError


class WrapStandardOut:
    def __init__(self, writer):
        super().__init__()
        self.writer = writer

    def write(self, data):
        return self.writer.write(data)

    def flush(self):
        pass


class WriteEmptyEnd:
    def __init__(self, writer):
        super().__init__()
        self.writer = writer

    def write(self, data):
        return self.writer.write(data, end="")


class ShellSession:
    def __init__(self, connected: Dict[str, "ShellSession"], process, handler_factory):
        super().__init__()
        self.connected = connected
        self.process = process
        self.username = process.get_extra_info("username")
        self.handler = handler_factory(
            username=self.username, channel=WriteEmptyEnd(self)
        )
        assert self.handler

    async def iteration(self):
        command = await self.read_command()

        if command is None:
            return False

        if command == "":
            return True

        try:
            await self.handler.handle(command)
        except:
            log.exception("error", exc_info=True)

        return True

    async def repl(self):
        try:
            while True:
                try:
                    safe = await self.iteration()
                    if not safe:
                        break
                except asyncssh.TerminalSizeChanged as exc:
                    log.info("%s: terminal size changed %s" % (self.username, str(exc)))
                    self.recreate_console()
                    self.write("\n", end="")
        finally:
            await self.handler.finished()

    def recreate_console(self):
        term_type = self.process.get_terminal_type()
        width, height, width_pixels, height_pixels = self.process.get_terminal_size()
        log.info("%s: recreating (%d x %d)" % (self.username, width, height))
        self.console = rich.console.Console(
            file=WrapStandardOut(self.process.stdout),  # type:ignore
            force_terminal=True,
            width=width,
            height=height,
        )

    async def run(self):
        self.username = self.process.get_extra_info("username")

        self.recreate_console()

        log.info("%s: connected" % (self.username))

        self.connected[self.username] = self

        try:
            self.print("\n", end="")

            self.print("Welcome to the party, %s!" % (self.username,))
            self.print("%d other users are connected." % len(self.connected))
            self.print("\n", end="")

            try:
                await self.repl()
            except asyncssh.BreakReceived:
                log.info("%s: brk" % (self.username,))

            log.info("%s: disconnected" % (self.username,))
        finally:
            del self.connected[self.username]
            self.process.exit(0)

    def prompt(self) -> str:
        return ">> "

    async def read_command(self) -> Union[str, None]:
        line = self.console.input(prompt=self.prompt(), stream=self.process.stdin)
        if isinstance(line, str):
            if len(line) == 0:
                return None
            return line.strip()

    def write_everyone_else(self, msg: str):
        for username, other in self.connected.items():
            if other != self:
                other.control(
                    rich.control.Control(
                        (rich.segment.ControlType.CURSOR_MOVE_TO_COLUMN, 0),
                        (rich.segment.ControlType.ERASE_IN_LINE, 2),
                    )
                )
                other.write(msg + "\n")
                other.write(self.prompt(), end="")

    def control(self, control: rich.control.Control, **kwargs):
        self.console.control(control)

    def print(self, msg: str, **kwargs):
        self.console.print(msg, **kwargs)

    def write(self, msg: str, **kwargs):
        self.console.out(msg, **kwargs)


class Server(asyncssh.SSHServer):
    def __init__(self):
        super().__init__()

    def connection_made(self, conn):
        log.info("connection from %s" % conn.get_extra_info("peername")[0])

    def connection_lost(self, exc):
        if exc:
            log.exception("error", exc_info=exc)
        else:
            log.info("connection closed")

    def begin_auth(self, username: str) -> bool:
        return False

    def password_auth_supported(self):
        return True

    def validate_password(self, username: str, password: str) -> bool:
        return True


async def start_server(port: int, handler_factory):
    def create_server():
        return Server()

    connected: Dict[str, ShellSession] = {}

    async def handle_process(process):
        await ShellSession(connected, process, handler_factory).run()

    await asyncssh.create_server(
        create_server,
        "",
        port,
        server_host_keys=["ssh_host_key"],
        process_factory=handle_process,
    )
