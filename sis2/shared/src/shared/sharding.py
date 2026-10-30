import bisect
import hashlib
from collections import defaultdict
from collections.abc import Iterable, Sequence

VIRTUAL_NODES = 160


def _hash(key: str) -> int:
    return int.from_bytes(hashlib.blake2b(key.encode(), digest_size=8).digest())


class HashRing:
    def __init__(self, nodes: Sequence[str], virtual_nodes: int = VIRTUAL_NODES):
        if not nodes:
            raise ValueError("at least one node is required")
        if len(set(nodes)) != len(nodes):
            raise ValueError("node names must be unique")
        points = sorted(
            (_hash(f"{node}#{replica}"), index) for index, node in enumerate(nodes) for replica in range(virtual_nodes)
        )
        self._points = [point for point, _ in points]
        self._nodes = [index for _, index in points]

    def node_for(self, post_id: int) -> int:
        position = bisect.bisect(self._points, _hash(str(post_id)))
        return self._nodes[position % len(self._nodes)]

    def group(self, post_ids: Iterable[int]) -> dict[int, list[int]]:
        groups: dict[int, list[int]] = defaultdict(list)
        for post_id in post_ids:
            groups[self.node_for(post_id)].append(post_id)
        return dict(groups)
