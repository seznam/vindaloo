from base import *


DEPLOYMENT_ADMINWEB.update({
    'env': [
        {
            'key': 'ENVIRONMENT',
            'val': "avengers-stable"
        },
        {
            'key': 'PORT',
            'val': "8001"
        },
    ],
    # Anotace pro produkcniho promethea admins3
    'spec_annotations': [
        {
            'key': 'metrics.scrape',
            'val': "true"
        },
        {
            'key': 'metrics.port',
            'val': "8000"
        },
        {
            'key': 'metrics.path',
            'val': "/monitoring/prometheus"
        },
        {
            'key': 'log-retention',
            'val': "3w"
        },
        {
            'key': 'team',
            'val': "avengers"
        },
    ]
})

SERVICE.update({
    'ports': [
        {'port': 8000, 'nodePort': 30056, 'name': 'http'},
    ]
})
