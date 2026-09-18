from dataclasses import dataclass, field


@dataclass
class ProcessGroup:
    name: str
    processes: list[str]
    label: str
    color: str
    scale_factor: float | None = field(default=None)


@dataclass
class ProcessSet:
    name: str
    data: list[ProcessGroup] = field(default_factory=list)
    signals: list[ProcessGroup] = field(default_factory=list)
    backgrounds: list[ProcessGroup] = field(default_factory=list)

    @property
    def process_groups(self) -> list[ProcessGroup]:
        """
        Return a list of all process groups in the process set.

        Returns
        -------
        list[ProcessGroup]
            A list of all process groups in the process set.
        """
        return self.data + self.signals + self.backgrounds
