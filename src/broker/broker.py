#!env/bin/python3

import sys
import logging
import time
import ipaddress
import asyncio

import proxy
import sshd

if __name__ == "__main__":
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)

    with proxy.start(
        ["--enable-web-server"],
        hostname=ipaddress.IPv4Address("0.0.0.0"),
        port=8899,
        plugins=[proxy.plugin.ReverseProxyPlugin],
    ):
        loop = asyncio.get_event_loop()

        try:
            loop.run_until_complete(sshd.start_server())
        except (OSError, asyncssh.Error) as exc:
            sys.exit("Error starting server: " + str(exc))

        loop.run_forever()
