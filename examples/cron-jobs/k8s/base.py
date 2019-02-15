import datetime
import re
import sys
import os

import versions

from crontab import CRONS

CAMEL_FORM = re.compile('([a-z0-9])([A-Z])')


def get_uniq_name(name, cron_jobs_names):
    appendix = 0

    # camelCase to snake-case
    name = CAMEL_FORM.sub(r'\1-\2', name).lower().replace('_', '-')

    while True:
        full_name = '{}{}'.format(
            name,
            '-{}'.format(appendix) if appendix else '',
        )
        if full_name in cron_jobs_names:
            appendix += 1
        else:
            break

    return full_name


cron_jobs = {}

for job in CRONS:
    if job.disabled:
        continue

    # we need unique name for every cron job
    name = get_uniq_name(job.name, list(cron_jobs.keys()))

    command = job.command.replace('\\', '\\\\').replace('"', '\"')

    cron_jobs[name] = {
        'name': name,
        'schedule': job.schedule,
        'command': command,
    }

CONFIG = {
    'maintainer': "Daniel Milde <daniel.milde@firma.seznam.cz>",
    'version': versions['sos/robot'],
    'image_name': 'sos/robot',
}

CRON_JOB = {
    'image': "{}:{}".format(CONFIG['image_name'], CONFIG['version']),
    'env': [
        {
            'key': 'PONY_ENVIRONMENT',
            'val': "scif.sos-stable"
        },
    ],
}

DOCKER_FILES = [
    {
        'context_dir': "..",
        'config': CONFIG,
        'template': "Dockerfile",
        'includes': {
            'base_image': "../k8s-includes/BaseImage.include",
        },
        'pre_build_msg': """Please run first:

make clean
"""
    },
]

K8S_OBJECTS = {
    "cronjob": [
        {
            'config': {
                'ident_label': job['name'],
                'image': CRON_JOB['image'],
                'env': CRON_JOB['env'],
                'schedule': job['schedule'],
                'command': job['command'],
            },
            'template': "cron-job.yaml",
        } for job in cron_jobs.values()
    ]
}

# deploy one of cron-jobs as one time k8s job
job_name = os.getenv('DEPLOY_JOB', '')
if job_name:
    if job_name not in cron_jobs:
        raise Exception('Cron job "{}" not found. Use some of: {}'.format(job_name, list(cron_jobs.keys())))

    job = cron_jobs[job_name]

    K8S_OBJECTS = {
        "job": [
            {
                'config': {
                    'ident_label': '{}-{}'.format(job['name'], int(datetime.datetime.now().timestamp())),
                    'image': CRON_JOB['image'],
                    'env': CRON_JOB['env'],
                    'schedule': job['schedule'],
                    'command': job['command'],
                },
                'template': "job.yaml",
            }
        ]
    }
