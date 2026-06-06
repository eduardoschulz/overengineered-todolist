from dataclasses import dataclass


@dataclass(frozen=True)
class EmailAddress:
    address: str

    def __post_init__(self):
        if "@" not in self.address:
            raise ValueError(f"Invalid email: {self.address}")


@dataclass(frozen=True)
class HashedPassword:
    hash_passwd: str
