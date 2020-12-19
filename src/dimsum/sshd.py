from typing import Any

import asyncio
import asyncssh
import crypt
import sys
import logging

log = logging.getLogger("sshd")

passwords = {
    "jlewallen": "",
}


class ShellSession:
    others = []

    @classmethod
    async def handle_process(cls, process):
        await cls(process).run()

    def __init__(self, process):
        super().__init__()
        self.process = process

    async def run(self):
        term_type = self.process.get_terminal_type()
        width, height, pixwidth, pixheight = self.process.get_terminal_size()

        name = self.process.get_extra_info("username")

        log.info("%s: connected: %s (%d x %d)" % (name, term_type, width, height))

        self.write("Welcome to the party, %s!\n" % (name,))
        self.write("%d other users are connected.\n\n" % len(self.others))

        self.write_everyone_else("*** %s has entered chat ***\n" % name)

        self.others.append(self)

        try:
            while True:
                command = await self.repl()
        except asyncssh.BreakReceived:
            log.info("%s: brk" % (name,))

        log.info("%s: disconnected" % (name,))

        self.others.remove(self)
        self.process.exit(0)

    def prompt(self) -> str:
        return " > "

    async def repl(self) -> str:
        self.write(self.prompt())
        line = await self.process.stdin.readline()
        return line.strip()

    def write(self, msg: str):
        self.process.stdout.write(msg)

    def write_everyone_else(self, msg: str):
        for other in self.others:
            if other != self:
                other.write(msg)
                other.write("\n")
                other.write(self.prompt())


class Server(asyncssh.SSHServer):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def connection_made(self, conn):
        log.info("connection from %s" % conn.get_extra_info("peername")[0])

    def connection_lost(self, exc):
        if exc:
            log.error("connection error: " + str(exc))
        else:
            log.info("connection closed")

    def begin_auth(self, username: str) -> bool:
        return passwords.get(username) != ""

    def password_auth_supported(self):
        return True

    def validate_password(self, username: str, password: str) -> bool:
        pw = passwords.get(username, "*")
        return crypt.crypt(password, pw) == pw


async def start_server(state):
    def create_server():
        return Server(state)

    await asyncssh.create_server(
        create_server,
        "",
        8022,
        server_host_keys=["ssh_host_key"],
        process_factory=ShellSession.handle_process,
    )
