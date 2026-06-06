import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .value_objects import EmailAddress, HashedPassword


@dataclass(kw_only=True)
class User:
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    email: EmailAddress
    hashed_password: HashedPassword
    is_active: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def deactivate(self):
        self.is_active = False

    def activate(self):
        """Reverse method for deactivate"""
        self.is_active = True

    def change_email(self, new_email: EmailAddress):
        self.email = new_email

    def change_password(self, new_hashed_password: HashedPassword):
        self.hashed_password = new_hashed_password

    def __repr__(self):
        return f"User(id={self.id!r}, email={self.email!r}, is_active={self.is_active!r})"
