import os
import sys

import requests
import sentry_sdk
from kinto_http import Client, KintoException
from kinto_http.utils import collection_diff
from sentry_sdk.integrations.gcp import GcpIntegration


# Required environment variables
AUTHORIZATION = os.getenv("AUTHORIZATION", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "local").lower()
SERVER = os.getenv(
    "SERVER",
    {
        "local": "http://localhost:8888/v1",
        "dev": "https://remote-settings-dev.allizom.org/v1",
        "stage": "https://remote-settings.allizom.org/v1",
        "prod": "https://remote-settings.mozilla.org/v1",
    }[ENVIRONMENT],
)
IS_DRY_RUN = os.getenv("DRY_RUN", "0") in "1yY"
SENTRY_DSN = os.getenv("SENTRY_DSN")
SENTRY_ENV = os.getenv("SENTRY_ENV", ENVIRONMENT)
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))

if ENVIRONMENT not in {"local", "dev", "stage", "prod"}:
    raise ValueError(f"'ENVIRONMENT={ENVIRONMENT}' is not a valid value")

# Constants for collection
BUCKET = "main-workspace"
ALLOWLIST_COLLECTION = "fxrelay-allowlist"
BLOCKLIST_COLLECTION = "fxrelay-denylist"
LIST_INPUT_URL_BASE = (
    "https://raw.githubusercontent.com/mozilla/fx-private-relay/refs/heads/main/privaterelay"
)
ALLOWLIST_INPUT_URL = os.getenv(
    "ALLOWLIST_INPUT_URL",
    f"{LIST_INPUT_URL_BASE}/fxrelay-allowlist-domains.txt",
)
BLOCKLIST_INPUT_URL = os.getenv(
    "BLOCKLIST_INPUT_URL",
    f"{LIST_INPUT_URL_BASE}/fxrelay-blocklist-domains.txt",
)


def fetch_list(input_url):
    print(f"📥 Loading list from {input_url}")
    response = requests.get(input_url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    new_list = response.content.decode()
    domains = set(filter(None, new_list.split("\n")))
    print(f"📋 Parsed {len(domains)} domains.")
    return [{"id": domain.replace(".", "-"), "domain": domain} for domain in sorted(domains)]


def sync_collection(client, source_records):
    print("📥 Fetching current destination records...")
    try:
        dest_records = client.get_records()
    except KintoException as e:
        print(f"❌ Failed to fetch existing records: {e}")
        return 1

    # Compute the diff
    to_create, to_update, to_delete = collection_diff(source_records, dest_records)

    has_changes = to_create or to_update or to_delete
    if not has_changes:
        print("✅ Records are already in sync. Nothing to do.")
        return 0

    print(
        f"🔧 Applying {len(to_create)} creates, {len(to_update)} updates, {len(to_delete)} deletes..."
    )
    try:
        with client.batch() as batch:
            for record in to_create:
                batch.create_record(data=record)
            for _, new in to_update:
                new.pop("last_modified", None)
                batch.update_record(data=new)
            for record in to_delete:
                batch.delete_record(id=record["id"])
        ops_count = len(batch.results())
        print(f"✅ Batch {ops_count} operations applied.")
    except KintoException as e:
        print(f"❌ Failed to apply changes: {e}")
        return 1

    try:
        if ENVIRONMENT == "dev":
            print("🟢 Self-approving changes on dev...")
            client.request_review(message="r?")
            client.approve_changes()
            print("✅ Changes self-approved.")
        else:
            print("📤 Requesting review...")
            client.request_review(message="r?")
            print("✅ Review requested.")
    except KintoException as e:
        print(f"❌ Failed to update collection status: {e}")
        return 1

    return 0


def main():
    if SENTRY_DSN:
        # Initialize Sentry for error reporting.
        sentry_sdk.init(SENTRY_DSN, integrations=[GcpIntegration()], environment=SENTRY_ENV)
    else:
        print("⚠️ Sentry is not configured. Set SENTRY_DSN environment variable to enable it.")

    # --- Allowlist ---
    allowlist_client = Client(
        server_url=SERVER,
        auth=AUTHORIZATION,
        bucket=BUCKET,
        collection=ALLOWLIST_COLLECTION,
        dry_mode=IS_DRY_RUN,
    )
    try:
        print("🔐 Checking credentials...", end="")
        server_info = allowlist_client.server_info()
        print("✅")
        if "user" in server_info:
            print(f"👤 Logged in as {server_info['user']['id']}")
        else:
            print("⚠️ Anonymous access")
    except Exception as e:
        print(f"❌ Failed to connect to Remote Settings server: {e}")
        return 1

    print("\n=== Processing ALLOWLIST ===")
    print("📥 Fetching new allowlist records...")
    allowlist_records = fetch_list(ALLOWLIST_INPUT_URL)
    result = sync_collection(allowlist_client, allowlist_records)
    if result != 0:
        return result

    # --- Blocklist ---
    print("\n=== Processing BLOCKLIST ===")
    blocklist_client = allowlist_client.clone(collection=BLOCKLIST_COLLECTION)

    print("📥 Fetching new blocklist records...")
    blocklist_records = fetch_list(BLOCKLIST_INPUT_URL)
    result = sync_collection(blocklist_client, blocklist_records)
    if result != 0:
        return result

    return 0


if __name__ == "__main__":
    sys.exit(main())
