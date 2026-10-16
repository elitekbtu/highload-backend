# Счётчики лайков и просмотров

Асинхронный прототип на Python: FastAPI, SQLAlchemy AsyncSession, asyncpg,
Kafka, PostgreSQL и Redis. Один пользователь может поставить один лайк и
добавить один просмотр к каждому посту за всё время. Повторные запросы и
повторная доставка Kafka не увеличивают счётчики.

## Запуск через Docker

Нужен Docker Compose. Все зависимости Python устанавливаются внутри образов.

```bash
cd sis1
docker compose up --build -d --wait
```

Swagger: <http://localhost:8000/docs>. API metrics: <http://localhost:8000/metrics>.
Первый запуск скачивает образы и создаёт кластер из трёх брокеров Kafka.
Для локального стека желательно выделить Docker не менее 8 ГБ памяти.

Порядок запуска: PostgreSQL → `migrate` (`alembic upgrade head`) → API и worker.
Kafka получает 64 партиции с replication factor 3 и `min.insync.replicas=2`.
`database/init.py` и создание таблиц при запуске API не используются.

Если порт 8000 занят:

```bash
API_PORT=8080 docker compose up --build -d --wait
```

## Проверка API

```bash
curl -X POST http://localhost:8000/post/ \
  -H 'Content-Type: application/json' \
  -d '{"content":"Первый пост"}'

curl -X POST http://localhost:8000/like \
  -H 'Content-Type: application/json' \
  -d '{"post_id":1,"username":"alice"}'

curl -X POST http://localhost:8000/view \
  -H 'Content-Type: application/json' \
  -d '{"post_id":1,"username":"alice"}'

curl http://localhost:8000/post/1
```

Инкременты возвращают `202` и `event_id` после подтверждения Kafka.
Счётчик появляется после обработки worker. Повтор обоих запросов должен
оставить `likes_count=1` и `views_count=1`.

`username` служит учебным идентификатором. В публичной системе он заменяется
на постоянный `user_id` из проверенной авторизации. Саморегистрации по
произвольному имени недостаточно для защиты от накрутки.

`GET /post/?after_id=0&limit=20` использует курсорную пагинацию, максимум 100 записей.
Чтение одного поста суммирует не более 16 строк `post_counters`.

## Тесты в Docker

После запуска основного стека:

```bash
docker compose --profile test build tests
docker compose --profile test run --rm --no-deps tests
```

Тесты БД используют отдельную временную схему PostgreSQL для каждого теста.
Интеграционные проверки обращаются к настоящим Kafka, worker и Redis.
Они проверяют конкурентное создание пользователя, повторы после commit,
атомарный rollback и видимость инкремента за 2 секунды после прогрева.

## Миграции

Миграции находятся в `migrations/versions`. Настройки подключения берутся из
`DATABASE_URL`. В приложении нет автоматического изменения схемы.

```bash
docker compose run --rm --no-deps migrate alembic current
docker compose run --rm --no-deps migrate alembic upgrade head
docker compose run --rm --no-deps migrate alembic check
```

После изменения моделей создайте новую ревизию Alembic, проверьте её SQL,
пересоберите образ и примените `upgrade head`. Применённые ревизии не редактируют.
Начальная миграция рассчитана на новую PostgreSQL-базу.

## Нагрузка и масштабирование

```bash
RATE=100 DURATION=30s docker compose --profile load run --rm --no-deps load
docker compose up -d --scale worker=4
```

Нагрузочный профиль направляет половину событий на один популярный пост.
Он создаёт тестовые посты и пользователей. Запускайте его на тестовом стеке.
Для целевых 20 000 RPS меняйте `RATE` и проверяйте одновременно HTTP p99,
consumer lag, задержку применения события и нагрузку PostgreSQL.
Сам ответ `202` ещё не доказывает обработку с задержкой до 2 секунд.

Метрики worker доступны внутри сети Compose на порту 8001. Порт не закреплён
на хосте, поэтому несколько worker запускаются без конфликтов.

```bash
docker compose logs --tail=100 worker
docker compose exec worker python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8001/metrics').read().decode())"
```

## Остановка

```bash
docker compose down
```

Volumes сохраняются. Удаление volumes уничтожает PostgreSQL и журнал Kafka.
Redis хранит только кэш и восстанавливается из PostgreSQL.

Материал для защиты, расчёты и границы масштабирования — в [DESIGN.md](DESIGN.md).

## Результаты локальной проверки

Проверено 16 октября 2026 года в Docker VM с 10 CPU и 7,75 GiB памяти:
один API, два worker, три Kafka broker, PostgreSQL и Redis.

| Проверка | Результат |
|---|---|
| Автоматические тесты | 29 passed |
| Alembic | Миграции применены, `alembic check` без расхождений |
| 1000 RPS на 15 секунд | 15 001 запрос инкремента, все получили 202 |
| HTTP p99 в нагрузочном профиле | 30,74 мс, включая создание 100 постов в setup |
| Ошибки HTTP и dropped iterations | 0 |
| Остановленный Redis | Чтение и запись работают через PostgreSQL и Kafka |
| Остановленный Kafka broker | Приём работает с двумя брокерами, счётчики видны за 2 с после приёма |
| Проверка агрегатов после нагрузки | Суммы полос совпадают с числом уникальных лайков и просмотров |

Профиль использует 100 заранее выделенных VU, примерно половину событий
направляет на один пост и повторяет пары пользователь–пост. Это короткая
проверка прототипа. Целевые 20 000 RPS и состояние на 50 млн постов требуют
отдельного длительного испытания на целевом оборудовании. Задержка p99
end-to-end при 20 000 RPS этой проверкой не подтверждается.
