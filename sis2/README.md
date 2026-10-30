# SIS 2 — счётчик лайков и просмотров

Стек: Python 3.12, FastAPI, aiokafka, redis-py, SQLAlchemy (asyncpg), Alembic, nginx, Kafka (KRaft), Redis, PostgreSQL ×2.
Монорепо на `uv` workspace: `shared` + три сервиса + миграции.

## Архитектура

```mermaid
flowchart LR
    client([Клиент])

    subgraph edge[Edge]
        gw["gateway<br/>nginx :8080<br/>rate limit 50 r/s на IP"]
    end

    subgraph app[Сервисы]
        ws["write_service<br/>FastAPI"]
        rs["read_service<br/>FastAPI + L1 TTLCache"]
        agg["aggregator<br/>Kafka consumer"]
    end

    subgraph data[Хранилища]
        kafka[("Kafka<br/>topic counter-events<br/>12 партиций, key = post_id")]
        redis[("Redis<br/>кэш счётчиков + дедуп просмотров")]
        pg0[("pg-0")]
        pg1[("pg-1")]
    end

    client --> gw
    gw -- "PUT/DELETE /like<br/>POST /view_*" --> ws
    gw -- "GET /counters" --> rs

    ws -- "CounterEvent" --> kafka
    ws -- "SET NX дедуп" --> redis

    kafka --> agg
    agg -- "лайки сразу,<br/>просмотры раз в 10 с" --> pg0 & pg1
    agg -- "Lua: обновить<br/>существующий ключ" --> redis

    rs -- "HMGET / HSETNX" --> redis
    rs -- "промах кэша,<br/>liked_by_me" --> pg0 & pg1
```

Принцип — CQRS: запись принимается асинхронно (событие в Kafka, ответ `202`), чтение идёт из многоуровневого кэша.
Счётчики eventually consistent: лайки видны после ближайшего батча (~1 с), просмотры в Redis — тоже, в Postgres — после чекпоинта (~10 с).

| Компонент | Код | Роль |
|---|---|---|
| gateway | [services/gateway/nginx.conf](services/gateway/nginx.conf) | Единственная точка входа, роутинг по URL, лимит 50 r/s + burst 100 на IP (`429`) |
| write_service | [services/write_service](services/write_service) | Аутентификация, токены просмотров, дедуп, публикация событий |
| read_service | [services/read_service](services/read_service) | Отдаёт счётчики: L1 → Redis → Postgres |
| aggregator | [services/aggregator](services/aggregator) | Читает Kafka батчами, пишет в шарды Postgres и обновляет Redis |
| shared | [shared/src/shared](shared/src/shared) | События, модели, ключи Redis, шардинг, JWT, настройки |
| migrate | [infra/postgres](infra/postgres) | `alembic upgrade head` на каждом шарде |

## API

Все запросы — с `Authorization: Bearer <JWT>` (HS256, секрет `JWT_SECRET`, `sub` = id пользователя).

| Метод | Путь | Сервис | Ответ |
|---|---|---|---|
| `PUT` | `/api/v1/posts/{id}/like` | write | `202` |
| `DELETE` | `/api/v1/posts/{id}/like` | write | `202` |
| `POST` | `/api/v1/posts/{id}/view_started` | write | `200 {"view_token": "..."}` |
| `POST` | `/api/v1/posts/{id}/view_finished` | write | `202` засчитан, `200` уже засчитан, `400` токен невалиден / просмотр < 2 с |
| `GET` | `/api/v1/posts/{id}/counters` | read | `{post_id, likes, views, liked_by_me}` |
| `GET` | `/api/v1/counters?post_ids=1,2,3` | read | `{"counters": [...]}`, до 100 id |

Если Kafka недоступна, write-эндпоинты отвечают `503` — клиент повторяет запрос.

## Лайк

```mermaid
sequenceDiagram
    autonumber
    participant C as Клиент
    participant W as write_service
    participant K as Kafka
    C->>W: PUT /posts/42/like (JWT)
    W->>W: user_id из JWT
    W->>K: send_and_wait(LIKE, key=42)<br/>acks=all, idempotent, таймаут 2 с
    alt доставлено
        W-->>C: 202 Accepted
    else KafkaError / таймаут
        W-->>C: 503
    end
```

Ключ сообщения — `post_id`, поэтому все события одного поста попадают в одну партицию и обрабатываются по порядку.
Повторный лайк или анлайк без лайка безопасны: идемпотентность обеспечивает aggregator через PK `(post_id, user_id)`.

## Просмотр

Просмотр засчитывается, только если между `view_started` и `view_finished` прошло ≥ 2 с, и не чаще раза в час на пару (пост, пользователь).

