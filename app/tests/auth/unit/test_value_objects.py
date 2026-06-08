import pytest
from src.auth.domain.value_objects import EmailAddress

class TestEmailAddressValid:
    def test_simple_valid_email(self):
        email = EmailAddress("user@example.com")
        assert email.value == "user@example.com"
 
    def test_subdomain_email(self):
        email = EmailAddress("user@mail.example.com")
        assert email.value == "user@mail.example.com"
 
    def test_plus_addressing(self):
        email = EmailAddress("user+tag@example.com")
        assert email.value == "user+tag@example.com"
 
    def test_dots_in_local_part(self):
        email = EmailAddress("first.last@example.com")
        assert email.value == "first.last@example.com"
 
    def test_numeric_local_part(self):
        email = EmailAddress("123@example.com")
        assert email.value == "123@example.com"
 
    def test_uppercase_is_normalised_to_lowercase(self):
        email = EmailAddress("User@Example.COM")
        assert email.value == "user@example.com"
 
    def test_hyphenated_domain(self):
        email = EmailAddress("user@my-domain.org")
        assert email.value == "user@my-domain.org"
 
    def test_two_char_tld(self):
        email = EmailAddress("user@example.br")
        assert email.value == "user@example.br"
 
 
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
 
    def test_missing_local_part(self):
        with pytest.raises(ValueError):
            EmailAddress("@example.com")
 
    def test_missing_domain(self):
        with pytest.raises(ValueError):
            EmailAddress("user@")
 
    def test_missing_tld(self):
        with pytest.raises(ValueError):
            EmailAddress("user@example")
 
    def test_double_at_sign(self):
        with pytest.raises(ValueError):
            EmailAddress("user@@example.com")
 
    def test_spaces_inside(self):
        with pytest.raises(ValueError):
            EmailAddress("us er@example.com")
 
    def test_trailing_dot_in_domain(self):
        with pytest.raises(ValueError):
            EmailAddress("user@example.com.")
 
    def test_leading_dot_in_local_part(self):
        with pytest.raises(ValueError):
            EmailAddress(".user@example.com")
 
    def test_consecutive_dots_in_local_part(self):
        with pytest.raises(ValueError):
            EmailAddress("us..er@example.com")

