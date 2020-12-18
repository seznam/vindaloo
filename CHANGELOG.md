
# Version 2.0.0

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
