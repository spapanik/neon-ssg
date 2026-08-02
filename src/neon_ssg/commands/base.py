class BaseCommand:
    __slots__ = ("verbosity",)

    def __init__(self, verbosity: int) -> None:
        self.verbosity = verbosity

    def run(self) -> None:
        raise NotImplementedError
