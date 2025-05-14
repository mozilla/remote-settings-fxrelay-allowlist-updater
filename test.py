from unittest import mock

import pytest

from script import main


@pytest.fixture
def mocked_client():
    with mock.patch('kinto_http.Client') as mock_client:
        yield mock_client


def test_main_anonymous(mocked_client, capsys):
    mocked_client().server_info.return_value = {}

    main()

    mocked_client.return_value.server_info.assert_called_once()
    assert "⚠️ Anonymous" in capsys.readouterr().out


def test_main_anonymous(mocked_client, capsys):
    mocked_client().server_info.return_value = {
        "user": {
            "id": "account:bot"
        }
    }

    main()

    mocked_client.return_value.server_info.assert_called_once()
    assert "Logged in as account:bot" in capsys.readouterr().out
