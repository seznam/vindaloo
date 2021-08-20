from base import *


DEPLOYMENT_ADMINWEB.update({
    'env': [
        {
            'key': 'ENVIRONMENT',
            'val': "avengers-test"
        },
        {
            'key': 'PORT',
            'val': "8001"
        },
        {
            'key': 'http_proxy',
            'val': "http://proxy.com:3128",
        },
        {
            'key': 'https_proxy',
            'val': "http://proxy.com:3128",
        },
    ],
})

SERVICE.update({
    'ports': [
        {'port': 8000, 'nodePort': 30020, 'name': 'http'},
    ]
})
