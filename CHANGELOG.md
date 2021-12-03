# Version 4.2.0

* added support for current git commit hash as image tag

E.g. using `versions.json`
```
{
  "test/foo": "{{git}}-dev"
}
```

vindaloo will replace the `{{git}}` placeholder with 8 letters of current git hash 
resulting in e.g. `test/foo:d6ee34ae-dev`.


# Version 4.1.1

* fix: `ConfigMap` added to `__all__` in `objects.py`

# Version 4.1.0

* added support for ConfigMaps objects

```python
from vindaloo.objects import ConfigMap

CONTEXT = {'variable_1': 'This value depends on the selected environment.'}

CONFIG_MAP = ConfigMap(
    name='test-config-map',
    metadata={
        'labels': {'custom-labels': '123'},
        'annotations': {'custom-annotations': '...'},
    },
    data={
        'simple_config_key': 123,
        'file_config_key': {
            'file': 'templates/file_config.conf',
            'config': CONTEXT,
        },
    },
    binary_data={
        'simple_binary_key': b'\x76\x69\x6b\x79',
        'binary_file_config_key': {
            'file': 'templates/binary_config.conf',
        },
    },
      immutable=True,
)

K8S_OBJECTS = {
    "configmap": [CONFIG_MAP],
}
```

* orphaned `pystache` library replaced with `chevron`

# Version 4.0.0

## Breaking changes

* support for Python 3.5 is dropped

* `import versions` is replaced by:

```python
import vindaloo
versions = vindaloo.app.versions
```

* attributes (`containers`, `ports` ...) on `Deployment`, `Service`, `CronJob`, 
  e.g. are moved to full path corresponding to structure of k8s manifest:

```python
-JOB.containers['foo']['command']
+JOB.spec.template.spec.containers['foo']['command']
-SERVICE.load_balancer_ip
+SERVICE.spec.loadBalancerIP
-SERVICE.ports['http']['nodePort'
+SERVICE.spec.ports['http']['nodePort']
```

* init parameter `annotations` of `Deployment`, `CronJob` and `Job` now sets
`metadata.annotations` in manifest.
  
* init parameter `spec_annotations` to `Deployment`, `CronJob` and `Job` is added
which sets:
  * `spec.template.metadata.annotations` in `Deployment`
  * `spec.jobTemplate.spec.template.metadata.annotations` in `CronJob`
  
## Improvements

* Any parameter in manifest spec can now be set, user is not limited to attributes on `Deployment` e.g. 

```python
DEPLOYMENT.spec.something.foo.bar = 'boo'
```

* Objects can be created without init params:

```python
SERVICE = Service()
SERVICE.set_name("foo")
SERVICE.spec.type = "NodePort"
SERVICE.spec.selector = {'app': "foo"}
SERVICE.spec.ports = List({
    'http': {'port': 5001, 'targetPort': 5001, 'protocol': 'TCP'},
})
SERVICE.metadata.annotations.loadbalancer = "enabled"
```

* Method `set_name` is added to ease renaming and cloning:

```python
DEPLOYMENT2 = DEPLOYMENT.clone()
-DEPLOYMENT2.name = "sos-adminserver-private"
-DEPLOYMENT2.metadata = {'name': DEPLOYMENT2.name}
-DEPLOYMENT2.labels = {'app': DEPLOYMENT2.name}
+DEPLOYMENT2.set_name("foo2")
```
