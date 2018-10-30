EXAMPLE_VINDALOO_CONF = """
DEV = "dev"
TEST = "test"
STAGING = "staging"
STABLE = "stable"

LOCAL_ENVS = [DEV, TEST, STAGING, STABLE]

K8S_NAMESPACES = {{
    DEV: "{k8s_prefix}-dev",
    TEST: "{k8s_prefix}-test",
    STAGING: "{k8s_prefix}-staging",
    STABLE: "{k8s_prefix}-stable",
}}

K8S_CLUSTERS = {{
    "ko": "kube1.ko",
    "ng": "kube1.ng",
}}

ENVS_WITH_PROD_REGISTRY = [STAGING, STABLE]
"""

EXAMPLE_BASE = """
import versions

CONFIG = {{
    'maintainer': "{maintainer_name} <{maintainer_email}>",
    'version': versions['{image_name}'],
    'image_name': '{image_name}',
}}

DEPLOYMENT = {{
    'replicas': 1,
    'ident_label': "{ident_label}",
    'image': "{{}}:{{}}".format(CONFIG['image_name'], CONFIG['version']),
    'env': [
        {{
            'key': 'ENVIRONMENT',
            'val': "stable",  # Pretizit v tech co podedi.
        }},
    ],
    'spec_annotations': [],
}}

DOCKER_FILES = [
    {{
        'config': CONFIG,
        'template': "Dockerfile",
    }},
]

K8S_OBJECTS = {{
    "deployment": [
        {{
            'config': DEPLOYMENT,
            'template': "deployment.yaml",
        }},
    ],
}}

"""

EXAMPLE_DEV = """
from base import *


DEPLOYMENT.update({
    'env': [
        {
            'key': 'ENVIRONMENT',
            'val': "dev"
        },
    ],
})

"""

EXAMPLE_DOCKERFILE = """FROM doc.ker.dev.dszn.cz/debian:stretch
LABEL maintainer="{{{maintainer}}}"
LABEL description=""

EXPOSE 8000

# Nasetujeme český UTF-8 locale a globální jazyk.
RUN echo "cs_CZ.UTF-8 UTF-8" >> /etc/locale.gen
RUN echo "en_US.UTF-8 UTF-8" >> /etc/locale.gen
RUN locale-gen
# Tohle je nasetovani jazyka pouze lokalne behem buildu.
ENV LANG="en_US.UTF-8"
ENV LC_CTYPE="en_US.UTF-8"

RUN apt-get update && apt-get upgrade -y

LABEL version="{{version}}"
"""

EXAMPLE_DEPLOYMENT = """apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: {{ident_label}}
spec:
  replicas: {{replicas}}
  template:
    metadata:
      name: "{{ident_label}}"
      labels:
        app: "{{ident_label}}"
      annotations:
        {{#spec_annotations}}
        {{key}}: "{{val}}"
        {{/spec_annotations}}
    spec:
      containers:
      - name: "{{ident_label}}"
        image: {{registry}}/{{image}}
        env:
        {{#env}}
        - name: {{key}}
          value: {{val}}
        {{/env}}
"""

EXAMPLE_SERVICE = """apiVersion: v1
kind: Service
metadata:
  name: {{ident_label}}
  labels:
    app: {{app_label}}
spec:
  type: NodePort
  ports:
  - port: 9213
    nodePort: 31515
    protocol: TCP
  selector:
    app: {{app_label}}
"""
