FROM python:3.11-slim

WORKDIR /app

COPY Pipfile Pipfile.lock /app/

RUN pip install pipenv && pipenv install --system --deploy --ignore-pipfile

COPY . /app

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8080", "main:app"]
