

# Vindaloo
[![Build Status](https://travis-ci.org/seznam/vindaloo.svg?branch=master)](https://travis-ci.org/seznam/vindaloo)
[![codecov](https://codecov.io/gh/seznam/vindaloo/branch/master/graph/badge.svg)](https://codecov.io/gh/seznam/vindaloo)

`Vindaloo` is universal deployer into kubernetes. It easily provides one project to work with multiple docker registries, repositories, kubernetes clusters and namespaces without the need of duplicating configuration.

Requirements
------------

Python 3.5 and higher is required.


Installation
------------

Download latest [pex binary](https://github.com/seznam/vindaloo/raw/master/latest/vindaloo.pex)

```
sudo wget -O /usr/bin/vindaloo https://github.com/seznam/vindaloo/raw/master/latest/vindaloo.pex
sudo chmod +x /usr/bin/vindaloo
```

or use pip:

```
pip3 install vindaloo
```

What can it do
--------------

- build docker images
- push to docker registry
- deploy to k8s
- check versions in k8s
- edit k8s secrets
- bash completion

Why to use Vindaloo and not X
-----------------------------

- can be distributed as one executable file, no need to install
- configuration using Python files which implies little code duplication and huge expressivity
- powerful templating using Mustache language (pystache)
- can include parts of templates in Dockerfiles
- can build multiple images from one component
- can change docker context dir for building an image
- high test coverage
- can bash-complete options, environments and images used in the component

Configuration
-------------

`Vindaloo` uses two levels of configuration.

"Global" configuration is expected to be placed in `vindaloo_conf.py` and
defines a list of environments, corresponding k8s namespaces and k8s clusters.
`vindaloo_conf.py` can be placed into the directory of the deployed component or
any parent directory, e.g. into your home folder if you share the same k8s environment (namespaces, clusters)
for all your projects.

Every project/component/service using `Vindaloo` must have directory `k8s`,
which contains configuration for build and deployment of this component.
`Vindaloo` generates deployments, Dockerfiles, etc. and calls `kubectl` and `docker` using this configuration.


Typical usage
-------------

```
cd projekt
vindaloo init .

vindaloo build
vindaloo push
vindaloo deploy dev cluster1
vindaloo deploy dev cluster2

vindaloo versions
```

Bash completion
---------------

Add this to your `~/.bashrc` to enable bash completion:

```
source <(vindaloo completion)
```


Component configuration
-----------------------

```
vindaloo_conf.py
k8s
    templates
        - Dockerfile
        - deployment.yaml
        - service.yaml

    - base.py
    - dev.py
    - test.py
    - stable.py
    - versions.json
```

`vindaloo_conf.py` contains the definition of deployment environments (dev, test, prerelease, stable), corresponding k8s namespaces and list of k8s clusters.
The file can be placed in the directory of the component or in any parent dir (if we share the configuration among more components).

Configuration of the component's deployment is placed in the `k8s` directory, where a couple of files is located:

`templates` contains templates of generated files (yamls, Dockerfiles).
They use mustache syntax, which provides simple loops etc.
Syntax: https://mustache.github.io/mustache.5.html

`base.py` is the basis of configuration and should contain everything, what will have all the environment configurations in common.

`[dev/test/...].py` are config files for individual k8s environments and contain settings specific for them (e.g. nodePort).

`versions.json` is a configuration file defining versions of images we want to build/deploy.
We can easily read and modify it programmatically because it's valid JSON.


Example vindaloo_conf.py
------------------------

```
ENVS = {
    'dev': {
        'k8s_namespace': 'avengers-dev',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': 'foo-registry.com',
    },
    'test': {
        'k8s_namespace': 'avengers-test',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': 'foo-registry.com',
    },
    'staging': {
        'k8s_namespace': 'avengers-staging',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': 'foo-registry.com',
    },
    'stable': {
        'k8s_namespace': 'avengers-stable',
        'k8s_clusters': ['cluster1', 'cluster2'],
        'docker_registry': 'foo-registry.com',
    },
}

K8S_CLUSTER_ALIASES = {
    'c1': 'cluster1',
    'c2': 'cluster2',
}
```


Example base.py
---------------

```
# import image versions from versions.json as a dict (awfull hack)
import versions

# will be used further
CONFIG = {
    'maintainer': "John Doe <john.doe@domain.com>",
    'version': versions['avengers/cool_app'],
    'image_name': 'avengers/cool_app',
}

# will be used further
DEPLOYMENT = {
    'replicas': 2,
    'ident_label': "cool-app",
    'image': "{}:{}".format(CONFIG['image_name'], CONFIG['version']),
    'container_port': 6666,
    'env': [
        {
            'key': 'BACKEND',
            'val': "some-url.com"
        },
    ]
}

# will be used further
SERVICE = {
    'app_name': "cool-app",
    'ident_label': "cool-app",
    'container_port': 6666,
    'port': 31666,
}

# Dockerfiles configuration
# list of dicts with keys:
# config - dict with configuration
# template - file with Dockerfile template
# context_dir - directory passed to docker (optional)
# pre_build_msg - message shown before the build is started (optional)
# includes - loading of files to be included into Dockerfile.
Every file will be processed with mustache with same context as main template.

DOCKER_FILES = [
    {
        'context_dir': ".",
        'config': CONFIG,
        'template': "Dockerfile",
        'pre_build_msg': """Please run first:

make clean
"""
        'includes': {
             'some_name': 'path/to/file/with/template',
        }
    }
]

# K8S configuration
K8S_OBJECTS = {
    "deployment": [
        {
            'config': DEPLOYMENT,
            'template': "deployment.yaml",
        },
    ],
    "service": [
        {
            'config': SERVICE,
            'template': "service.yaml",
        },
    ]
}
```

Example dev.py
--------------

```
from base import *  #  config inheritance

# Here we can overload or modify everything what was defined in base.py


DEPLOYMENT.update({
    'env': [
        {
            'key': 'BACKEND',
            'val': "some-other-url.com"
        },
    ]
})

SERVICE.update({
    'port': 32666,
})
```

Example versions.json
---------------------

```
{
  "avengers/cool_app": "1.0.0"
}
```


Example Dockerfile
------------------

```
{{#includes}}{{&base_image}}{{/includes}}
LABEL maintainer="{{{maintainer}}}"
LABEL description="Avengers cool app"

COPY ...
RUN ...
CMD ...

LABEL version="{{version}}"
```

Example deployment.yaml
-----------------------

```
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: {{ident_label}}
spec:
  replicas: {{replicas}}
  template:
    metadata:
      name: {{ident_label}}
      labels:
        app: {{ident_label}}
    spec:
      containers:
      - name: {{ident_label}}
        image: {{registry}}/{{image}}
        ports:
        - containerPort: {{container_port}}
        livenessProbe:
          initialDelaySeconds: 5
          periodSeconds: 5
          httpGet:
            path: /
            port: {{container_port}}
```

Example service.yaml
--------------------

```
apiVersion: v1
kind: Service
metadata:
  name: {{ident_label}}
  labels:
    name: {{ident_label}}
spec:
  type: NodePort
  ports:
  - name: http
    nodePort: {{port}}
    port: {{container_port}}
    protocol: TCP
  selector:
    app: {{app_name}}
```

Advanced configuration
---------------------------

Configuration written in Python allows us to solve a far more complicated scenarios.

We can build more images from one component and the deploy them into one pod.
See the [example](examples/multi-image/k8s).

We can create python module similar to crontab and generate CronJobs dynamically using it.
Then if we need to run some task out of schedule, we can deploy one k8s Job by passing ENV variable for example.

```
DEPLOY_JOB=campaign-run-manager vindaloo deploy dev
```

See the [example](examples/cron-jobs/k8s).

Experimental configuration using classes
----------------------------------------

Kubernetes manifests can be configured using dicts (classical way) or classes (experimental).
This feature is not considered stable yet and should be used with caution.
The advantage is that base configuration can be more easily changed in environment config files.

The data structure used in classes is basically the same as in K8S JSON manifests with some exceptions.
All `name`, `value` lists used in K8S (i.e. `env`) are stored as `key`: `value` python dicts.

See the [example](examples/class-config/k8s).

How to build `vindaloo`
-----------------------

```
pip install pystache pex

make

# success
```
