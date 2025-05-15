from unittest import mock

import pytest

from script import main


@pytest.fixture
def mocked_client():
    # Mock the kinto_http.Client where it is imported.
    with mock.patch("script.kinto_http.Client", spec=True) as mocked_class:
        yield mocked_class()


@pytest.fixture
def mocked_get():
    # Mock requests where it is imported.
    with mock.patch("script.requests.get") as mock_get:
        yield mock_get


def test_cannot_call_unknown_method(mocked_client):
    # Thanks to the spec=True argument, the mock will raise an
    # AttributeError if we try to call a method that doesn't exist
    with pytest.raises(AttributeError):
        mocked_client.unknown_method()


def test_main_anonymous(mocked_client, capsys):
    mocked_client.server_info.return_value = {}

    main()

    mocked_client.server_info.assert_called_once()
    assert "⚠️ Anonymous" in capsys.readouterr().out


def test_main_logged_in(mocked_client, capsys):
    mocked_client.server_info.return_value = {"user": {"id": "account:bot"}}

    main()

    mocked_client.server_info.assert_called_once()
    assert "Logged in as account:bot" in capsys.readouterr().out


def test_up_to_date(mocked_client, mocked_get, capsys):
    mocked_client.get_records.return_value = [
        {"id": "release", "version": "100.0"},
        {"id": "beta", "version": "100.0b1"},
        {"id": "esr", "version": "91.0"},
    ]
    mocked_get.return_value.json.return_value = {
        "LATEST_FIREFOX_VERSION": "100.0",
        "FIREFOX_DEVEDITION": "100.0b1",
        "FIREFOX_ESR": "91.0",
    }

    main()

    mocked_client.get_records.assert_called_once()
    mocked_get.assert_called_once()
    assert "Records are in sync" in capsys.readouterr().out


def test_outdated(mocked_client, mocked_get, capsys):
    mocked_client.get_records.return_value = [
        {"id": "release", "version": "1.0"},
        {"id": "beta", "version": "100.0b1"},
    ]
    mocked_get.return_value.json.return_value = {
        "LATEST_FIREFOX_VERSION": "100.0",
        "FIREFOX_DEVEDITION": "100.0b1",
        "FIREFOX_ESR": "91.0",
    }
    mocked_client.batch().__enter__().results.return_value = [
        {"id": "release", "version": "100.0"}
    ]

    main()

    mocked_client.get_records.assert_called_once()
    mocked_get.assert_called_once()
    assert "1 operations ✅" in capsys.readouterr().out
