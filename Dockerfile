FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY . .

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl ffmpeg \
 && curl -k https://gu-st.ru/content/Other/doc/russian_trusted_root_ca.cer \
    -o /usr/local/share/ca-certificates/russian_trusted_root_ca.crt \
 && update-ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Запускаем бота
CMD ["python", "main.py"]

