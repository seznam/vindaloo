import vindaloo
from base import *

DEPLOYMENT_PUBLIC.spec.template.spec.containers['avengers-server'].env.ENVIRONMENT = "avengers-dev"
DEPLOYMENT_PRIVATE.spec.template.spec.containers['avengers-server'].env.ENVIRONMENT = "avengers-dev"

SERVICE_PUBLIC.spec.ports['rpc']['nodePort'] = 30007
