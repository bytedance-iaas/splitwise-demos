FROM python:3.12 AS python

RUN mkdir /app
COPY requirements.txt /app/requirements.txt
COPY proxy.py /app/proxy.py

WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/pip \
    python3 -m pip install -r requirements.txt

ENTRYPOINT ["uvicorn", "proxy:app"]