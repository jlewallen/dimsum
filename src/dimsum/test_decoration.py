import logging
import inspect
import wrapt
import pytest

log = logging.getLogger("dimsum.tests")


class MethodProxy(wrapt.ObjectProxy):
    def __init__(self, target, name: str, hook, method):
        super().__init__(method)
        self._self_target = target
        self._self_name = name
        self._self_hook = hook
        log.info("method-proxy[%s]: created", self._self_name)

    async def __call__(self, *args, **kwargs):
        log.info(
            "method-proxy[%s]: %s call(%s %s)",
            self._self_name,
            self._self_hook,
            args,
            kwargs,
        )

        def forward(*wargs, **kwargs):
            return self.__wrapped__(*wargs, **kwargs)

        rv = await self._self_hook.fn(self._self_target, forward, *args, **kwargs)

        log.info("method-proxy[%s]: %s", self._self_name, rv)

        return rv


class HookTarget:
    def __init__(self, klass, function):
        self.klass = klass
        self.function = function


class Hook:
    def __init__(self, fn, target: HookTarget, order: int):
        self.fn = fn
        self.target = target
        self.order = order


class Hooks:
    def __init__(self):
        self.hooks = []

    def wrap(self, target_class, target_fn, order: int = 0, before=None, after=None):
        assert not before
        assert not after

        def wrapper(hook_itself):
            if inspect.isclass(hook_itself):
                raise NotImplementedError

            hook = Hook(hook_itself, HookTarget(target_class, target_fn), order)
            name = target_fn.__name__
            log.info(
                "hooks:fn %s (%s) %s name='%s'",
                hook_itself,
                target_class,
                target_fn,
                name,
            )

            self.hooks.append(hook)

            return hook_itself

        return wrapper

    def install(self, obj):
        for hook in self.hooks:
            target = hook.target
            if target.klass != obj.__class__:
                continue

            name = target.function.__name__
            log.info("hook %s %s (%s)", target.klass, target.function, name)

            method = getattr(obj, name)
            proxy = MethodProxy(obj, name, hook, method)
            setattr(obj, name, proxy)

        return obj


hooks = Hooks()


class Hello:
    async def talk(self):
        log.info("talking!")
        return "done"

    async def yell(self, what: str):
        log.info("yelling: %s", what)
        return what


class TalkingHook:
    @staticmethod
    @hooks.wrap(Hello, Hello.talk)
    async def talk_hook(target, forward):
        log.info("TalkingHook before")
        value = await forward()
        log.info("TalkingHook after '%s'", value)
        return "hook-" + value

    @staticmethod
    @hooks.wrap(Hello, Hello.yell)
    async def yell_hook(target, forward, what: str):
        log.info("TalkingHook before")
        value = await forward(what + " HOOK!")
        log.info("TalkingHook after '%s'", value)
        return "hook-" + value


class AnotherTalkingHook:
    @staticmethod
    @hooks.wrap(Hello, Hello.talk)
    async def talk_hook(target, forward):
        log.info("AnotherTalkingHook before")
        value = await forward()
        log.info("AnotherTalkingHook after '%s'", value)
        return "another-" + value

    @staticmethod
    @hooks.wrap(Hello, Hello.yell)
    async def yell_hook(target, forward, what: str):
        log.info("AnotherTalkingHook before")
        value = await forward(what + " ANOTHER!")
        log.info("AnotherTalkingHook after '%s'", value)
        return "another-" + value


@pytest.mark.asyncio
async def test_simple_hook_no_args():
    hello = hooks.install(Hello())
    actual = await hello.talk()
    assert actual == "another-hook-done"


@pytest.mark.asyncio
async def test_simple_hook_one_arg():
    hello = hooks.install(Hello())
    actual = await hello.yell("HELLO!")
    assert actual == "another-hook-HELLO! ANOTHER! HOOK!"
