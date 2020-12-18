import vindaloo
from base import *

ENV = {
    'ENVIRONMENT' = "avengers-test",
    'WEB_CONCURRENCY': "10",
}

DEPLOYMENT_PUBLIC.spec.template.spec.containers['avengers-server'].env.update(ENV)
DEPLOYMENT_PRIVATE.spec.template.spec.containers['avengers-server'].env.update(ENV)

SERVICE_PUBLIC.spec.ports['rpc']['nodePort'] = 30013
