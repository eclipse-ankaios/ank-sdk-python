FROM python:3.12-slim-bookworm as base

RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install \
    git \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app

FROM base as prod

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY ./app.py ./

CMD [ "python", "-u", "./app.py" ]

FROM base as dev

COPY . ./ank-sdk-python
RUN pip install ./ank-sdk-python
COPY examples/follow_state/app.py ./

CMD [ "python", "-u", "./app.py" ]