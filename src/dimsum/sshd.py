from typing import Any, List, Union

import asyncio
import asyncssh
import time
import crypt
import sys
import logging
import grammar
import animals
import actions
import props
import evaluator
import messages
import rich
import rich.console
import rich.live
import rich.table


log = logging.getLogger("dimsum.sshd")

passwords = {
    "jlewallen": "",
}


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

    def __init__(self, state, process):
        super().__init__()
        self.l = grammar.create_parser()
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

    def parse_as(self, evaluator, full):
        tree = self.l.parse(full.strip())
        log.info(str(tree))
        return evaluator.transform(tree)

    async def iteration(self):
        command = await self.read_command()

        if command is None:
            return False

        if command == "":
            return True

        world = self.state.world
        player = await self.get_player()
        action = self.parse_as(evaluator.create(world, player), command)
        reply = await world.perform(action, player)
        await self.state.save()

        visitor = messages.ReplyVisitor()
        visual = reply.accept(visitor)
        log.info(
            "%s" % (visual),
        )

        self.write("\n", end="")

        if "title" in visual:
            self.write(visual["title"], end="")
            self.write("\n", end="")

        if "text" in visual:
            self.write(visual["text"], end="")
            self.write("\n", end="")

        if "description" in visual:
            self.write("\n", end="")
            self.write(visual["description"], end="")

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
        print("%s: recreating (%d x %d)" % (self.name, width, height))
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

        if not self.state.world:
            self.print("\ninitializing...\n")
            self.process.exit(0)
            return

        if False:
            table = rich.table.Table()
            table.add_column("Row ID")
            table.add_column("Description")
            table.add_column("Level")

            with rich.live.Live(table, refresh_per_second=4, console=self.console):
                for row in range(12):
                    time.sleep(0.4)
                    table.add_row(f"{row}", f"description {row}", "[red]ERROR")

        player = await self.get_player()

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
