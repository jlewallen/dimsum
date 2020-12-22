from typing import Any, List

import asyncio
import asyncssh
import crypt
import sys
import logging
import grammar
import animals
import actions
import props
import evaluator
import messages

log = logging.getLogger("dimsum.sshd")

passwords = {
    "jlewallen": "",
}


class ShellSession:
    others: List["ShellSession"] = []

    def __init__(self, state, process):
        super().__init__()
        self.state = state
        self.process = process
        self.name = self.process.get_extra_info("username")

    async def get_player(self):
        key = self.name
        world = self.state.world
        if world.contains(key):
            player = world.find_by_key(key)
            return player

        player = animals.Player(
            key=key,
            creator=world,
            details=props.Details(self.name, desc="A ssh user"),
        )
        await world.perform(actions.Join(), player)
        await self.state.save()
        return player

    async def repl(self):
        l = grammar.create_parser()

        def parse_as(evaluator, full):
            tree = l.parse(full.strip())
            log.info(str(tree))
            return evaluator.transform(tree)

        while True:
            command = await self.read_command()

            if not command:
                break

            world = self.state.world
            player = await self.get_player()
            action = parse_as(evaluator.create(world, player), command)
            reply = await world.perform(action, player)
            await self.state.save()

            visitor = messages.ReplyVisitor()
            visual = reply.accept(visitor)
            log.info(
                "%s" % (visual),
            )

            self.write("\n")

            if "title" in visual:
                self.write(visual["title"])
                self.write("\n")

            if "text" in visual:
                self.write(visual["text"])
                self.write("\n")

            if "description" in visual:
                self.write("\n")
                self.write(visual["description"])

            self.write("\n")

    async def run(self):
        term_type = self.process.get_terminal_type()
        width, height, pixwidth, pixheight = self.process.get_terminal_size()

        name = self.process.get_extra_info("username")

        log.info("%s: connected: %s (%d x %d)" % (name, term_type, width, height))

        if not self.state.world:
            self.write("\ninitializing...\n\n")
            self.process.exit(0)
            return

        player = await self.get_player()

        self.write("Welcome to the party, %s!\n" % (name,))
        self.write("%d other users are connected.\n\n" % len(self.others))

        self.write_everyone_else("*** %s has joined\n" % name)

        self.others.append(self)

        try:
            await self.repl()
        except asyncssh.BreakReceived:
            log.info("%s: brk" % (name,))

        log.info("%s: disconnected" % (name,))

        self.write_everyone_else("*** %s has left\n" % name)

        self.others.remove(self)
        self.process.exit(0)

    def prompt(self) -> str:
        return " > "

    async def read_command(self) -> str:
        self.write(self.prompt())
        line = await self.process.stdin.readline()
        return line.strip()

    def write(self, msg: str):
        self.process.stdout.write(msg)

    def write_everyone_else(self, msg: str):
        for other in self.others:
            if other != self:
                other.write("\r")
                other.write(msg)
                other.write("\33[2K\n")
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

    async def handle_process(process):
        await ShellSession(state, process).run()

    await asyncssh.create_server(
        create_server,
        "",
        8022,
        server_host_keys=["ssh_host_key"],
        process_factory=handle_process,
    )
