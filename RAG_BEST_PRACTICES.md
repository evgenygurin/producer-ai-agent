# RAG Best Practices Guide

Руководство по лучшим практикам разработки RAG систем на основе **RAG Zero to Hero Guide** и опыта интеграции R2R с Producer AI Agent.

## Содержание

1. [Основы RAG](#основы-rag)
2. [Hybrid Search](#hybrid-search)
3. [GraphRAG](#graphrag)
4. [Chunking Strategies](#chunking-strategies)
5. [Reranking](#reranking)
6. [Query Enhancement](#query-enhancement)
7. [Evaluation](#evaluation)
8. [Production Considerations](#production-considerations)

---

## Основы RAG

### Что такое RAG?

**Retrieval-Augmented Generation** - это архитектурный паттерн, который улучшает LLM генерацию путем извлечения релевантной информации из внешних источников.

### Этапы RAG пайплайна

```
1. Индексирование → 2. Retrieval → 3. Augmentation → 4. Generation
```

#### 1. Индексирование
- **Chunking** документов на оптимальные фрагменты
- **Embedding** - создание векторных представлений
- **Сохранение** в векторную базу данных

#### 2. Retrieval
- **Поиск** релевантных документов
- **Hybrid search** (semantic + keyword)
- **GraphRAG** для сложных связей

#### 3. Augmentation
- **Reranking** для улучшения релевантности
- **Compression** контекста
- **Query enhancement**

#### 4. Generation
- Передача контекста в LLM
- Генерация ответа
- **Evaluation** качества

---

## Hybrid Search

### Почему гибридный поиск?

Semantic search (vector-based):
- ✅ Понимает семантику и intent
- ❌ Может пропустить точные термины

Keyword search (BM25):
- ✅ Находит точные совпадения
- ❌ Не понимает контекст

**Hybrid = Best of Both Worlds**

### Reciprocal Rank Fusion (RRF)

Оптимальный метод объединения результатов:

```python
def rrf(results1, results2, k=60):
    """
    RRF formula: score = 1 / (k + rank)
    k=60 - стандартное значение из литературы
    """
    scores = {}
    for rank, doc in enumerate(results1):
        scores[doc.id] = scores.get(doc.id, 0) + 1/(k + rank + 1)
    for rank, doc in enumerate(results2):
        scores[doc.id] = scores.get(doc.id, 0) + 1/(k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

### Настройка весов

```toml
[search]
hybrid_search = true
semantic_weight = 0.7  # 70% semantic
keyword_weight = 0.3   # 30% keyword
fusion_method = "reciprocal_rank"
rrf_k = 60
```

**Рекомендации:**
- **Общий поиск**: semantic=0.7, keyword=0.3
- **Технические документы**: semantic=0.5, keyword=0.5
- **Имена/коды**: semantic=0.3, keyword=0.7

---

## GraphRAG

### Когда использовать GraphRAG?

✅ **Используйте GraphRAG когда:**
- Нужны сложные связи между сущностями
- Требуется multi-hop reasoning
- Важна структура знаний
- Много повторяющихся сущностей

❌ **Не используйте когда:**
- Простой вопрос-ответ
- Документы без связей
- Небольшой объем данных (< 100 docs)

### Компоненты GraphRAG

1. **Entity Extraction** - извлечение сущностей
2. **Relationship Extraction** - связи между сущностями
3. **Community Detection** - группировка связанных сущностей
4. **Graph Traversal** - навигация по графу

### Конфигурация

```toml
[kg]
extraction_enabled = true
kg_search_enabled = true
extract_entities = true
extract_relationships = true
extract_communities = true
max_hops = 2  # Глубина обхода графа
community_detection_algorithm = "leiden"
```

### Пример использования

```python
from src.rag_advanced import AdvancedRAGPipeline, RAGStrategy, GraphRAGConfig

pipeline = AdvancedRAGPipeline(
    r2r_client=r2r,
    strategy=RAGStrategy.GRAPH,
    graph_config=GraphRAGConfig(
        enable_entity_extraction=True,
        max_hops=2,
        community_detection=True
    )
)

result = await pipeline.query(
    "How is Suno AI related to other music AI platforms?"
)
```

---

## Chunking Strategies

### Выбор стратегии

| Стратегия | Когда использовать | Chunk Size |
|-----------|-------------------|------------|
| **Fixed Size** | Однородные документы | 512-1024 |
| **Sentence** | Короткие тексты | 256-512 |
| **Semantic** | Длинные документы | 512-1024 |
| **Markdown** | Структурированные docs | Varies |
| **Recursive** | Сложные документы | 512-2048 |

### Оптимальные параметры

```toml
[chunking]
strategy = "recursive"
chunk_size = 512        # Оптимально для большинства LLM
chunk_overlap = 100     # 20% overlap рекомендуется
respect_document_boundaries = true
```

### Важность overlap

```
Chunk 1: [...текст...] → [overlap] ←
Chunk 2:                  → [overlap] ← [...текст...]
```

**Рекомендации:**
- Минимум 10% overlap (50 tokens для chunk_size=512)
- Оптимум 20% overlap (100 tokens)
- Максимум 30% overlap (избыточно)

### Реализация

```python
from src.rag_advanced import AdvancedChunker

chunker = AdvancedChunker()

# Semantic chunking
chunks = chunker.semantic_chunking(text, max_chunk_size=512)

# Markdown-aware chunking
chunks = chunker.markdown_chunking(text)

# Recursive with overlap
chunks = chunker.recursive_chunking(
    text,
    chunk_size=512,
    chunk_overlap=100
)
```

---

## Reranking

### Зачем нужен reranking?

Bi-encoder (initial retrieval):
- Быстрый
- Менее точный
- Используется для первичного поиска

Cross-encoder (reranking):
- Медленнее
- Более точный
- Используется для top-k результатов

**Gain:** 5-15% улучшение relevance@k

### Методы reranking

1. **Cross-Encoder Models** (рекомендуется)
2. **LLM-based** reranking
3. **Hybrid** approach

### Конфигурация

```toml
[reranking]
enabled = true
provider = "cohere"  # Или sentence-transformers
model = "rerank-english-v2.0"
top_k = 10  # Rerank только топ-10
```

### Использование

```python
pipeline = AdvancedRAGPipeline(
    r2r_client=r2r,
    reranking=RerankingMethod.CROSS_ENCODER
)
```

---

## Query Enhancement

### Техники улучшения запросов

#### 1. Query Expansion

Расширение запроса синонимами и related terms:

```
Original: "electronic music"
Expanded: "electronic music EDM dance techno house"
```

#### 2. Multi-Query Generation

Генерация множественных вариаций запроса:

```
Original: "How to produce EDM?"

Generated:
1. "What are the steps to create electronic dance music?"
2. "EDM production techniques for beginners"
3. "Tools and software for EDM music production"
```

#### 3. HyDE (Hypothetical Document Embeddings)

Генерация гипотетического ответа и поиск по нему:

```
Query → Generate hypothetical answer → Embed → Search
```

### Конфигурация

```toml
[query_enhancement]
query_expansion = true
multi_query = true
num_queries = 3
hyde_enabled = false  # Экспериментально
```

---

## Evaluation

### Ключевые метрики

#### Retrieval Metrics

- **Precision@k** - точность top-k результатов
- **Recall@k** - полнота top-k результатов
- **MRR** (Mean Reciprocal Rank) - средний обратный ранг
- **NDCG** (Normalized Discounted Cumulative Gain)

#### Generation Metrics

- **Relevance** - релевантность ответа запросу
- **Groundedness** - обоснованность источниками
- **Completeness** - полнота ответа
- **Hallucination Detection** - детекция галлюцинаций

### Конфигурация

```toml
[evaluation]
enabled = true
compute_relevance = true
compute_groundedness = true
detect_hallucinations = true
min_relevance_score = 0.5
min_groundedness_score = 0.7
```

### Реализация

```python
evaluation = await pipeline._evaluate_answer(
    query=query,
    answer=answer,
    sources=sources
)

print(f"Groundedness: {evaluation['groundedness_score']}")
print(f"Hallucination: {evaluation['hallucination_detected']}")
```

### Groundedness Check

```python
def check_groundedness(answer: str, sources: List[str]) -> float:
    """
    Проверка, насколько ответ основан на источниках
    """
    answer_words = set(answer.lower().split())
    source_words = set(' '.join(sources).lower().split())

    overlap = answer_words.intersection(source_words)
    return len(overlap) / len(answer_words) if answer_words else 0
```

**Интерпретация:**
- `> 0.7` - хорошая обоснованность
- `0.4-0.7` - средняя обоснованность
- `< 0.4` - возможна галлюцинация

---

## Production Considerations

### Производительность

#### Latency Breakdown

```
Total Latency = Embedding + Retrieval + Reranking + Generation
    ~100ms        ~50ms       ~200ms       ~1-3s
```

**Оптимизации:**

1. **Caching**
```toml
[cache]
enabled = true
provider = "redis"
ttl = 3600
cache_embeddings = true
cache_completions = true
```

2. **Batch Processing**
```toml
[embedding]
batch_size = 32  # Batch embeddings
```

3. **Async Processing**
```python
# Use async for parallel operations
results = await asyncio.gather(
    semantic_search(),
    keyword_search(),
    graph_search()
)
```

### Масштабирование

#### Horizontal Scaling

```yaml
# docker-compose.yml
r2r:
  deploy:
    replicas: 3  # Multiple R2R instances
```

#### Load Balancing

```nginx
upstream r2r_backend {
    server r2r-1:7272;
    server r2r-2:7272;
    server r2r-3:7272;
}
```

### Мониторинг

```toml
[logging]
level = "INFO"
log_queries = true
log_responses = true
track_latency = true
track_token_usage = true
```

**Key Metrics:**
- Query latency (p50, p95, p99)
- Token usage per query
- Cache hit rate
- Error rate
- Groundedness scores

### Costs

Оптимизация затрат:

1. **Использование меньших embedding моделей**
```toml
model = "text-embedding-3-small"  # Дешевле
# vs
model = "text-embedding-3-large"  # Дороже, но точнее
```

2. **Кэширование**
   - Cache hit = $0
   - Экономия до 80% на повторяющихся запросах

3. **Batch processing**
   - Снижение накладных расходов

4. **Chunk size optimization**
   - Меньше chunks = меньше embeddings
   - Баланс: качество vs стоимость

---

## Примеры из Production

### Use Case 1: Customer Support

```python
# Optimized for customer questions
pipeline = AdvancedRAGPipeline(
    strategy=RAGStrategy.HYBRID,
    reranking=RerankingMethod.CROSS_ENCODER,
    hybrid_config=HybridSearchConfig(
        semantic_weight=0.6,
        keyword_weight=0.4  # Higher for specific terms
    )
)
```

### Use Case 2: Research Assistant

```python
# Optimized for complex queries
pipeline = AdvancedRAGPipeline(
    strategy=RAGStrategy.GRAPH,
    reranking=RerankingMethod.LLM_BASED,
    graph_config=GraphRAGConfig(
        max_hops=3,  # Deep exploration
        community_detection=True
    )
)
```

### Use Case 3: Music Generation (Producer AI)

```python
# Optimized for creative prompts
pipeline = AdvancedRAGPipeline(
    strategy=RAGStrategy.HYBRID,
    reranking=RerankingMethod.HYBRID
)

# Enhance music prompt with RAG
result = await pipeline.query(
    "Create energetic workout music",
    collection_id="music-knowledge"
)

# Generate music with enhanced context
music_request = MusicGenerationRequest(
    gpt_description_prompt=f"{query}. {result['answer']}"
)
```

---

## Troubleshooting

### Проблема: Low Relevance

**Симптомы:** Нерелевантные результаты

**Решения:**
1. Проверить chunking strategy
2. Увеличить reranking top_k
3. Настроить hybrid search weights
4. Использовать query expansion

### Проблема: Hallucinations

**Симптомы:** LLM генерирует не подтвержденную информацию

**Решения:**
1. Увеличить threshold для groundedness
2. Включить hallucination detection
3. Добавить больше контекста
4. Использовать stricter prompts

### Проблема: High Latency

**Симптомы:** Медленные ответы (> 5s)

**Решения:**
1. Включить caching
2. Уменьшить reranking top_k
3. Оптимизировать chunk size
4. Использовать меньшие модели
5. Horizontal scaling

### Проблема: Low Recall

**Симптомы:** Пропускаются релевантные документы

**Решения:**
1. Увеличить retrieval limit
2. Использовать query expansion
3. Проверить embedding model
4. Оптимизировать chunking

---

## Ресурсы

### Документация
- [R2R Documentation](https://r2r-docs.sciphi.ai)
- [RAG Zero to Hero Guide](https://github.com/evgenygurin/rag-zero-to-hero-guide)
- [Producer AI Agent Docs](./DEPLOYMENT.md)

### Papers
- "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al., 2020)
- "Lost in the Middle" (Liu et al., 2023)
- "Precise Zero-Shot Dense Retrieval without Relevance Labels" (Gao et al., 2022)

### Tools
- **R2R** - Production RAG framework
- **LangChain** - RAG building blocks
- **LlamaIndex** - Data framework for LLMs
- **Chroma/Qdrant** - Vector databases

---

**Version:** 2.0.0
**Last Updated:** 2025-11-05
**Based on:** RAG Zero to Hero Guide + Production Experience
