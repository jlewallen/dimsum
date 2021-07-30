import asyncio
import cProfile, pstats
import test
import library
import domains
import yappi


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


def run_perf_case(fn, prof_path: str, use_yappi: bool = True):
    if use_yappi:
        yappi.set_clock_type("wall")
        with yappi.run():
            asyncio.run(run_multiple_times(fn))
        fns = yappi.get_func_stats(
            filter_callback=lambda x: "site-packages" not in x.module
            and "/usr/lib" not in x.module
            and "importlib" not in x.module,
        )
        for fn in fns:
            print(fn.module)
        fns.print_all(
            columns={
                0: ("name", 96),
                1: ("ncall", 5),
                2: ("tsub", 8),
                3: ("ttot", 8),
                4: ("tavg", 8),
            },
        )
    else:
        profiler = cProfile.Profile()
        profiler.enable()
        asyncio.run(run_multiple_times(fn))
        profiler.disable()
        stats = pstats.Stats(profiler).sort_stats("cumtime")
        stats.dump_stats(prof_path)


if __name__ == "__main__":
    run_perf_case(create_simple, "gen/create_simple.prof", use_yappi=True)
    run_perf_case(create_library, "gen/create_library.prof", use_yappi=True)
