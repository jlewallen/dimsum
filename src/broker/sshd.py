from typing import Any, List, Union

import asyncio
import asyncssh
import time
import crypt
import sys
import logging

import rich
import rich.console
import rich.live
import rich.table


log = logging.getLogger("dimsum.sshd")


class WrapStandardOut:
    def __init__(self, writer):
        super().__init__()
        self.writer = writer

    def write(self, data):
        return self.writer.write(data)

    def flush(self):
        pass


class ShellSession:
    others: List["ShellSession"] = []

    def __init__(self, process):
        super().__init__()
        self.process = process
        self.name = self.process.get_extra_info("username")

    async def iteration(self):
        command = await self.read_command()

        if command is None:
            return False

        if command == "":
            return True

        self.write("\n", end="")
        self.write("{0}".format(command))
        self.write("\n", end="")

        return True

    async def repl(self):
        while True:
            try:
                safe = await self.iteration()
                if not safe:
                    break
            except asyncssh.TerminalSizeChanged as exc:
                log.info("%s: terminal size changed %s" % (self.name, str(exc)))
                self.recreate_console()
                self.write("\n", end="")

    def recreate_console(self):
        term_type = self.process.get_terminal_type()
        width, height, width_pixels, height_pixels = self.process.get_terminal_size()
        log.info("%s: recreating (%d x %d)" % (self.name, width, height))
        self.console = rich.console.Console(
            file=WrapStandardOut(self.process.stdout),
            force_terminal=True,
            width=width,
            height=height,
        )

    async def run(self):
        self.name = self.process.get_extra_info("username")

        self.recreate_console()

        log.info("%s: connected" % (self.name))

        self.others.append(self)

        try:
            self.print("\n", end="")

            if False:
                if self.process.env:
                    for key, value in self.process.env.items():
                        self.process.stdout.write("%s=%s\n" % (key, value))

            self.print("Welcome to the party, %s!" % (self.name,))
            self.print("%d other users are connected." % len(self.others))
            self.print("\n", end="")

            self.write_everyone_else("*** %s has joined" % self.name)

            try:
                await self.repl()
            except asyncssh.BreakReceived:
                log.info("%s: brk" % (self.name,))

            log.info("%s: disconnected" % (self.name,))

            self.write_everyone_else("*** %s has left" % self.name)
        finally:
            self.others.remove(self)
            self.process.exit(0)

    def prompt(self) -> str:
        return ">> "

    async def read_command(self) -> Union[str, None]:
        line = await self.console.input(prompt=self.prompt(), stream=self.process.stdin)
        if isinstance(line, str):
            if len(line) == 0:
                return None
            return line.strip()
        return None

    def write_everyone_else(self, msg: str):
        for other in self.others:
            if other != self:
                if False:
                    other.control("\033[1G\033[2K")
                other.write(msg + "\n")
                other.write(self.prompt(), end="")

    def control(self, msg: str, **kwargs):
        self.console.control(msg, **kwargs)

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
            log.error("connection error: " + str(exc))
        else:
            log.info("connection closed")

    def password_auth_supported(self):
        return True

    def begin_auth(self, username: str) -> bool:
        log.info("auth:begin %s", username)
        # Return False to allow passwordless, otherwise True to check
        # password in validate_password
        return False

    def validate_password(self, username: str, password: str) -> bool:
        # Only called when the above says there's a password to check.
        log.info("auth:validate %s", username)
        return True


async def start_server():
    def create_server():
        return Server()

    async def handle_process(process):
        await ShellSession(process).run()

    await asyncssh.create_server(
        create_server,
        "",
        8022,
        server_host_keys=["ssh_host_key"],
        process_factory=handle_process,
    )
