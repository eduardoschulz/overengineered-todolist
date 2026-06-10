import pytest
from modules.auth.domain.value_objects import EmailAddress


class TestEmailAddressValid:
    def test_simple_valid_email(self):
        email = EmailAddress("user@example.com")
        assert email.address == "user@example.com"

    def test_subdomain_email(self):
        email = EmailAddress("user@mail.example.com")
        assert email.address == "user@mail.example.com"

    def test_plus_addressing(self):
        email = EmailAddress("user+tag@example.com")
        assert email.address == "user+tag@example.com"

    def test_dots_in_local_part(self):
        email = EmailAddress("first.last@example.com")
        assert email.address == "first.last@example.com"

    def test_numeric_local_part(self):
        email = EmailAddress("123@example.com")
        assert email.address == "123@example.com"

    def test_uppercase_is_stored_as_is(self):
        email = EmailAddress("User@Example.COM")
        assert email.address == "User@Example.COM"

    def test_hyphenated_domain(self):
        email = EmailAddress("user@my-domain.org")
        assert email.address == "user@my-domain.org"

    def test_two_char_tld(self):
        email = EmailAddress("user@example.br")
        assert email.address == "user@example.br"


class TestEmailAddressInvalid:
    def test_empty_string(self):
        with pytest.raises(ValueError):
            EmailAddress("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError):
            EmailAddress("   ")

    def test_missing_at_sign(self):
        with pytest.raises(ValueError):
            EmailAddress("userexample.com")
