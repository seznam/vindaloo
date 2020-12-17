from base import CRONJOB, DEPLOYMENT, SERVICE, K8S_OBJECTS
import vindaloo

CRONJOB.spec.jobTemplate.spec.template.spec.containers.foo.command = ['echo', 'z']

DEPLOYMENT.spec.template.spec.containers.foo.env.ENV = "dev"
DEPLOYMENT.metadata.annotations['deploy-cluster'] = 'cluster2'

SERVICE.spec.ports['http']['nodePort'] = 30666
SERVICE.spec.loadBalancerIP = '10.1.1.1' if vindaloo.app.args.cluster == 'cluster1' else '10.2.1.1'
SERVICE.metadata.annotations['certificate/https'] = 'foo.com'
