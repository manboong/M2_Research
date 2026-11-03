FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY collector /app/collector
COPY network /app/network
COPY research_cli.py /app/research_cli.py
USER 10001:10001
CMD ["python", "-m", "research_cli", "run-demo"]
