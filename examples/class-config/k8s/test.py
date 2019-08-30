from base import *

ENV_PUBLIC['ENVIRONMENT'] = "avengers-test"
ENV_PRIVATE['ENVIRONMENT'] = "avengers-test"

SERVICE_PUBLIC.ports['rpc']['nodePort'] = 30013
