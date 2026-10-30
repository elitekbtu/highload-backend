| Message | protobuf, B | JSON, B | JSON / protobuf |
|---|---|---|---|
| GetCounters response | 12 | 67 | 5.6x |
| BatchGetCounters request (100 ids) | 400 | 888 | 2.2x |
| BatchGetCounters response (100) | 1453 | 6746 | 4.6x |
| ViewFinished request | 168 | 177 | 1.1x |
