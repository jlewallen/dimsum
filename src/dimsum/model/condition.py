import abc


class Condition:
    @abc.abstractmethod
    def applies(self) -> bool:
        return True


class AlwaysTrue(Condition):
    def applies(self) -> bool:
        return True
