class Action:
    def __init__(self, **kwargs):
        super().__init__()


class Reply:
    def accept(self, visitor):
        raise NotImplementedError


class SimpleReply(Reply):
    def __init__(self, message: str, **kwargs):
        super().__init__()
        self.message = message
        self.item = kwargs["item"] if "item" in kwargs else None


class Success(SimpleReply):
    def accept(self, visitor):
        return visitor.success(self)

    def __str__(self):
        return "Success<%s>" % (self.message,)


class Failure(SimpleReply):
    def accept(self, visitor):
        return visitor.failure(self)

    def __str__(self):
        return "Failure<%s>" % (self.message,)
