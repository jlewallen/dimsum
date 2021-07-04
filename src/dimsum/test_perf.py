import logging
import cProfile
import asyncio

import re
import test


async def main():
    tw = test.TestWorld()
    await tw.initialize()


if __name__ == "__main__":
    cProfile.run("test.TestWorld()")
    # cProfile.run("asyncio.run(main())")
