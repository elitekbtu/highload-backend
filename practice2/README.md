# Practice 2 — HTTP/1.1 vs HTTP/2 vs HTTP/3

Стек: Python, FastAPI, Hypercorn, Caddy, k6, curl.
В методичке указаны Java 21 / Spring Boot; здесь те же измерения и механизмы.

Один сервис на `:8443`. Caddy на `:9443` отдаёт h1/h2/h3, на `:9444` — только HTTP/1.1.
Папки `servers/http1`, `http2`, `http3` не используются.

## Полный порядок запуска (Docker)

Нужен только Docker Desktop. Терминал 1 не закрывайте, пока идут прогоны.
Все `docker compose exec` — из каталога `practice2`, **второй** терминал.
Каждый k6-прогон ~60 с. Если `dropped_iterations != 0` — строку выбросить и повторить.

### 0. Стенд

```bash
cd practice2
docker compose up --build
```

Ждите в логах Caddy, что слушает `:9443` / `:9444`. Сертификат создастся сам.

### 1. Доказать протокол (без этого цифры врут)

```bash
docker compose exec lab curl -k --http1.1 -so /dev/null -w '%{http_version}\n' https://localhost:9444/api/quote/1
docker compose exec lab curl -k --http2    -so /dev/null -w '%{http_version}\n' https://localhost:9443/api/quote/1
docker compose exec lab curl -k --http3    -so /dev/null -w '%{http_version}\n' https://localhost:9443/api/quote/1
```

Ожидаем `1.1` / `2` / `3`. Если `--http3` нет у curl — напишите это в отчёте.

```bash
docker compose exec lab curl -k --http2 -so /dev/null -w \
  'tcp=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer}\n' \
  https://localhost:9443/api/quote/1
```

### 2. Handshake в Python (один запрос за раз)

```bash
docker compose exec lab python client_harness.py
docker compose exec lab python client_harness.py --cold
docker compose exec lab python client_harness.py --http1 --url https://localhost:9444/api/quote/1
```

В `REPORT.md`: handshake ≈ `(cold p50 − warm p50)` в миллисекундах (`us / 1000`).
Warm HTTP/1.1 и HTTP/2 должны быть близки — это нормально.

### 3. Нагрузка k6 — чистая сеть

Смотрите `http_req_duration` p50/p95/p99, `http_reqs` (это RPS),
`dropped_iterations`, на cold ещё `http_req_connecting` и `http_req_tls_handshaking`.

```bash
docker compose exec lab k6 run -e URL=https://localhost:9444 load.js
```

Строка таблицы: HTTP/1.1 reused.

```bash
docker compose exec lab k6 run -e URL=https://localhost:9443 load.js
```

Строка: HTTP/2 reused.

```bash
docker compose exec lab k6 run -e URL=https://localhost:9443 -e COLD=1 load.js
```

Строка: HTTP/1.1 (или HTTP/2) new per request.
Handshake из k6: p50(`connecting` + `tls_handshaking`) на этом прогоне.

HTTP/3: k6 его не умеет. Если `curl --http3` сработал в шаге 1:

```bash
docker compose exec lab sh -c 'for i in 1 2 3 4 5; do
  curl -k --http3 -so /dev/null -w "%{http_version} %{time_total}\n" \
    https://localhost:9443/api/quote/1
done'
```

Строка HTTP/3 reused — curl, не 500 RPS. В отчёте так и напишите.

### 4. Плохая сеть — только delay

```bash
docker compose exec lab ./netem.sh delay
docker compose exec lab ping -c 3 127.0.0.1
```

ping ~200 ms. Затем те же три протокола:

```bash
docker compose exec lab k6 run -e URL=https://localhost:9444 load.js
docker compose exec lab k6 run -e URL=https://localhost:9443 load.js
docker compose exec lab sh -c 'for i in 1 2 3 4 5; do
  curl -k --http3 -so /dev/null -w "%{http_version} %{time_total}\n" \
    https://localhost:9443/api/quote/1
done'
docker compose exec lab ./netem.sh del
```

