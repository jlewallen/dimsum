class Hook:
    def __ini__(self, **kwargs):
        self.name = kwargs["name"]


hooks = {}


def get(self, name):
    if not name in hooks:
        hooks[name] = Hook(name=name)
    return hooks[name]


def all(self):
    return hooks
