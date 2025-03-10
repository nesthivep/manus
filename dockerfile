FROM python:3.12-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install --no-cache-dir fastapi uvicorn jinja2

RUN mkdir -p config

RUN if [ ! -f config/config.toml ]; then cp config/config.example.toml config/config.toml; fi

ENV PYTHONUNBUFFERED=1

EXPOSE 5172

CMD ["sh", "-c", "if [ \"$MODE\" = \"cli\" ]; then python main.py; else python app.py; fi"]