Строка: HTTP/1.1 netem 100ms (и при желании h2/h3 delay-only).

### 5. Плохая сеть — delay + 1% loss (отдельный прогон)

```bash
docker compose exec lab ./netem.sh loss
docker compose exec lab k6 run -e URL=https://localhost:9444 load.js
docker compose exec lab k6 run -e URL=https://localhost:9443 load.js
docker compose exec lab sh -c 'for i in 1 2 3 4 5; do
  curl -k --http3 -so /dev/null -w "%{http_version} %{time_total}\n" \
    https://localhost:9443/api/quote/1
done'
docker compose exec lab ./netem.sh del
```

Строки: каждый протокол / netem 100ms / 1%. Смотрите **p99**, не среднее.

### 6. Отчёт и стоп

Впишите числа в `REPORT.md`, допишите три объяснения своими цифрами.
Версии для шапки:

```bash
docker compose exec lab python --version
docker compose exec lab caddy version
docker compose exec lab k6 version
docker compose exec lab curl -V
```

```bash
docker compose down
```

## Зависимости (если без Docker)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Нужны также: [Caddy](https://caddyserver.com/docs/install), [k6](https://k6.io/), curl (лучше с HTTP3: `curl -V`).

## Сертификат

```bash
python scripts/key_generate.py
```

Пишет `certs/cert.pem`, `certs/key.pem`, `certs/keystore.p12` (EC, SAN localhost / 127.0.0.1).

## Запуск

```bash
hypercorn servers.app:app --config hypercorn.toml
caddy run --config Caddyfile --adapter caddyfile
```

## Smoke: какая версия на проводе

```bash
curl -k --http1.1 -so /dev/null -w '%{http_version}\n' https://localhost:9444/api/quote/1
curl -k --http2    -so /dev/null -w '%{http_version}\n' https://localhost:9443/api/quote/1
curl -k --http3    -so /dev/null -w '%{http_version}\n' https://localhost:9443/api/quote/1
# ожидаем: 1.1 / 2 / 3

curl -k --http2 -so /dev/null -w \
  'tcp=%{time_connect} tls=%{time_appconnect} ttfb=%{time_starttransfer}\n' \
  https://localhost:9443/api/quote/1
```

## Java-аналог: перцентили в Python

```bash
python client_harness.py
python client_harness.py --cold
python client_harness.py --http1 --url https://localhost:9444/api/quote/1
```

`httpx` не говорит HTTP/3. Handshake ≈ `cold p50 − warm p50`.

## Нагрузка

```bash
k6 run -e URL=https://localhost:9443 load.js          # HTTP/2
k6 run -e URL=https://localhost:9444 load.js          # HTTP/1.1
k6 run -e URL=https://localhost:9443 -e COLD=1 load.js
```

Прогон невалиден, если `dropped_iterations != 0`.

HTTP/3 (если `h2load --version` показывает QUIC):

```bash
h2load -n 30000 -c 50 -m 20 https://localhost:9443/api/quote/1
```

Иначе сравнение фаз:

```bash
for i in 1 2 3 4 5; do
  curl -k --http3 -so /dev/null -w '%{http_version} %{time_total}\n' \
    https://localhost:9443/api/quote/1
done
```

## netem (только Linux)

На macOS сервис и `tc` — в контейнере:

```bash
docker run --rm -it --cap-add=NET_ADMIN --name lab \
  -p 9443:9443/tcp -p 9443:9443/udp -p 9444:9444 \
  -v "$PWD":/work -w /work python:3.12-bookworm bash
```

Внутри:

```bash
./netem.sh delay   # 100ms ± 10ms
./netem.sh loss    # delay + 1% loss — отдельный прогон
./netem.sh del
```

## Лимиты Hypercorn (в отчёт)

`workers = 1`, `backlog = 100`, `keep_alive_timeout = 5`

## AI

Каркас и команды подготовлены в Cursor (канвас + генерация файлов).
Цифры в `REPORT.md` нужно снять своими прогонами.
