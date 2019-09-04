from base import *
import vindaloo

DEPLOYMENT.containers['foo']['env']['ENV'] = "dev"
SERVICE.ports['http']['nodePort'] = 30666
LOADBALANCER.load_balancer_ip = '10.1.1.1' if vindaloo.app.args.cluster == 'ko' else '10.2.1.1'
