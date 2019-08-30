from base import *

ENV_PUBLIC['ENVIRONMENT'] = "avengers-dev"
ENV_PRIVATE['ENVIRONMENT'] = "avengers-dev"

SERVICE_PUBLIC.ports['rpc']['nodePort'] = 30007
