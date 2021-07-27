import asyncio
import cProfile, pstats
import test
import library
import domains


async def create_simple():
    await test.make_simple_domain()


async def create_library():
    domain = domains.Domain(empty=True)

    with domain.session() as session:
        world = await session.prepare()

        factory = library.example_world_factory(world)
        await factory(session)

        await session.save()


async def run_multiple_times(fn, n=100):
    for i in range(0, n):
        await fn()


def run_perf_case(fn, prof_path: str, print=False):
    profiler = cProfile.Profile()
    profiler.enable()
    asyncio.run(run_multiple_times(fn))
    profiler.disable()
    stats = pstats.Stats(profiler).sort_stats("cumtime")
    stats.dump_stats(prof_path)
    if print:
        stats.print_stats()


if __name__ == "__main__":
    run_perf_case(create_simple, "gen/create_simple.prof")
    run_perf_case(create_library, "gen/create_library.prof")
