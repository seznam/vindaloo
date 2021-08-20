from base import *


DEPLOYMENT_ADMINWEB.update({
    'env': [
        {
            'key': 'ENVIRONMENT',
            'val': "avengers-dev"
        },
        {
            'key': 'PORT',
            'val': "8001"
        },
    ],
})

SERVICE.update({
    'ports': [
        {'port': 8000, 'nodePort': 30005, 'name': 'http'},
    ]
})
