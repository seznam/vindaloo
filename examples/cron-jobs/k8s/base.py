from jobs import JOBS
import versions


CONFIG = {
    'maintainer': "Daniel Milde <daniel.milde@firma.seznam.cz>",
    'version': versions['sos/robot'],
    'image_name': 'doc.ker.dev.dszn.cz/sos/robot',
    'https_proxy': 'http://proxy.dev.dszn.cz:3128',
}

CRON_JOB = {
    'file_version': 3,
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
        'pre_build_msg': """Prosim nejdriv spust:

make clean
"""
    },
]

K8S_OBJECTS = {
    "cronjob": [
        {
            'config': {
                'ident_label': 'cron-job-{}'.format(job['name']),
                'file_version': CRON_JOB['file_version'],
                'image': CRON_JOB['image'],
                'env': CRON_JOB['env'],
                'schedule': job['schedule'],
                'command': job['command'],
            },
            'template': "cron-job.yaml",
        } for job in JOBS
    ],
}
