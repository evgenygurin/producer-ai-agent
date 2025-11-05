# Руководство по развертыванию Producer AI Agent с R2R и n8n

Полное руководство по развертыванию интегрированной системы с R2R (RAG), n8n (автоматизация), Auth0 (аутентификация), Supabase/Prisma (БД).

## Архитектура системы

```
┌─────────────────────────────────────────────────────────────┐
│                     Producer AI Platform                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │  Auth0   │──▶│   n8n    │──▶│   API    │──▶│   R2R    │ │
│  │  (Auth)  │   │(Workflow)│   │ Gateway  │   │  (RAG)   │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
│                        │              │              │       │
│                        ▼              ▼              ▼       │
│                 ┌──────────┐   ┌──────────┐  ┌──────────┐  │
│                 │ Supabase │   │  Redis   │  │PostgreSQL│  │
│                 │(Metadata)│   │ (Cache)  │  │ (Vectors)│  │
│                 └──────────┘   └──────────┘  └──────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Предварительные требования

### Обязательные компоненты:
- Docker >= 20.10
- Docker Compose >= 2.0
- Git
- OpenAI API key (для R2R)

### Опциональные компоненты:
- Auth0 аккаунт (для аутентификации)
- Supabase проект (для продакшн БД)
- AI Music API key (для генерации музыки)

## Шаг 1: Клонирование и настройка

```bash
# Клонировать репозиторий
git clone https://github.com/evgenygurin/producer-ai-agent.git
cd producer-ai-agent

# Создать .env файл из примера
cp .env.example .env
```

## Шаг 2: Настройка переменных окружения

Отредактируйте `.env` файл:

### 2.1 Обязательные переменные

```env
# OpenAI (для R2R)
OPENAI_API_KEY=sk-your-openai-key-here

# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_secure_password_here
POSTGRES_DB=r2r
N8N_DB=n8n

# n8n
N8N_USER=admin
N8N_PASSWORD=your_secure_n8n_password
N8N_HOST=localhost
WEBHOOK_URL=http://localhost:5678
```

### 2.2 Опциональные переменные

```env
# AI Music API (если используете генерацию музыки)
AIMUSIC_API_KEY=your_aimusic_api_key

# Auth0 (если нужна аутентификация)
AUTH0_ENABLED=true
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your_client_id
AUTH0_CLIENT_SECRET=your_client_secret
AUTH0_AUDIENCE=https://your-api-identifier

# Supabase (опционально, для продакшн)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

## Шаг 3: Настройка Auth0 (опционально)

Если вы хотите использовать Auth0 для аутентификации:

### 3.1 Создание приложения в Auth0