```mermaid
sequenceDiagram
    autonumber
    participant C as Клиент
    participant W as write_service
    participant R as Redis
    participant K as Kafka

    C->>W: POST /posts/42/view_started
    W-->>C: view_token = JWT{pid, uid, t=now, exp=+1h}<br/>подписан VIEW_TOKEN_SECRET

    Note over C: пользователь смотрит пост ≥ 2 с

    C->>W: POST /posts/42/view_finished {view_token}
    W->>W: подпись, exp, pid/uid совпадают, now − t ≥ 2 с
    alt токен невалиден
        W-->>C: 400
    end
    W->>R: SET view:{42}:uid 1 NX EX 3600
    alt ключ уже был
        W-->>C: 200 (уже засчитан)
    else первый просмотр
        W->>K: VIEW(42, uid)
        alt Kafka упала
            W->>R: DEL view:{42}:uid
            W-->>C: 503
        else
            W-->>C: 202
        end
    end
```

Токен stateless — серверу не нужно хранить начало просмотра. Если Redis недоступен, дедуп пропускает запрос (fail-open): лучше лишний просмотр, чем ошибка.

## Aggregator

```mermaid
flowchart TD
    start([старт]) --> topic["ensure_topic:<br/>создать counter-events, 12 партиций"]
    topic --> poll["poll_batch: до 10 000 событий<br/>или окно 1 с"]
    poll --> empty{есть события?}
    empty -- нет --> timer
    empty -- да --> batch["Batch.from_records:<br/>лайки — последнее событие на (post, user)<br/>просмотры — список offset'ов на post"]
    batch --> likes["apply_likes, по шардам, одна транзакция на шард:<br/>INSERT likes ON CONFLICT DO NOTHING RETURNING<br/>DELETE likes RETURNING<br/>UPSERT post_counters.likes_count += delta RETURNING"]
    likes --> cache["update_cache: Lua-скрипт на каждый post<br/>(только если ключ уже в Redis)"]
    cache --> pending["pending_views += просмотры батча<br/>(в памяти)"]
    pending --> timer{прошло ≥ 10 с?}
    timer -- нет --> poll
    timer -- да --> cp["checkpoint:<br/>1. flush_views → UPSERT views_count += n по шардам<br/>2. consumer.commit()"]
    cp --> poll

    likes -. ошибка .-> retry["retry каждую 1 с,<br/>пока не получится"]
    cp -. ошибка .-> retry
```

Чекпоинт также выполняется при отзыве партиций (rebalance) и при остановке (SIGTERM/SIGINT).

### Почему счётчики не задваиваются

Offset в Kafka коммитится **только после** записи просмотров в Postgres. После падения aggregator перечитывает события с последнего коммита:

- **Лайки** — `likes` с PK `(post_id, user_id)`: повторный `INSERT` ничего не вставит, `RETURNING` вернёт пусто, `delta = 0`. В Redis пишется абсолютное значение `likes_count` из Postgres.
- **Просмотры в Postgres** — `pending_views` жили в памяти и потерялись вместе с процессом, поэтому повторное чтение запишет их ровно один раз.
- **Просмотры в Redis** — Lua-скрипт хранит в хэше поле `offset` и прибавляет только события с offset больше сохранённого. Все события поста лежат в одной партиции, так что offset'ы монотонны.

```lua
-- KEYS[1] = counter:{post_id}, ARGV[1] = likes или '', ARGV[2..] = offset'ы просмотров
if not EXISTS(key) then return 0 end      -- не греем кэш сами, это делает read_service
if likes ~= '' then HSET likes end
views = count(offset > key.offset)
HINCRBY views; HSET offset = max(offset)
```

## Чтение

```mermaid
flowchart TD
    req["GET /counters?post_ids=..."] --> par{{параллельно}}

    par --> l1{"L1 TTLCache<br/>in-process, 1 с, 100k"}
    l1 -- все есть --> merge
    l1 -- промахи --> r{"Redis<br/>pipeline HMGET counter:{id}"}
    r -- найдены --> putl1
    r -- промахи / Redis упал --> db["Postgres по шардам:<br/>SELECT post_counters WHERE post_id IN (...)<br/>нет строки → (0, 0)"]
    db --> fill["Redis HSETNX likes, views"]
    fill --> putl1["положить в L1"]
    putl1 --> merge

    par --> liked["Postgres по шардам:<br/>SELECT post_id FROM likes<br/>WHERE post_id IN (...) AND user_id = me"]
    liked --> merge

    merge["собрать PostCounters<br/>likes, views, liked_by_me"]
```

- L1 гасит горячие посты: при всплеске трафика на один пост Redis получает не больше запроса в секунду на инстанс.
- `HSETNX` не перезапишет значение, если aggregator успел обновить ключ между чтением из Postgres и заполнением.
- Ошибки Redis не валят запрос — сервис деградирует до Postgres.
- `liked_by_me` всегда читается из Postgres (персональные данные не кэшируются).

## Шардирование Postgres

