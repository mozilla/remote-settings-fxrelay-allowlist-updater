# Remote Settings Relay Allowlist Ingestion Job

Turn the list of [allowed domains](https://raw.githubusercontent.com/mozilla/fx-private-relay/refs/heads/main/privaterelay/fxrelay-allowlist-domains.txt) into records on Remote Settings.

## Run

With local Remote Settings server:

```
$ docker run --rm --detach \
    -p 8888:8888 \
    --env KINTO_INI=config/testing.ini \
    mozilla/remote-settings
```

Create the source collection:

```
$ curl -X PUT http://localhost:8888/v1/buckets/main-workspace/collections/fxrelay-allowlist
```

And run the script from sources:

```
$ poetry install
$ poetry shell
$ AUTHORIZATION=testing:foobar SERVER="http://localhost:8888/v1" python script.py

Fetch server info...✅
⚠️ Anonymous
Fetch records from source of truth...✅
Fetch current destination records...✅
Batch #0: PUT /buckets/main-workspace/collections/product-integrity/records/release - 201
Batch #1: PUT /buckets/main-workspace/collections/product-integrity/records/beta - 201
Batch #2: PUT /buckets/main-workspace/collections/product-integrity/records/esr - 201
Apply changes...3 operations ✅
Request review...✅
```

Or from the Docker container:

```
$ docker build -t ingestion:local .
$ docker run -e SERVER="http://localhost:8888/v1" ingestion:local
...
...
✅ Records are already in sync. Nothing to do.
```

### On Remote Settings official servers

([List of environment servers](https://remote-settings.readthedocs.io/en/latest/getting-started.html#environments))

**As yourself**:

Login on the Admin UI and copy the Bearer header value (UI top right bar)

And use it to run the script

```
$ read -s BEARER
$ AUTHORIZATION=$BEARER SERVER="http://remote-settings.mozilla.org/v1" python script.py
```

**Using an account**:

```
$ read -s PASSWD
$ AUTHORIZATION=fxrelay-publisher:$PASSWD ENVIRONMENT=prod SERVER="http://remote-settings.mozilla.org/v1" python script.py
```