1. Зайдите в [Auth0 Dashboard](https://manage.auth0.com/)
2. Перейдите в **Applications** → **Create Application**
3. Выберите **"Regular Web Application"**
4. Сохраните **Domain**, **Client ID**, и **Client Secret**

### 3.2 Настройка API в Auth0

1. Перейдите в **Applications** → **APIs**
2. Создайте новый API:
   - Name: `Producer AI API`
   - Identifier: `https://api.producer-ai.com`
   - Signing Algorithm: `RS256`

### 3.3 Настройка Callback URLs

В настройках приложения добавьте:

```
Allowed Callback URLs:
http://localhost:5678/rest/oauth2-credential/callback
http://localhost:8000/callback

Allowed Logout URLs:
http://localhost:5678
http://localhost:8000

Allowed Web Origins:
http://localhost:5678
http://localhost:8000
```

### 3.4 Включение в .env

```env
AUTH0_ENABLED=true
AUTH0_DOMAIN=your-tenant.auth0.com
AUTH0_CLIENT_ID=your_client_id_here
AUTH0_CLIENT_SECRET=your_client_secret_here
AUTH0_AUDIENCE=https://api.producer-ai.com
```

## Шаг 4: Запуск системы

### 4.1 Запуск через Docker Compose

```bash
# Запустить все сервисы
docker-compose up -d

# Проверить статус
docker-compose ps

# Просмотр логов
docker-compose logs -f
```

### 4.2 Проверка запуска сервисов

Подождите 1-2 минуты, пока все сервисы запустятся, затем проверьте:

```bash
# PostgreSQL
docker-compose exec postgres pg_isready

# R2R API
curl http://localhost:7272/v2/health

# n8n
curl http://localhost:5678/healthz

# API Gateway
curl http://localhost:8000/health

# Redis
docker-compose exec redis redis-cli ping
```

## Шаг 5: Настройка n8n

### 5.1 Вход в n8n

1. Откройте браузер: http://localhost:5678
2. Войдите используя учетные данные из `.env`:
   - Username: `admin` (или значение `N8N_USER`)
   - Password: ваш `N8N_PASSWORD`

### 5.2 Импорт готовых workflows

1. В n8n перейдите в **Workflows** → **Import from File**
2. Импортируйте файлы из папки `n8n-workflows/`:
   - `rag-music-generation.json` - RAG + генерация музыки
   - `document-ingestion.json` - загрузка документов в R2R

### 5.3 Настройка PostgreSQL credentials в n8n

1. Перейдите в **Credentials** → **Add Credential**
2. Выберите **Postgres**
3. Заполните данные:
   - Host: `postgres`
   - Port: `5432`
   - Database: `r2r`
   - User: значение из `POSTGRES_USER`
   - Password: значение из `POSTGRES_PASSWORD`
4. Сохраните как `postgres-credentials`

## Шаг 6: Инициализация базы данных

### 6.1 Применение Prisma миграций

```bash
# Установить Prisma CLI (если еще не установлен)
npm install -g prisma

# Генерировать Prisma клиент
cd producer-ai-agent
npx prisma generate

# Применить миграции
npx prisma db push
```

### 6.2 Проверка таблиц

```bash
# Подключиться к PostgreSQL
docker-compose exec postgres psql -U postgres -d r2r

# Проверить схему metadata
\dt metadata.*

# Должны увидеть:
# - metadata.users
# - metadata.workflows
# - metadata.rag_sessions
# - metadata.music_generations
# - metadata.collections

\q
```

## Шаг 7: Тестирование интеграции

### 7.1 Тест R2R API

```bash
# Health check
curl http://localhost:8000/health

# Создать коллекцию
curl -X POST http://localhost:8000/api/v1/rag/collections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "music-references",
    "description": "Music generation context and references"
  }'

# Загрузить документы
curl -X POST http://localhost:8000/api/v1/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "content": "Uplifting pop music with energetic beats and positive vibes",
        "title": "Pop Music Reference",
        "metadata": {"genre": "pop", "mood": "uplifting"}
      }
    ],
    "collection_id": "music-references"
  }'

# Выполнить RAG запрос
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Generate uplifting music",
    "limit": 5,
    "collection_id": "music-references"
  }'
```

### 7.2 Тест n8n Webhook

```bash
# Тест document ingestion workflow
curl -X POST http://localhost:5678/webhook/ingest-documents \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "content": "Electronic dance music with heavy bass",
        "title": "EDM Reference"
      }
    ],
    "collection_id": "music-references"
  }'

# Тест RAG-powered music generation workflow
curl -X POST http://localhost:5678/webhook/generate-music \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create energetic dance music",
    "style": "electronic dance",
    "instrumental": false,
    "voice_gender": "female"
  }'
```

### 7.3 Тест генерации музыки (если настроен AIMUSIC_API_KEY)

```bash
# Проверить кредиты
curl http://localhost:8000/api/v1/music/credits

# Сгенерировать музыку
curl -X POST http://localhost:8000/api/v1/music/generate \
  -H "Content-Type: application/json" \
  -d '{
    "custom_mode": false,
    "gpt_description_prompt": "Upbeat electronic dance music",
    "make_instrumental": false,
    "mv": "chirp-v4",
    "voice_gender": "female"
  }'
```

## Шаг 8: Использование с Auth0 (если включен)

### 8.1 Получение токена

```bash
# Получить токен через Client Credentials flow
curl --request POST \
  --url https://YOUR_DOMAIN.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id":"YOUR_CLIENT_ID",
    "client_secret":"YOUR_CLIENT_SECRET",
    "audience":"https://api.producer-ai.com",
    "grant_type":"client_credentials"
  }'
```

### 8.2 Использование токена в запросах

```bash
# Сохраните токен
TOKEN="your_access_token_here"

# Используйте в запросах
curl -X POST http://localhost:8000/api/v1/rag/ingest \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"documents": [...]}'
```

## Шаг 9: Мониторинг и отладка

### 9.1 Просмотр логов

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f r2r
docker-compose logs -f n8n
docker-compose logs -f api-gateway
docker-compose logs -f postgres
```

### 9.2 Проверка базы данных

```bash
# Подключиться к PostgreSQL
docker-compose exec postgres psql -U postgres -d r2r

# Проверить workflow логи
SELECT * FROM metadata.workflows ORDER BY created_at DESC LIMIT 10;

# Проверить RAG сессии
SELECT * FROM metadata.rag_sessions ORDER BY created_at DESC LIMIT 10;

# Проверить музыкальную генерацию (если есть)
SELECT * FROM metadata.music_generations ORDER BY created_at DESC LIMIT 10;
```

### 9.3 R2R Collections

```bash
# Список коллекций
curl http://localhost:8000/api/v1/rag/collections

# Поиск в коллекции
curl -X POST http://localhost:8000/api/v1/rag/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "dance music",
    "limit": 10,
    "collection_id": "music-references"
  }'
