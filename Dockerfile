FROM python:3.9-slim

WORKDIR /app

COPY ./root/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./root/ .

ENV PORT=5000
EXPOSE 5000

CMD ["python", "app.py"]