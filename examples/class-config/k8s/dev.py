import vindaloo
from base import *

ENV_PUBLIC['ENVIRONMENT'] = "avengers-dev"
ENV_PRIVATE['ENVIRONMENT'] = "avengers-dev"

DEPLOYMENT_PUBLIC.spec.template.spec.containers['avengers-server'].env = vindaloo.List(ENV_PUBLIC)
DEPLOYMENT_PRIVATE.spec.template.spec.containers['avengers-server'].env = vindaloo.List(ENV_PRIVATE)

SERVICE_PUBLIC.spec.ports['rpc']['nodePort'] = 30007
