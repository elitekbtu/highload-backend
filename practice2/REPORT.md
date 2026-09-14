# Practice 2 — Load Testing HTTP/1.1 vs HTTP/2 vs HTTP/3

Стек методички: Java 21 / Spring Boot.
Этот отчёт: Python / FastAPI / Hypercorn / Caddy / k6 / curl.
Измеряем те же механизмы: handshake RTT, multiplexing, HPACK, HOL, QUIC.

## Стенд

- железо:
- ОС:
- Python / Hypercorn / Caddy / k6 / curl / h2load (версии):
- arrival rate: 500 RPS, duration: 60s, payload: `/api/quote/1` (~90 B)
- лимиты Hypercorn: `workers=1`, `backlog=100`, `keep_alive_timeout=5`
- все три протокола через Caddy `:9443` (`:9444` только HTTP/1.1)
- HTTP/3 нагрузка: k6 / h2load / только curl (вычеркнуть лишнее)

Переговоренные версии (curl `-w '%{http_version}'`): 1.1 / 2 / 3.

## Таблица

| protocol | connection | p50 | p95 | p99 | RPS | mechanism |
|---|---|---|---|---|---|---|
| HTTP/1.1 | reused |  |  |  |  | baseline |
| HTTP/1.1 | new per request |  |  |  |  | TCP + TLS = … ms |
| HTTP/2 | reused |  |  |  |  | multiplexing, HPACK |
| HTTP/3 | reused |  |  |  |  | QUIC handshake, per-stream loss |
| HTTP/1.1 | netem 100ms |  |  |  |  | RTT dominates handshake |
| HTTP/2 | netem 100ms / 1% |  |  |  |  | HOL on one TCP conn — смотри p99 |
| HTTP/3 | netem 100ms / 1% |  |  |  |  | независимые стримы QUIC |

Handshake cost: ___ ms.
Источник: k6 `http_req_connecting` + `http_req_tls_handshaking` на cold
(warm ≈ 0) **или** `cold p50 − warm p50` в `client_harness.py`.

`dropped_iterations` на валидных прогонах: 0.

## Три объяснения

1. Handshake. На reused HTTP/1.1 p50 = ___ ms, на new-per-request p50 = ___ ms.
   Разница ___ ms совпадает с k6 `http_req_connecting` + `http_req_tls_handshaking`
   на cold. Это round-trip TCP и TLS 1.3, не работа хендлера: `http_req_waiting`
   почти не сдвинулся. На netem 100 ms этот зазор становится главным членом.

2. HTTP/2 выигрывает на concurrency, не на одном запросе. Sequential harness
   дал близкие p50 у 1.1 и 2 — один стрим, нечему мультиплексировать. На 500 RPS
   reused HTTP/2 держит ___ RPS / p99 ___ ms против HTTP/1.1 ___ / ___: один
   сокет, много стримов, HPACK на повторяющихся заголовках маленького JSON.
   Не «новее быстрее».

3. Loss разделяет h2 и h3. На чистом линке h2 и h3 близки (p50 ___ vs ___).
   С delay+1% HTTP/2 p99 вырос до ___ (потерянный пакет стопорит все стримы на
   одном TCP — head-of-line). HTTP/3 p99 ___ — recovery по стриму в QUIC.
   Если h3 не лучше: ограничение стенда (буфер UDP, нет QUIC в h2load, только curl).

## AI

Каркас репозитория сгенерирован в Cursor. Числа и финальные формулировки —
с ваших прогонов.
