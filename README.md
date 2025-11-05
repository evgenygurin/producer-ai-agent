# Producer AI Agent - Suno API Integration

AI-агент для генерации музыки с использованием Suno API v4/v5 через сервис [AIMusicAPI.ai](https://aimusicapi.ai). Реализован с применением **FSM (Finite State Machine)** для надёжного управления асинхронным процессом генерации.

## Возможности

- **FSM-based архитектура** - надёжное управление состояниями генерации музыки
- **Два режима генерации**:
  - **Auto mode** - AI генерирует музыку по текстовому описанию
  - **Custom mode** - пользовательские тексты песен и стили
- **Поддержка вокала и инструментальной музыки**
- **Выбор пола голоса** (мужской/женский)
- **Автоматическая загрузка** сгенерированных файлов
- **Отслеживание прогресса** в реальном времени
- **Retry механизм** для надёжности API запросов
- **Подробное логирование** всех операций

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

## Установка

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd producer-ai-agent
```

### 2. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 3. Настройка окружения

Скопируйте `.env.example` в `.env` и настройте:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
AIMUSIC_API_KEY=your_api_key_here
AIMUSIC_BASE_URL=https://api.aimusicapi.ai/v1
POLL_INTERVAL=5
MAX_RETRIES=60
OUTPUT_DIR=./output
AUTO_DOWNLOAD=true
LOG_LEVEL=INFO
```

## Быстрый старт

### Пример 1: Базовая генерация (Auto mode)

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
│   ├── api_client.py        # HTTP клиент для API
│   ├── music_fsm.py         # Основной FSM класс
│   ├── config.py            # Управление конфигурацией
│   └── logger.py            # Настройка логирования
├── examples/
│   ├── basic_generation.py  # Базовый пример
│   ├── custom_lyrics.py     # Пример с текстами
│   └── instrumental.py      # Инструментальная музыка
├── tests/                   # Тесты (TODO)
├── output/                  # Загруженные файлы
├── .env                     # Конфигурация (не в git)
├── .env.example             # Пример конфигурации
├── requirements.txt         # Python зависимости
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

## Полезные ссылки

- [AIMusicAPI.ai Documentation](https://docs.aimusicapi.ai/)
- [Suno API Instructions](https://docs.aimusicapi.ai/suno-api-instructions.md)
- [API Credits Guide](https://docs.aimusicapi.ai/ai-music-api-credits-usage-guide.md)

---

**Автор:** Producer AI Agent
**Версия:** 1.0.0
