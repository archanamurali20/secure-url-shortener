import pytest
from pydantic import ValidationError
from schemas import UrlAPI

@pytest.mark.parametrize(
    "blocked_url",
    [
        "http://127.0.0.1/x",
        "http://localhost:5432",
        "http://169.254.169.254/",
        "http://10.0.0.1/",
        "http://[::1]/",
    ],
)
def test_url_api_rejects_non_public_hosts(blocked_url):
    with pytest.raises(ValidationError):
        UrlAPI(long_url=blocked_url)


def test_url_api_accepts_public_hostname():
    url = "https://google.com/"

    result = UrlAPI(long_url=url)

    assert str(result.long_url) == url
