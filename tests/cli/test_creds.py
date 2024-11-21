import pydantic
import pytest

from virtualship.cli._creds import CredentialFileError, Credentials


def test_load_credentials(tmp_file):
    tmp_file.write_text(
        """
        COPERNICUS_USERNAME: test_user
        COPERNICUS_PASSWORD: test_password
        """
    )

    creds = Credentials.from_yaml(tmp_file)
    assert creds.COPERNICUS_USERNAME == "test_user"
    assert creds.COPERNICUS_PASSWORD == "test_password"


# parameterize with the contents of the file
@pytest.mark.parametrize(
    "contents",
    [
        pytest.param(
            """
            INVALID_KEY: some_value
            """,
            id="invalid-key",
        ),
        pytest.param(
            """
            # number not allowed, should be string (or quoted number)
            USERNAME: 123
            """,
            id="number-not-allowed",
        ),
    ],
)
def test_invalid_credentials(tmp_file, contents):
    tmp_file.write_text(contents)

    with pytest.raises(pydantic.ValidationError):
        Credentials.from_yaml(tmp_file)


def test_credentials_invalid_format(tmp_file):
    tmp_file.write_text(
        """
        INVALID_FORMAT_BUT_VALID_YAML
        """
    )

    with pytest.raises(CredentialFileError):
        Credentials.from_yaml(tmp_file)


def test_rt_credentials(tmp_file):
    """Test round-trip for credentials using Credentials.from_yaml() and Credentials.dump()."""
    creds = Credentials(
        COPERNICUS_USERNAME="test_user", COPERNICUS_PASSWORD="test_password"
    )

    creds.to_yaml(tmp_file)
    creds_loaded = Credentials.from_yaml(tmp_file)

    assert creds == creds_loaded
