FROM python:latest

WORKDIR /app

COPY "fake.py" "./bot.py"

RUN pip install discord
RUN pip install requests
RUN pip install Pillow
RUN pip install numpy

CMD "python" "bot.py"
