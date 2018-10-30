from base import *


CRON_JOB.update({
    'env': [
        {
            'key': 'PONY_ENVIRONMENT',
            'val': "scif.sos-test"
        },
    ],
})

for job in K8S_OBJECTS['cronjob']:
    job['config'].update(CRON_JOB)
