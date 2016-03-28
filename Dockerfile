FROM python:3-onbuild

COPY src /opt/src
RUN pip install -r /opt/src/requirements.txt

ENTRYPOINT ["python","/opt/src/social_genius_backend.py"]