```mermaid
flowchart LR
    id["post_id"] --> h["blake2b(post_id), 64 бита"]
    h --> ring(("hash ring<br/>160 виртуальных узлов<br/>на шард"))
    ring --> s0[("pg-0:5432/counters")]
    ring --> s1[("pg-1:5432/counters")]
```

- Обе таблицы шардируются по `post_id` — все данные поста лежат на одном шарде, транзакции не распределённые.
- Шарды задаются списком `DATABASE_URLS`; имя узла на кольце — `host:port/db`. Consistent hashing: при добавлении шарда переезжает ~1/N постов.
- `ShardedDatabase.map_shards` группирует `post_ids` по шардам и выполняет запросы к ним параллельно.
- Миграции ([env.py](infra/postgres/migrations/env.py)) последовательно применяются к каждому шарду под `pg_advisory_xact_lock`.

## Данные

```mermaid
erDiagram
    post_counters {
        bigint post_id PK
        bigint likes_count
        bigint views_count
        timestamptz updated_at
    }
    likes {
        bigint post_id PK
        bigint user_id PK
        timestamptz created_at
    }
    post_counters ||--o{ likes : "post_id (один шард)"
```

| Redis-ключ | Тип | TTL | Назначение |
|---|---|---|---|
| `counter:{post_id}` | hash `likes`, `views`, `offset` | нет, вытеснение `allkeys-lru` (512 МБ) | кэш счётчиков |
| `view:{post_id}:{user_id}` | string | 3600 с | дедуп просмотров |

Фигурные скобки — hash tag: при переходе на Redis Cluster ключи одного поста окажутся в одном слоте.
Redis работает как чистый кэш (`save ""`, `appendonly no`) — источник истины Postgres + Kafka.

Событие в Kafka ([events.py](shared/src/shared/events.py)):

```json
{"event_id": "uuid", "type": "like | unlike | view", "post_id": 42, "user_id": 7, "timestamp": 1761800000000}
```

## Запуск

```bash
cd sis2
cp .env.example .env        # POSTGRES_PASSWORD, VIEW_TOKEN_SECRET, JWT_SECRET
docker compose up --build
```

Порядок старта задан через `depends_on` + healthcheck'и:

```mermaid
flowchart LR
    pg0[(pg-0)] --> migrate
    pg1[(pg-1)] --> migrate
    migrate -- completed --> rs[read_service]
    migrate -- completed --> agg[aggregator]
    redis[(redis)] --> rs & ws[write_service] & agg
    kafka[(kafka)] --> ws & agg
    ws -- healthy --> gw[gateway :8080]
    rs -- healthy --> gw
```

Наружу открыт только `:8080`. Compose собран из файлов в [docker-ymls](docker-ymls), все Python-образы — из одного [python.Dockerfile](docker-ymls/dockerfiles/python.Dockerfile) с аргументами `PACKAGE` и `SRC`.

### Проверка руками

```bash
TOKEN=$(uv run --with pyjwt python -c "import jwt; print(jwt.encode({'sub': '7'}, 'change-me-jwt', algorithm='HS256'))")
H="Authorization: Bearer $TOKEN"

curl -i -X PUT -H "$H" localhost:8080/api/v1/posts/42/like

VT=$(curl -s -X POST -H "$H" localhost:8080/api/v1/posts/42/view_started | jq -r .view_token)
sleep 2
curl -i -X POST -H "$H" -H 'Content-Type: application/json' \
  -d "{\"view_token\": \"$VT\"}" localhost:8080/api/v1/posts/42/view_finished

sleep 1
curl -s -H "$H" 'localhost:8080/api/v1/counters?post_ids=42,43' | jq
```

## Настройки

Общие переменные (из [services.yml](docker-ymls/services.yml)): `DATABASE_URLS` (через запятую), `REDIS_URL`, `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_TOPIC`, `JWT_SECRET`.

| Сервис | Переменная | По умолчанию |
|---|---|---|
| write | `VIEW_TOKEN_SECRET` | — |
| write | `VIEW_TOKEN_TTL_SECONDS` | 3600 |
| write | `VIEW_MIN_SECONDS` | 2.0 |
| write | `PUBLISH_TIMEOUT_SECONDS` | 2.0 |
| read | `DB_POOL_SIZE` | 20 |
| read | `LOCAL_CACHE_TTL_SECONDS` / `LOCAL_CACHE_SIZE` | 1.0 / 100 000 |
| read | `MAX_BATCH_POSTS` | 100 |
| aggregator | `KAFKA_GROUP_ID` / `KAFKA_TOPIC_PARTITIONS` | aggregator / 12 |
| aggregator | `BATCH_WINDOW_SECONDS` / `BATCH_MAX_EVENTS` | 1.0 / 10 000 |
| aggregator | `FLUSH_INTERVAL_SECONDS` | 10.0 |
| aggregator | `RETRY_BACKOFF_SECONDS` | 1.0 |
| aggregator | `DB_POOL_SIZE` | 5 |
