from base import *


DEPLOYMENT_ADMINWEB.update({
    'env': [
        {
            'key': 'PONY_ENVIRONMENT',
            'val': "scif.sos-staging"
        },
        {
            'key': 'PORT',
            'val': "8001"
        },
    ],
})

SERVICE.update({
    'ports': [
        {'port': 8000, 'nodePort': 30055, 'name': 'http'},
    ]
})
