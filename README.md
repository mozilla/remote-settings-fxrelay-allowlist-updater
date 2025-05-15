# Remote Settings Cronjob Example

Turn a source of data into records on Remote Settings.

* [Compliant with specs](https://remote-settings.readthedocs.io/en/latest/support.html#how-do-i-automate-the-publication-of-records-forever)
* Dry run
* Dual sign-off
* Lint
* Github Action CI
* Tests with `kinto_http` mocks

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
$ curl -X PUT http://localhost:8888/v1/buckets/main-workspace/collections/product-integrity
```

And run the script:

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

### On the DEV server

* Login on the DEV Admin UI and copy the Bearer header value (UI top right bar)

And use it to run the script:

```
$ read -s BEARER
$ AUTHORIZATION=$BEARER SERVER="http://remote-settings-dev.allizom.org/v1" python script.py
