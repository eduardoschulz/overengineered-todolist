from dataclasses import dataclass


@dataclass(frozen=True)
class ListName:
    value: str

    def __post_init__(self):
        if not self.value.strip():
            raise ValueError("List name cannot be blank")
        if len(self.value) > 100:
            raise ValueError("List name cannot exceed 100 characters")
