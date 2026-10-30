from collections import defaultdict
from collections.abc import Iterable


def shard_for(post_id: int, shard_count: int) -> int:
    if shard_count < 1:
        raise ValueError("shard_count must be >= 1")
    return post_id % shard_count


def group_by_shard(post_ids: Iterable[int], shard_count: int) -> dict[int, list[int]]:
    groups: dict[int, list[int]] = defaultdict(list)
    for post_id in post_ids:
        groups[shard_for(post_id, shard_count)].append(post_id)
    return dict(groups)
