class TokenBlocklist:
    _blocked: set[str]

    def __init__(self) -> None:
        self._blocked = set()

    def add(self, token: str) -> None:
        self._blocked.add(token)

    def is_blocked(self, token: str) -> bool:
        return token in self._blocked


token_blocklist = TokenBlocklist()
