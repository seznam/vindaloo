from base import *


DEPLOYMENT_ADMINWEB.update({
    'env': [
        {
            'key': 'PONY_ENVIRONMENT',
            'val': "scif.sos-stable"
        },
        {
            'key': 'PORT',
            'val': "8001"
        },
    ],
    # Anotace pro produkcniho promethea admins3
    'spec_annotations': [
        {
            'key': 'cz.seznam.admins3.metrics.scrape',
            'val': "true"
        },
        {
            'key': 'cz.seznam.admins3.metrics.port',
            'val': "8000"
        },
        {
            'key': 'cz.seznam.admins3.metrics.path',
            'val': "/monitoring/prometheus"
        },
        {
            'key': 'scif.cz/log-retention',
            'val': "3w"
        },
        {
            'key': 'team',
            'val': "sos-vyvoj@firma.seznam.cz"
        },
    ]
})

SERVICE.update({
    'ports': [
        {'port': 8000, 'nodePort': 30056, 'name': 'http'},
    ]
})
