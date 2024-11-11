# Remote Settings Cronjob Example

Turn a source of data into records on Remote Settings.

* [Compliant with specs](https://remote-settings.readthedocs.io/en/latest/support.html#how-do-i-automate-the-publication-of-records-forever)
* Dual sign-off
* Lint
* Github Action CI

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
$ curl -X PUT http://localhost:8888/v1/buckets/main-workspace/collections/product-integrity \
     -H 'Content-Type:application/json' \
     -u editor:3d1t0r
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
