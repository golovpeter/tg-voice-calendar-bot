# Развертывание Telegram Calendar Bot через Helm

Этот Helm чарт позволяет развернуть Telegram Calendar Bot в Kubernetes кластере.

## Структура чарта

```
k8s/
├── Chart.yaml              # Метаданные чарта
├── values.yaml             # Значения по умолчанию
├── values-production.yaml   # Production конфигурация
├── secrets.yaml            # Шаблон секретов (заполните и не коммитьте!)
├── .helmignore             # Игнорируемые файлы
├── .gitignore               # Git ignore для секретов
├── templates/              # Kubernetes манифесты
│   ├── _helpers.tpl        # Helper функции
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── serviceaccount.yaml
│   ├── redis-pvc.yaml
│   ├── redis-deployment.yaml
│   ├── redis-service.yaml
│   └── bot-deployment.yaml
└── README.md               # Этот файл
```

## Предварительные требования

1. Kubernetes кластер (версия 1.19+)
   - Для локальной разработки можно использовать [kind](https://kind.sigs.k8s.io/) или [minikube](https://minikube.sigs.k8s.io/)
2. Helm 3.x установлен
3. `kubectl` настроен для работы с кластером
4. Docker образ бота собран
   - Для обычного кластера: образ должен быть доступен в registry
   - Для kind: образ загружается напрямую в кластер (см. ниже)

## Быстрый старт

### 1. Подготовка секретов

Заполните файл `secrets.yaml`:

```yaml
secrets:
  telegramBotToken: "YOUR_TELEGRAM_BOT_TOKEN"
  gigachatAuthKey: "YOUR_GIGACHAT_AUTH_KEY"
  googleCredentials: |
    {
      "installed": {
        "client_id": "YOUR_CLIENT_ID",
        ...
      }
    }
```

Или используйте файл `credentials.json`:

```bash
# Создать secrets.yaml из credentials.json
cat > secrets.yaml <<EOF
secrets:
  telegramBotToken: "YOUR_TOKEN"
  gigachatAuthKey: "YOUR_KEY"
  googleCredentials: |
$(cat credentials.json | sed 's/^/    /')
EOF
```

### 2. Сборка Docker образа

#### Для обычного Kubernetes кластера (с registry):

```bash
# Соберите образ
docker build -t tg-calendar-bot:latest .

# Загрузите в registry
docker tag tg-calendar-bot:latest your-registry/tg-calendar-bot:v1.0.0
docker push your-registry/tg-calendar-bot:v1.0.0
```

#### Для kind (Kubernetes in Docker):

```bash
# Соберите образ
docker build -t tg-calendar-bot:latest .

# Загрузите образ напрямую в kind кластер (не нужно пушить в registry!)
kind load docker-image tg-calendar-bot:latest --name <your-cluster-name>

# Если не знаете имя кластера, посмотрите список:
kind get clusters

# Или используйте имя по умолчанию:
kind load docker-image tg-calendar-bot:latest
```

**Важно для kind:** В `values.yaml` используется `imagePullPolicy: IfNotPresent` по умолчанию, что подходит для kind.

### 3. Установка чарта

#### Вариант A: С значениями по умолчанию

```bash
cd k8s
helm install tg-calendar-bot . \
  --set secrets.telegramBotToken='YOUR_TOKEN' \
  --set secrets.gigachatAuthKey='YOUR_KEY' \
  --set-file secrets.googleCredentials=../credentials.json
```

#### Вариант B: С файлом secrets

```bash
cd k8s
helm install tg-calendar-bot . -f secrets.yaml
```

#### Вариант C: Production конфигурация

```bash
cd k8s
helm install tg-calendar-bot . \
  -f values-production.yaml \
  -f secrets.yaml \
  --set image.repository=your-registry/tg-calendar-bot \
  --set image.tag=v1.0.0
```

#### Вариант D: Для kind (локальный кластер)

```bash
cd k8s
# Загрузите образ в kind (см. шаг 2 выше)
kind load docker-image tg-calendar-bot:latest

# Установите с настройками для kind
helm install tg-calendar-bot . \
  -f secrets.yaml \
  --set image.repository=tg-calendar-bot \
  --set image.tag=latest \
  --set image.pullPolicy=IfNotPresent
```

### 4. Проверка установки

```bash
# Проверить статус релиза
helm status tg-calendar-bot

# Проверить поды
kubectl get pods -n tg-calendar-bot

# Просмотр логов
kubectl logs -f deployment/tg-calendar-bot -n tg-calendar-bot

# Проверить все ресурсы
kubectl get all -n tg-calendar-bot
```

## Обновление

### Обновление образа

```bash
helm upgrade tg-calendar-bot . \
  --set image.tag=v1.1.0 \
  -f secrets.yaml
```

### Обновление конфигурации

```bash
# Обновить с новыми values
helm upgrade tg-calendar-bot . -f values-production.yaml -f secrets.yaml

# Обновить конкретные параметры
helm upgrade tg-calendar-bot . \
  --set bot.replicas=3 \
  --set bot.resources.limits.memory=1Gi
```

## Удаление

```bash
helm uninstall tg-calendar-bot
```

Если нужно удалить и namespace:

```bash
helm uninstall tg-calendar-bot
kubectl delete namespace tg-calendar-bot
```

## Настройка values

### Основные параметры

Отредактируйте `values.yaml` или создайте свой файл values:

```yaml
# Количество реплик бота
bot:
  replicas: 2

# Ресурсы
bot:
  resources:
    requests:
      memory: "512Mi"
      cpu: "300m"
    limits:
      memory: "1Gi"
      cpu: "1000m"

# Redis с персистентным хранилищем
redis:
  persistence:
    enabled: true
    size: 5Gi
    storageClass: "standard"
```

### Использование внешнего Redis

Если хотите использовать внешний Redis:

```yaml
redis:
  enabled: false

bot:
  env:
    redisUrl: "redis://external-redis:6379/0"
```

## Масштабирование

```bash
# Увеличить количество реплик
helm upgrade tg-calendar-bot . \
  --set bot.replicas=3 \
  -f secrets.yaml
```

## Мониторинг и логи

```bash
# Логи бота
kubectl logs -f deployment/tg-calendar-bot -n tg-calendar-bot

# Логи Redis
kubectl logs -f deployment/redis -n tg-calendar-bot

# Описание пода
kubectl describe pod <pod-name> -n tg-calendar-bot

# Выполнить команду в поде
kubectl exec -it deployment/tg-calendar-bot -n tg-calendar-bot -- /bin/bash
```

## Troubleshooting

### Проблема: Поды не запускаются

```bash
# Проверить события
kubectl get events -n tg-calendar-bot --sort-by='.lastTimestamp'

# Описание пода
kubectl describe pod <pod-name> -n tg-calendar-bot

# Проверить статус Helm релиза
helm status tg-calendar-bot
```

### Проблема: Ошибки секретов

```bash
# Проверить Secret
kubectl get secret tg-calendar-bot-secrets -n tg-calendar-bot -o yaml

# Проверить переменные окружения
kubectl exec deployment/tg-calendar-bot -n tg-calendar-bot -- env | grep -E 'TELEGRAM|GIGACHAT'
```

### Проблема: Бот не может подключиться к Redis

```bash
# Проверить Redis сервис
kubectl get svc redis -n tg-calendar-bot

# Проверить логи бота
kubectl logs deployment/tg-calendar-bot -n tg-calendar-bot | grep -i redis

# Проверить DNS
kubectl exec deployment/tg-calendar-bot -n tg-calendar-bot -- nslookup redis
```

### Проблема: Образ не найден (для kind)

```bash
# Убедитесь, что образ загружен в kind
kind load docker-image tg-calendar-bot:latest

# Проверьте, что используется правильный imagePullPolicy
helm upgrade tg-calendar-bot . \
  --set image.pullPolicy=IfNotPresent \
  -f secrets.yaml
```

### Проблема: Образ не найден (для обычного кластера)

```bash
# Проверить imagePullSecrets
kubectl get secrets -n tg-calendar-bot

# Если используете private registry, создайте secret:
kubectl create secret docker-registry regcred \
  --docker-server=your-registry.com \
  --docker-username=your-username \
  --docker-password=your-password \
  --docker-email=your-email@example.com \
  -n tg-calendar-bot

# И укажите в values.yaml:
imagePullSecrets:
  - name: regcred
```

## Production рекомендации

1. **Используйте `values-production.yaml`** как основу
2. **Включите персистентное хранилище для Redis**:
   ```yaml
   redis:
     persistence:
       enabled: true
       size: 5Gi
   ```
3. **Используйте конкретные версии образов**, а не `latest`
4. **Настройте ресурсы** в зависимости от нагрузки
5. **Используйте несколько реплик** для высокой доступности
6. **Настройте мониторинг** (Prometheus, Grafana)
7. **Используйте внешний Redis** для production (например, AWS ElastiCache, Redis Cloud)

## Примеры команд

### Полная установка с production конфигурацией

```bash
helm install tg-calendar-bot . \
  -f values-production.yaml \
  -f secrets.yaml \
  --set image.repository=your-registry/tg-calendar-bot \
  --set image.tag=v1.0.0 \
  --set redis.persistence.enabled=true \
  --set redis.persistence.size=5Gi \
  --set bot.replicas=2
```

### Обновление с новым образом

```bash
helm upgrade tg-calendar-bot . \
  --set image.tag=v1.1.0 \
  -f secrets.yaml
```

### Откат к предыдущей версии

```bash
helm rollback tg-calendar-bot
```

### Просмотр истории релизов

```bash
helm history tg-calendar-bot
```

## Дополнительные ресурсы

- [Helm документация](https://helm.sh/docs/)
- [Kubernetes документация](https://kubernetes.io/docs/)
- [kind документация](https://kind.sigs.k8s.io/docs/)

