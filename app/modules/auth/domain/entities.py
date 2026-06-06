import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .value_objects import EmailAddress, HashedPassword


@dataclass()
class User:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: EmailAddress
    hashed_password: HashedPassword
    is_active: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def disable_user(self):
        self.is_active = False


