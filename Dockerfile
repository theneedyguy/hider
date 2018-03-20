FROM python:3.6
RUN mkdir -p /opt/hider

COPY ./app.py /opt/hider/
COPY ./requirements.txt /opt/hider/
COPY ./templates /opt/hider/templates
COPY ./uploads_enc /opt/hider/uploads_enc
COPY ./uploads_dec /opt/hider/uploads_dec
COPY ./static /opt/hider/static

RUN pip install -r /opt/hider/requirements.txt
WORKDIR /opt/hider

EXPOSE 3131

ENTRYPOINT ["python3", "app.py"]
