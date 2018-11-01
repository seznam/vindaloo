{{#includes}}{{&base_image}}{{/includes}}
LABEL maintainer="{{{maintainer}}}"
LABEL description="SOS robot"

RUN apt-get install -y \
        szn-python-frpcstorage \
        szn-python-mysqldbwrapper \
        szn-python2.7-chartdirector>=5.0.0

RUN groupadd -r --gid=1000 sos-robot && \
    useradd -r --uid=1000 -b /www/sos/admin-robot -d /www/sos/admin-robot -m -s /bin/bash -g sos-robot sos-robot

COPY robot/robot /www/sos/admin-robot/robot
COPY robot/src /www/sos/admin-robot/bin
COPY robot/debian/szn-sos-admin-robot.init /etc/init.d/szn-sos-admin-robot
COPY robot/templ /www/sos/admin-robot/templ

COPY libs/template.py /www/sos/admin-robot/bin/librobot/template.py
COPY libs/mailer.py /www/sos/admin-robot/bin/librobot/mailer.py

RUN mkdir -p /www/sos/admin-robot/log
RUN chown sos-robot /www/sos/admin-robot/log

ENV USER="sos-robot"
USER sos-robot
LABEL version="{{version}}"
