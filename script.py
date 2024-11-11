import os
import sys
from collections import defaultdict

import kinto_http
import requests


AUTHORIZATION = os.getenv("AUTHORIZATION", "")
SERVER = os.getenv("SERVER", "http://localhost:8888/v1")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local").lower()
if ENVIRONMENT not in {"local", "dev", "stage", "prod"}:
    raise ValueError(f"'ENVIRONMENT={ENVIRONMENT}' is not a valid value")
IS_DRY_RUN = os.getenv("DRY_RUN", "0") in "1yY"

COLLECTION_NAME = "product-integrity"


def get_source_records():
    """
    Function that turns the source of truth data into Remote Settings records.
    Write your own...
    """
    resp = requests.get("https://product-details.mozilla.org/1.0/firefox_versions.json")
    details = resp.json()
    return [
        {"id": "release", "version": details["LATEST_FIREFOX_VERSION"]},
        {"id": "beta", "version": details["FIREFOX_DEVEDITION"]},
        {"id": "esr", "version": details["FIREFOX_ESR"]},
    ]


def records_equal(a, b):
    """
    Example function that will compare a source with a destination.
    Adjust to your needs...
    """
    ignore_fields = ("last_modified", "schema")
    ac = {k: v for k, v in a.items() if k not in ignore_fields}
    bc = {k: v for k, v in b.items() if k not in ignore_fields}
    return ac == bc


def main():
    client = kinto_http.Client(
        server_url=SERVER, auth=AUTHORIZATION, bucket="main-workspace", collection=COLLECTION_NAME
    )

    if IS_DRY_RUN:
        # Replace write operations with no-op.
        orig_request = client.session.request

        def dry_run(method, *args, **kwargs):
            if method.lower() in ("get", "head"):
                return orig_request(method, *args, **kwargs)
            return defaultdict(), {}

        client.session.request = dry_run

    # Check credentials.
    print("Fetch server info...", end="")
    server_info = client.server_info()
    print("✅")
    if "user" not in server_info:
        print("⚠️ Anonymous")
    else:
        print(f"Logged in as {server_info['user']['id']}")

    # Get source records.
    print("Fetch records from source of truth...", end="")
    source_records = get_source_records()
    print("✅")

    # Get current destination records.
    print("Fetch current destination records...", end="")
    records_by_id = {r["id"]: r for r in client.get_records()}
    print("✅")

    # Create or update the destination records.
    to_create = []
    to_update = []
    for r in source_records:
        record = records_by_id.pop(r["id"], None)
        if record is None:
            to_create.append(r)
        elif not records_equal(r, record):
            to_update.append(r)
    # Delete the records missing from source.
    to_delete = records_by_id.values()

    has_pending_changes = (len(to_create) + len(to_update) + len(to_delete)) > 0
    if not has_pending_changes:
        print("Records are in sync. Nothing to do ✅.")
        return os.EX_OK

    # Use a batch request for all operations.
    # Note, if you need to add attachments on records, use individual calls.
    # See https://github.com/Kinto/kinto-http.py/?tab=readme-ov-file#attachments
    print("Apply changes...", end="")
    with client.batch() as batch:
        for r in to_create:
            batch.create_record(data=r)
        for r in to_update:
            # Let the server assign a new timestamp.
            r.pop("last_modified", None)
            batch.update_record(data=r)
        for r in to_delete:
            batch.delete_record(id=r["id"])
    ops_count = len(batch.results())
    print(f"{ops_count} operations ✅")

    if ENVIRONMENT == "dev":
        # Self approve changes on DEV.
        client.patch_collection(data={"status": "to-sign"})
    else:
        # Request review.
        print("Request review...", end="")
        client.patch_collection(data={"status": "to-review"})
        print("✅")

    return os.EX_OK


if __name__ == "__main__":
    sys.exit(main())
