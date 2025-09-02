from unittest import mock

import pytest

from script import main


@pytest.fixture
def mocked_clients():
    with mock.patch("script.Client", spec=True) as mocked_class:
        allow_client = mock.MagicMock(name="allow_client")
        block_client = mock.MagicMock(name="block_client")
        allow_batch = mock.MagicMock(name="allow_batch")
        block_batch = mock.MagicMock(name="block_batch")
        allow_client.batch.return_value.__enter__.return_value = allow_batch
        allow_client.batch.return_value.__exit__.return_value = None
        block_client.batch.return_value.__enter__.return_value = block_batch
        block_client.batch.return_value.__exit__.return_value = None
        allow_client.clone.return_value = block_client
        mocked_class.side_effect = [allow_client]

        yield (allow_client, block_client, allow_batch, block_batch)


@pytest.fixture
def mocked_get():
    with mock.patch("requests.get") as mock_get:
        yield mock_get


def setup_env(monkeypatch):
    # Ensure environment variables are set for both lists
    monkeypatch.setenv("ALLOWLIST_INPUT_URL", "https://example.com/allowlist.txt")
    monkeypatch.setenv("BLOCKLIST_INPUT_URL", "https://example.com/blocklist.txt")


def test_sync_both_lists_success(mocked_clients, mocked_get, monkeypatch):
    setup_env(monkeypatch)
    allow_client, block_client, allow_batch, block_batch = mocked_clients
    allow_client.server_info.return_value = {}
    allow_client.get_records.return_value = [{"id": "old-allow-com", "domain": "old-allow.com"}]
    block_client.get_records.return_value = [{"id": "old-block-com", "domain": "old-block.com"}]
    mocked_get.side_effect = [
        mock.Mock(ok=True, content=b"new-allow.com\n"),
        mock.Mock(ok=True, content=b"new-block.com\n"),
    ]

    rc = main()

    assert rc == 0
    # Review requested for both
    assert allow_client.server_info.call_count == 1
    assert allow_client.get_records.call_count == 1
    assert allow_batch.create_record.call_args_list[0].kwargs["data"]["domain"] == "new-allow.com"
    assert allow_batch.delete_record.call_count == 1
    assert allow_batch.delete_record.call_args_list[0].kwargs["id"] == "old-allow-com"
    assert block_batch.create_record.call_count == 1
    assert block_batch.create_record.call_args_list[0].kwargs["data"]["domain"] == "new-block.com"
    assert block_batch.delete_record.call_count == 1
    assert block_batch.delete_record.call_args_list[0].kwargs["id"] == "old-block-com"
    assert allow_client.request_review.call_count == 1
    assert block_client.request_review.call_count == 1


def test_no_changes_for_both_lists(mocked_clients, mocked_get, monkeypatch):
    setup_env(monkeypatch)
    allow_client, block_client, allow_batch, block_batch = mocked_clients
    allow_client.server_info.return_value = {}
    allow_client.get_records.return_value = [
        {"id": "nochange-allow-com", "domain": "nochange-allow.com"}
    ]
    block_client.get_records.return_value = [
        {"id": "nochange-block-com", "domain": "nochange-block.com"}
    ]
    mocked_get.side_effect = [
        mock.Mock(ok=True, content=b"nochange-allow.com\n"),
        mock.Mock(ok=True, content=b"nochange-block.com\n"),
    ]
    allow_client.server_info.return_value = {}

    rc = main()

    assert rc == 0
    # Should not call batch for either collection
    assert allow_batch.call_count == 0
    assert block_batch.call_count == 0


def test_allowlist_connection_failure_only(mocked_clients, mocked_get, monkeypatch):
    """
    Allowlist fails on server_info (early exit, no batch ops; blocklist is not exercised).
    """
    setup_env(monkeypatch)
    allow_client, _, _, _ = mocked_clients

    # Provide deterministic list fetches (won't be used due to early exit).
    mocked_get.side_effect = [
        mock.Mock(ok=True, content=b"allow.com\n"),
        mock.Mock(ok=True, content=b"block.com\n"),
    ]

    # Fail as early as possible during allowlist server connectivity check.
    allow_client.server_info.side_effect = Exception("Allowlist connection error")

    rc = main()

    assert allow_client.server_info.call_count == 1
    assert rc == 1
