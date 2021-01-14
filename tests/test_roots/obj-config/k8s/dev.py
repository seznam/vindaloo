from base import *
import vindaloo

DEPLOYMENT.spec.template.spec.containers.foo.env['ENV'] = "dev"
SERVICE.spec.ports['http']['nodePort'] = 30666
LOADBALANCER.spec.loadBalancerIP = '10.1.1.1' if vindaloo.app.args.cluster == 'cluster1' else '10.2.1.1'
