# PrimeHub Usage


## Develop locally

start a database in the docker

```
docker run -d \
    --name postgres \
    -e POSTGRES_PASSWORD=mysecretpassword \
    -e PGDATA=/var/lib/postgresql/data/pgdata \
    -v `pwd`/psql:/var/lib/postgresql/data \
    -p 5432:5432 \
    postgres
```

execute `watcher.py` which will keep watching pod events and update usage to the database.

### Use database

open psql shell by this command:

```
docker exec -it postgres psql -U postgres
```


## Chart

The chart is the part of the `primehub`, it could be enabled by

```yaml
usage:
  enabled: true
```

Some useful values to be override:

```yaml

usage:
  enabled: true
  dbUser: postgres
  dbPassword: mysecretpassword

  image:
    repository: infuseai/primehub-usage
    pullPolicy: IfNotPresent
    tag: alpha

  # cronjob schedule for the report generator
  schedule: "0 0 * * *"
```

### Connect to database

```
kubectl -n hub exec -it primehub-usage-db-0 -- psql -U postgres
```

### See logs

```
kubectl -n hub logs deploy/primehub-usage-prober
```

### Try API

Get report dates:

```
$ curl http://127.0.0.1:5000/report/monthly
["2020/7"]
```

Get a csv file by the selected date:

```
$ curl http://127.0.0.1:5000/report/monthly/2020/7
component,group_name,user_name,gpu_core_hours,cpu_core_hours,gb_memory_hours,usage_hours,report_month
,escaped-phusers,escaped-phadmin,0.00,27.55,27.55,27.55,202007
```


## run tests

Tests could run at the root of the project

### install dependencies

You could install it in a venv

```
pip install -r requirements.txt
pip install -r requirements-tests.txt
```

Execute tests

```
python -m pytest --ignore="./venv/*.py" -v  --cov=./usage
```

Output would look like this:

```
python -m pytest --ignore="./venv/*.py" -v  --cov=./usage
============================================================================= test session starts ==============================================================================
platform darwin -- Python 3.7.6, pytest-6.0.1, py-1.9.0, pluggy-0.13.1 -- ./primehub/modules/primehub-usage/venv/bin/python
cachedir: .pytest_cache
rootdir: ./primehub/modules/primehub-usage
plugins: cov-2.10.0
collected 6 items

tests/test_utils.py::TestUtils::test_range_picking_last_month PASSED                                                                                                     [ 16%]
tests/test_utils.py::TestUtils::test_range_picking_this_month PASSED                                                                                                     [ 33%]
tests/test_utils.py::TestUtils::test_to_string PASSED                                                                                                                    [ 50%]
tests/test_watcher.py::TestWatcher::test_get_resources PASSED                                                                                                            [ 66%]
tests/test_watcher.py::TestWatcher::test_get_usage_annotation PASSED                                                                                                     [ 83%]
tests/test_watcher.py::TestWatcher::test_parse_time_for_normal_completed_pod PASSED                                                                                      [100%]

---------- coverage: platform darwin, python 3.7.6-final-0 -----------
Name                Stmts   Miss  Cover
---------------------------------------
usage/__init__.py      31      9    71%
usage/model.py         50      8    84%
usage/report.py        22     22     0%
usage/watcher.py      125     76    39%
---------------------------------------
TOTAL                 228    115    50%


============================================================================== 6 passed in 0.92s ===============================================================================
```

## Publish the development image

For development, we use `alpha` tag for `primehub-usage` development

```
docker build . -t infuseai/primehub-usage:alpha
docker push infuseai/primehub-usage:alpha
```

it could be done with the script easily:

```
./dev-release-image.sh
```

## Release Image

1. Update the VERSION file
2. Publish image with `./release-image.sh`
3. Update `PrimeHub CE` chart values.yaml

```yaml
usage:
  image:
    repository: infuseai/primehub-usage
    pullPolicy: IfNotPresent
    tag: the-version-we-released
```

### Migration legacy pods or PhDeployment

There is a `primehub-usage-legacy-pods-helper.py` in the prober 

```
kubectl -n hub exec -it primehub-usage-prober-it-is-an-example -- primehub-usage-legacy-pods-helper.py
```


After execution, it will generate patch commands if some resources are needed to patch:


```sh
# patch jupyter pod: jupyter-foo
kubectl -n hub patch pod jupyter-foo --type='json' -p '[{"op": "add", "path": "/metadata/annotations/primehub.io~1usage", "value": "{\"component\": \"jupyter\", \"component_name\": \"jupyter-foo\", \"group\": \"phusers\", \"user\": \"foo\", \"instance_type\": \"cpu-1\"}"}]'

# patch phdeployment deployment: tmp-1gawm, it might restart pods if anything have changed
kubectl -n hub patch deployment tmp-1gawm --type='json' -p '[{"op": "add", "path": "/spec/template/metadata/annotations/primehub.io~1usage", "value": "{\"component\": \"deployment\", \"component_name\": \"tmp-1gawm\", \"group\": \"model-deployment-test-group\", \"user\": \"ericy\", \"instance_type\": \"cpu-tiny\"}"}]'
```

Please review the commands before applying them.