```

## Шаг 10: Продакшн развертывание

### 10.1 Использование Supabase вместо локального PostgreSQL

1. Создайте проект в [Supabase](https://supabase.com)
2. Получите connection string
3. Обновите `.env`:

```env
POSTGRES_URL=postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
SUPABASE_URL=https://[PROJECT].supabase.co
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

4. Примените миграции:

```bash
npx prisma db push
```

### 10.2 SSL/TLS и Reverse Proxy

Для продакшн используйте Nginx или Traefik с SSL:

```nginx
# /etc/nginx/sites-available/producer-ai
server {
    listen 443 ssl http2;
    server_name api.producer-ai.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # API Gateway
    location /api/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # n8n
    location /n8n/ {
        proxy_pass http://localhost:5678;
        proxy_set_header Host $host;
    }

    # R2R (опционально, если нужен прямой доступ)
    location /r2r/ {
        proxy_pass http://localhost:7272;
        proxy_set_header Host $host;
    }
}
```

### 10.3 Безопасность

1. **Измените пароли по умолчанию** во всех сервисах
2. **Ограничьте доступ** к портам через firewall
3. **Используйте secrets management** (AWS Secrets Manager, HashiCorp Vault)
4. **Включите SSL/TLS** для всех HTTP соединений
5. **Настройте rate limiting** на API Gateway
6. **Регулярно обновляйте** Docker образы

## Частые проблемы и решения

### Проблема: R2R не запускается

**Решение:**
```bash
# Проверьте логи
docker-compose logs r2r

# Убедитесь что OPENAI_API_KEY установлен
echo $OPENAI_API_KEY

# Перезапустите сервис
docker-compose restart r2r
```

### Проблема: n8n не может подключиться к PostgreSQL

**Решение:**
```bash
# Проверьте что PostgreSQL запущен
docker-compose ps postgres

# Проверьте credentials в n8n
# Используйте hostname: postgres (не localhost)
```

### Проблема: Auth0 токены не валидируются

**Решение:**
1. Проверьте что `AUTH0_DOMAIN` без `https://`
2. Проверьте `AUTH0_AUDIENCE` совпадает с API identifier
3. Очистите кэш JWKS:
```bash
docker-compose restart api-gateway
```

### Проблема: Out of memory

**Решение:**
```bash
# Увеличьте Docker memory limit
# Или ограничьте память для сервисов в docker-compose.yml:

services:
  r2r:
    mem_limit: 2g
    memswap_limit: 2g
```

## Полезные команды

```bash
# Остановить все сервисы
docker-compose down

# Остановить и удалить volumes (WARNING: удалит данные)
docker-compose down -v

# Перезапустить конкретный сервис
docker-compose restart r2r

# Обновить образы
docker-compose pull
docker-compose up -d

# Экспорт n8n workflows
docker-compose exec n8n n8n export:workflow --all --output=/workflows/backup

# Бэкап PostgreSQL
docker-compose exec postgres pg_dump -U postgres r2r > backup.sql

# Восстановление PostgreSQL
docker-compose exec -T postgres psql -U postgres r2r < backup.sql
```

## Дополнительная документация

- [R2R Documentation](https://r2r-docs.sciphi.ai)
- [n8n Documentation](https://docs.n8n.io)
- [Auth0 Documentation](https://auth0.com/docs)
- [Prisma Documentation](https://www.prisma.io/docs)
- [Supabase Documentation](https://supabase.com/docs)

## Поддержка

Для вопросов и проблем создавайте Issue в репозитории.

---

**Версия:** 2.0.0
**Дата обновления:** 2025-11-05
