{{#includes}}{{&base_image}}{{/includes}}
LABEL maintainer="{{{maintainer}}}"
LABEL description="avengers robot"

COPY robot/Pipfile robot/Pipfile.lock /home/avengers/robot/
RUN cd /home/avengers/robot && https_proxy={{https_proxy}} pipenv install --system --deploy

COPY robot /home/avengers/robot

LABEL version="{{version}}"
