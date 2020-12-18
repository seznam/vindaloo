from base import *
import vindaloo

ENV = {
    'ENV': "dev",
}

DEPLOYMENT.spec.template.spec.containers.foo.env.update(ENV)
DEPLOYMENT.metadata['annotations']['deploy-cluster'] = 'cluster2'

CRONJOB.spec.jobTemplate.spec.template.spec.containers.foo.command = ['echo', 'z']

SERVICE.spec.ports['http']['nodePort'] = 30666
SERVICE.spec.loadBalancerIP = '10.1.1.1' if vindaloo.app.args.cluster == 'cluster1' else '10.2.1.1'
SERVICE.metadata.annotations['certificate/https'] = 'foo.com'
