from base import *


CRON_JOB.update({
    'env': [
        {
            'key': 'PONY_ENVIRONMENT',
            'val': "scif.sos-dev"
        },
    ],
})

for job in K8S_OBJECTS.get('cronjob', []):
    job['config'].update(CRON_JOB)
for job in K8S_OBJECTS.get('job', []):
    job['config'].update(CRON_JOB)
