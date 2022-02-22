FROM python:3.8

RUN apt-get update && apt-get install -y

WORKDIR /app

COPY requirements.txt requirements.txt

RUN pip3 install -r requirements.txt

COPY . .

ENTRYPOINT ["./entrypoint.sh"]