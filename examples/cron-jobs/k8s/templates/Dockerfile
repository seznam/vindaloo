{{#includes}}{{&base_image}}{{/includes}}
LABEL maintainer="{{{maintainer}}}"
LABEL description="SOS robot"

RUN apt-get install -y \
        szn-python3.5-chartdirector>=5.0.0 \
        python3-pymssql

COPY robot/Pipfile robot/Pipfile.lock /www/sos/admin-robot/
RUN cd /www/sos/admin-robot && https_proxy={{https_proxy}} pipenv install --system --deploy

COPY robot/robot /www/sos/admin-robot/robot
COPY robot/src /www/sos/admin-robot/bin
COPY robot/debian/szn-sos-admin-robot.init /etc/init.d/szn-sos-admin-robot
COPY robot/templ /www/sos/admin-robot/templ
COPY robot/conf/admin-robot.conf /www/sos/admin-robot/conf/admin-robot.conf
COPY maintenance/maintenance /www/sos/maintenance

COPY libs/template.py /www/sos/admin-robot/bin/librobot/template.py
COPY libs/mailer.py /www/sos/admin-robot/bin/librobot/mailer.py

RUN mkdir -p /www/sos/admin-robot/log
RUN mkdir -p /www/sos/maintenance/log

LABEL version="{{version}}"
