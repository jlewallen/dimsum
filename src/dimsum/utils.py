import asyncio
import concurrent.futures

pool = concurrent.futures.ThreadPoolExecutor()


def run_async_on_other_thread(coroutine):
    return pool.submit(asyncio.run, coroutine).result()
