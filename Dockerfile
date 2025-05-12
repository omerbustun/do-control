FROM python:alpine

WORKDIR /app

# Install system dependencies
RUN apk add --no-cache gcc python3-dev musl-dev linux-headers librdkafka-dev

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "console.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]