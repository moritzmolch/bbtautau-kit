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
