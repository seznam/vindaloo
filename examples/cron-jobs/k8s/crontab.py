from collections import namedtuple

CronLine = namedtuple(
    'CronLine',
    (
        'schedule',
        'name',
        'command',
        'description',
        'expected_duration',
        'allowed_environments',
        'disabled',
    )
)

CRONS = [
    CronLine(
        schedule='50 23 * * *',
        name='campaignRunManager',
        command='/etc/init.d/szn-sos-admin-robot campaign_run_manager --mode expire',
        description='campaign expiration',
        expected_duration=5,
        disabled=False
    ),
    CronLine(
        schedule='0 * * * *',
        name='campaignRunManager',
        command='/etc/init.d/szn-sos-admin-robot campaign_run_manager --mode all',
        description='move all campaigns to desired states',
        expected_duration=10,
        disabled=False
    ),
]
