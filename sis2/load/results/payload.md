| Message | protobuf, B | JSON, B | JSON / protobuf | protobuf gzip, B | JSON gzip, B |
|---|---|---|---|---|---|
| GetCounters response | 12 | 67 | 5.6x | 32 | 81 |
| BatchGetCounters request (100 ids; REST — query string) | 400 | 888 | 2.2x | 423 | 478 |
| BatchGetCounters response (100) | 1453 | 6746 | 4.6x | 1145 | 1410 |
| ViewFinished request | 168 | 177 | 1.1x | 175 | 179 |
