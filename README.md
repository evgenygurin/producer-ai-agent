# Producer AI Agent - Интегрированная AI платформа

**Комплексная AI-платформа** для генерации музыки, RAG (Retrieval-Augmented Generation) и автоматизации workflow. Объединяет:
- **Suno API** (v4/v5) для генерации музыки через [AIMusicAPI.ai](https://aimusicapi.ai)
- **R2R** - Production-ready RAG система для семантического поиска и генерации
- **n8n** - Workflow automation для оркестрации AI-процессов
- **Auth0** - Аутентификация и управление доступом
- **Supabase/Prisma** - База данных и управление метаданными

## Возможности

### 🎵 Генерация музыки
- **FSM-based архитектура** - надёжное управление состояниями генерации музыки
- **Два режима генерации**:
  - **Auto mode** - AI генерирует музыку по текстовому описанию
  - **Custom mode** - пользовательские тексты песен и стили
- **Поддержка вокала и инструментальной музыки**
- **Выбор пола голоса** (мужской/женский)
- **Автоматическая загрузка** сгенерированных файлов

### 🔍 RAG (R2R)
- **Мультимодальная обработка** документов (PDF, TXT, JSON, PNG, MP3)
- **Гибридный поиск** (семантический + keyword search)
- **Knowledge Graphs** с автоматическим извлечением сущностей
- **Векторная база данных** на PostgreSQL/pgvector
- **Коллекции** для организации документов

### 🔄 Workflow Automation (n8n)
- **Визуальный редактор** workflow
- **Готовые шаблоны** для RAG + генерация музыки
- **Webhook интеграции** для внешних систем
- **Автоматическое логирование** в PostgreSQL
- **Расширяемость** через custom nodes

### 🔐 Аутентификация (Auth0)
- **JWT-based authentication**
- **Role-based access control (RBAC)**
- **OAuth 2.0 / OpenID Connect**
- **Multi-tenant support**

### 📊 База данных
- **PostgreSQL** с pgvector для векторного поиска
- **Prisma ORM** для типобезопасного доступа
- **Supabase** для продакшн развертывания
- **Автоматические миграции**

## Архитектура FSM

Конечный автомат управляет следующими состояниями:

```
IDLE → PREPARING → CREATING → PENDING → POLLING → COMPLETED → DOWNLOADING → IDLE
                        ↓           ↓         ↓          ↓
                      FAILED    FAILED    FAILED     FAILED
                        ↓           ↓         ↓          ↓
                      IDLE        IDLE      IDLE       IDLE
```

### Состояния:

- **IDLE** - начальное состояние, готов к работе
- **PREPARING** - валидация и подготовка запроса
- **CREATING** - отправка запроса на создание задачи
- **PENDING** - ожидание начала обработки задачи
- **POLLING** - активная проверка статуса задачи
- **COMPLETED** - задача успешно завершена
- **DOWNLOADING** - загрузка сгенерированных файлов
- **FAILED** - ошибка выполнения
- **CANCELLED** - отмена пользователем

## Быстрая установка с Docker

### Вариант 1: Используя Makefile (рекомендуется)

```bash
# Клонировать репозиторий
git clone https://github.com/evgenygurin/producer-ai-agent.git
cd producer-ai-agent

# Настроить окружение
make setup

# Отредактировать .env (добавьте ваши API keys)
nano .env

# Запустить все сервисы
make start

# Проверить статус
make health
```

### Вариант 2: Используя Docker Compose напрямую

```bash
# Клонировать и настроить
git clone https://github.com/evgenygurin/producer-ai-agent.git
cd producer-ai-agent
cp .env.example .env

# Отредактировать .env
nano .env

# Запустить
docker-compose up -d

# Проверить логи
docker-compose logs -f
```

### Минимальная настройка .env

```env
# Обязательные переменные
OPENAI_API_KEY=sk-your-openai-key-here
POSTGRES_PASSWORD=your_secure_password

# Опциональные (для полной функциональности)
AIMUSIC_API_KEY=your_aimusic_key
AUTH0_ENABLED=false  # Включите если нужна аутентификация
```

### Доступ к сервисам

После запуска будут доступны:
- **API Gateway**: http://localhost:8000
- **n8n**: http://localhost:5678 (admin/your_password)
- **R2R**: http://localhost:7272
- **PostgreSQL**: localhost:5432

Полное руководство по развертыванию: [DEPLOYMENT.md](DEPLOYMENT.md)

## Быстрый старт

### Использование через API

#### 1. Базовая генерация музыки

```bash
curl -X POST http://localhost:8000/api/v1/music/generate \
  -H "Content-Type: application/json" \
  -d '{
    "custom_mode": false,
    "gpt_description_prompt": "Upbeat electronic dance music",
    "make_instrumental": false,
    "voice_gender": "female"
  }'
```

#### 2. RAG запрос

```bash
# Загрузить документы
curl -X POST http://localhost:8000/api/v1/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [{
      "content": "Electronic dance music with heavy bass and energetic beats",
      "title": "EDM Reference"
    }]
  }'

# Выполнить RAG запрос
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the best style for energetic music?",
    "limit": 5
  }'
```

#### 3. RAG-powered генерация музыки через n8n

```bash
curl -X POST http://localhost:5678/webhook/generate-music \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create energetic dance music",
    "style": "electronic dance",
    "instrumental": false
  }'
```

### Использование через Python SDK

#### Пример 1: Базовая генерация (Auto mode)

```python
from src.config import load_config
from src.logger import setup_logging
from src.api_client import AIMusicAPIClient
from src.music_fsm import MusicGenerationFSM
from src.models import MusicGenerationRequest

# Загрузка конфигурации
config = load_config()
setup_logging(log_level=config.log_level)

# Создание клиента
client = AIMusicAPIClient(api_key=config.api_key)

# Создание FSM
fsm = MusicGenerationFSM(
    api_client=client,
    poll_interval=config.poll_interval,
    max_retries=config.max_retries
)

# Запрос на генерацию
request = MusicGenerationRequest(
    custom_mode=False,
    gpt_description_prompt="A cheerful acoustic guitar melody with uplifting vocals",
    make_instrumental=False,
    mv="chirp-v4",
    voice_gender="female"
)

# Генерация музыки
result = fsm.generate_music(
    request=request,
    auto_download=True,
    output_dir="./output"
)

print(f"Generated {len(result.clips)} clips")
for clip in result.clips:
    print(f"- {clip.title}: {clip.audio_url}")
```

### Пример 2: Пользовательские тексты (Custom mode)

```python
request = MusicGenerationRequest(
    custom_mode=True,
    lyrics="""[Verse 1]
Walking down the street tonight
City lights are shining bright

[Chorus]
Let the music play
Dancing through the day""",
    style="pop rock, upbeat, energetic",
    title="City Lights",
    make_instrumental=False,
    mv="chirp-v4",
    voice_gender="male"
)

result = fsm.generate_music(request=request, auto_download=True)
```

### Пример 3: Инструментальная музыка

```python
request = MusicGenerationRequest(
    custom_mode=False,
    gpt_description_prompt="Epic cinematic orchestral piece with dramatic percussion",
    make_instrumental=True,  # Без вокала
    mv="chirp-v4"
)

result = fsm.generate_music(request=request)
```

## Примеры использования

В папке `examples/` находятся готовые примеры:

```bash
# Базовая генерация
python examples/basic_generation.py

# Пользовательские тексты
python examples/custom_lyrics.py

# Инструментальная музыка
python examples/instrumental.py
```

## Структура проекта

```
producer-ai-agent/
├── src/
│   ├── __init__.py          # Инициализация пакета
│   ├── states.py            # Определение состояний FSM
│   ├── models.py            # Pydantic модели данных
│   ├── api_client.py        # HTTP клиент для Music API
│   ├── music_fsm.py         # FSM для генерации музыки
│   ├── r2r_client.py        # Клиент для R2R RAG системы
│   ├── auth0_middleware.py  # Auth0 аутентификация
│   ├── api_server.py        # FastAPI сервер
│   ├── config.py            # Управление конфигурацией
│   └── logger.py            # Настройка логирования
├── examples/
│   ├── basic_generation.py  # Базовый пример
│   ├── custom_lyrics.py     # Пример с текстами
│   └── instrumental.py      # Инструментальная музыка
├── n8n-workflows/           # Готовые n8n workflows
│   ├── rag-music-generation.json
│   └── document-ingestion.json
├── prisma/
│   └── schema.prisma        # Prisma схема БД
├── r2r-config/
│   └── r2r.toml            # Конфигурация R2R
├── init-scripts/
│   └── 01-init-databases.sql # SQL инициализация
├── tests/                   # Тесты
├── output/                  # Загруженные файлы
├── docker-compose.yml       # Docker Compose конфигурация
├── Dockerfile.api           # Dockerfile для API Gateway
├── Makefile                 # Makefile для удобства
├── .env.example             # Пример конфигурации
├── requirements.txt         # Python зависимости (базовые)
├── requirements.api.txt     # Python зависимости (API)
├── DEPLOYMENT.md           # Полное руководство по развертыванию
└── README.md               # Документация
```

## API Reference

### MusicGenerationRequest

Модель запроса на генерацию музыки:

```python
class MusicGenerationRequest(BaseModel):
    custom_mode: bool = False
    lyrics: Optional[str] = None              # Для custom_mode=True
    style: Optional[str] = None               # Для custom_mode=True
    title: Optional[str] = None
    gpt_description_prompt: Optional[str] = None  # Для custom_mode=False
    make_instrumental: bool = False
    mv: str = "chirp-v4"                      # Версия модели
    voice_gender: Optional[Literal["male", "female"]] = None
    auto_lyrics: bool = False
```

### MusicGenerationFSM

Основной класс FSM:

#### Методы:

- **`generate_music(request, auto_download, output_dir)`** - генерация музыки
- **`get_current_state()`** - текущее состояние FSM
- **`get_progress()`** - информация о прогрессе
- **`cancel_generation()`** - отмена генерации
- **`reset_fsm()`** - сброс в начальное состояние

#### Callbacks:

```python
def on_state_change(state: str):
    print(f"Current state: {state}")

fsm = MusicGenerationFSM(
    api_client=client,
    on_state_change=on_state_change
)
```

### AIMusicAPIClient

HTTP клиент для работы с API:

#### Методы:

- **`create_music(request)`** - создать задачу генерации
- **`get_task_status(task_id)`** - проверить статус задачи
- **`get_music_result(task_id)`** - получить результат
- **`check_credits()`** - проверить баланс кредитов
- **`download_audio(url, output_path)`** - скачать аудио файл

## Конфигурация

### Переменные окружения (.env)

| Параметр | Описание | По умолчанию |
|----------|----------|--------------|
| `AIMUSIC_API_KEY` | API ключ (обязательно) | - |
| `AIMUSIC_BASE_URL` | Base URL API | `https://api.aimusicapi.ai/v1` |
| `POLL_INTERVAL` | Интервал опроса (сек) | `5` |
| `MAX_RETRIES` | Макс. попыток опроса | `60` |
| `OUTPUT_DIR` | Папка для файлов | `./output` |
| `AUTO_DOWNLOAD` | Авто-загрузка файлов | `true` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `LOG_FILE` | Путь к лог-файлу | `None` |

### Модели Suno

Доступные версии моделей (параметр `mv`):

- `chirp-v4` - последняя версия v4
- `chirp-v3.5` - предыдущая стабильная
- `chirp-v3` - базовая версия

## Обработка ошибок

FSM автоматически обрабатывает ошибки и переходит в состояние `FAILED`:

```python
try:
    result = fsm.generate_music(request)
except AIMusicAPIError as e:
    print(f"API Error: {e}")
    print(f"FSM State: {fsm.get_current_state()}")
    print(f"Error details: {fsm.error_message}")
```

### Retry механизм

API клиент автоматически повторяет неудачные запросы:
- 3 попытки для каждого запроса
- Экспоненциальная задержка (2s, 4s, 8s)

## Мониторинг прогресса

```python
# Callback для отслеживания состояний
def on_state_change(state):
    progress = fsm.get_progress()
    print(f"State: {state}")
    print(f"Poll count: {progress['poll_count']}/{progress['max_retries']}")
    if 'progress_percentage' in progress:
        print(f"Progress: {progress['progress_percentage']}%")
    if 'elapsed_time' in progress:
        print(f"Elapsed: {progress['elapsed_time']:.2f}s")

fsm = MusicGenerationFSM(
    api_client=client,
    on_state_change=on_state_change
)
```

## Логирование

Логи включают:
- Переходы между состояниями FSM
- HTTP запросы и ответы API
- Ошибки и исключения
- Прогресс генерации

Настройка уровня логирования:

```python
from src.logger import setup_logging

setup_logging(
    log_level="DEBUG",      # DEBUG, INFO, WARNING, ERROR
    log_file="./logs/app.log"
)
```

## Лицензия

MIT License

## Поддержка

Для вопросов и проблем создавайте Issue в репозитории.

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

## API Endpoints

### Music Generation
- `POST /api/v1/music/generate` - Генерация музыки
- `GET /api/v1/music/status` - Статус генерации
- `GET /api/v1/music/credits` - Проверка кредитов

### RAG (R2R)
- `POST /api/v1/rag/ingest` - Загрузка документов
- `POST /api/v1/rag/ingest-files` - Загрузка файлов
- `POST /api/v1/rag/search` - Поиск документов
- `POST /api/v1/rag/query` - RAG запрос с генерацией
- `POST /api/v1/rag/collections` - Создание коллекции
- `GET /api/v1/rag/collections` - Список коллекций

### System
- `GET /health` - Health check всех сервисов
- `GET /api/v1/user/profile` - Профиль пользователя (Auth0)

## n8n Workflows

В проекте включены готовые workflows:

1. **RAG-Powered Music Generation** (`rag-music-generation.json`)
   - Принимает текстовый промпт
   - Выполняет RAG поиск для улучшения промпта
   - Генерирует музыку с учетом контекста
   - Логирует результаты в PostgreSQL

2. **Document Ingestion** (`document-ingestion.json`)
   - Валидирует документы
   - Загружает в R2R
   - Организует по коллекциям
   - Отслеживает в базе данных

Импортируйте workflows через n8n UI: http://localhost:5678

## Примеры использования

### Пример 1: RAG + Генерация музыки

```python
import asyncio
from src.r2r_client import R2RClient, Document
from src.music_fsm import MusicGenerationFSM
from src.api_client import AIMusicAPIClient
from src.models import MusicGenerationRequest

async def rag_powered_music():
    # Инициализация клиентов
    r2r = R2RClient(base_url="http://localhost:7272")
    music_client = AIMusicAPIClient(api_key="your_key")
    fsm = MusicGenerationFSM(api_client=music_client)

    # Загрузка контекста в R2R
    await r2r.ingest_documents([
        Document(
            content="Electronic dance music with heavy bass",
            title="EDM Reference",
            metadata={"genre": "edm"}
        )
    ], collection_id="music-refs")

    # RAG запрос для улучшения промпта
    rag_response = await r2r.rag(
        query="Create energetic dance music",
        collection_id="music-refs"
    )

    # Генерация музыки с улучшенным промптом
    request = MusicGenerationRequest(
        custom_mode=False,
        gpt_description_prompt=rag_response.answer,
        make_instrumental=False,
        voice_gender="female"
    )

    result = fsm.generate_music(request, auto_download=True)
    print(f"Generated: {result.clips[0].audio_url}")

asyncio.run(rag_powered_music())
```

### Пример 2: Работа с коллекциями

```python
async def manage_collections():
    r2r = R2RClient(base_url="http://localhost:7272")

    # Создать коллекцию
    collection = await r2r.create_collection(
        name="music-library",
        description="Music references and styles"
    )

    # Список коллекций
    collections = await r2r.list_collections()
    for col in collections:
        print(f"Collection: {col['name']}")
```

## Мониторинг и отладка

```bash
# Просмотр логов всех сервисов
make logs

# Просмотр логов конкретного сервиса
make logs-api
make logs-r2r
make logs-n8n

# Проверка здоровья сервисов
make health

# Подключение к PostgreSQL
make db-shell

# Бэкап базы данных
make backup
```

## Продакшн развертывание

Для продакшн развертывания см. [DEPLOYMENT.md](DEPLOYMENT.md), который включает:
- Настройку Auth0
- Интеграцию с Supabase
- SSL/TLS конфигурацию
- Безопасность и best practices
- Мониторинг и логирование

## Тестирование

```bash
# Запустить интеграционные тесты
make test

# Или вручную
curl http://localhost:8000/health
```

## Полезные ссылки

- [R2R Documentation](https://r2r-docs.sciphi.ai)
- [n8n Documentation](https://docs.n8n.io)
- [Auth0 Documentation](https://auth0.com/docs)
- [Prisma Documentation](https://www.prisma.io/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [AIMusicAPI.ai Documentation](https://docs.aimusicapi.ai/)

## Contributing

Pull requests are welcome! For major changes, please open an issue first.

## Лицензия

MIT License

## Поддержка

Для вопросов и проблем создавайте Issue в репозитории.

---

**Автор:** Producer AI Agent
**Версия:** 2.0.0 (R2R + n8n Integration)
**Дата:** 2025-11-05
