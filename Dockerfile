FROM python:latest

WORKDIR /app

COPY "fake.py" "."
COPY "token" "."

RUN pip install discord
RUN pip install requests
RUN pip install Pillow
RUN pip install numpy

CMD "python" "fake.py"
