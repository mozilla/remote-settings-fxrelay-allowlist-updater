from unittest import mock

import pytest

from script import main


@pytest.fixture
def mocked_client():
    # Mock the kinto_http.Client where it is imported.
    with mock.patch("script.Client", spec=True) as mocked_class:
        yield mocked_class()


@pytest.fixture
def mocked_get():
    with mock.patch("requests.get") as mock_get:
        yield mock_get


def test_cannot_call_unknown_method(mocked_client):
    with pytest.raises(AttributeError):
        mocked_client.unknown_method()


def test_sync_allowlist_success(mocked_client, mocked_get, capsys):
    mocked_client.server_info.return_value = {}
    mocked_client.get_records.return_value = [
        {"id": "old-com", "domain": "old.com"},
    ]
    mocked_get.return_value.ok = True
    mocked_get.return_value.content = b"new.com\n"
    # Get a handle on the context manager from ``client.batch()``:
    batch_client = mocked_client.batch().__enter__()
    batch_client.results.return_value = [{"id": "old-com"}, {"id": "new.com"}]

    main()

    assert "✅ Batch 2 operations applied." in capsys.readouterr().out
    batch_client.delete_record.assert_called_once_with(id="old-com")
    batch_client.create_record.assert_called_once_with(data={"id": "new-com", "domain": "new.com"})
    mocked_client.request_review.assert_called_once_with(message="r?")


def test_no_changes_found(mocked_client, mocked_get):
    mocked_client.server_info.return_value = {}
    mocked_client.get_records.return_value = [
        {"id": "nochanges-com", "domain": "nochanges.com"},
    ]
    mocked_get.return_value.ok = True
    mocked_get.return_value.content = b"nochanges.com\n"

    main()

    mocked_client.get_records.assert_called_once()
    mocked_get.assert_called_once()
    mocked_client.batch.assert_not_called()


def test_server_connection_failure(mocked_client, mocked_get, capsys):
    mocked_get.return_value.ok = True
    mocked_get.return_value.content = b"domain.com\n"

    mocked_client.server_info.side_effect = Exception("Connection error")

    main()

    captured = capsys.readouterr()
    assert "❌ Failed to connect to Remote Settings server: Connection error" in captured.out
