from base import *


CRON_JOB.update({
    'env': [
        {
            'key': 'ENVIRONMENT',
            'val': "avengers-dev"
        },
    ],
})

for job in K8S_OBJECTS.get('cronjob', []):
    job['config'].update(CRON_JOB)
for job in K8S_OBJECTS.get('job', []):
    job['config'].update(CRON_JOB)
