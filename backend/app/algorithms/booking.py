from collections.abc import Sequence
from typing import NamedTuple


class BundleCount(NamedTuple):
    size: int
    count: int


def min_bundles(sizes: Sequence[int], group_size: int) -> list[BundleCount] | None:
    """Fewest bundles whose seats add up to exactly `group_size`.

    Classic minimum coin change, solved bottom-up:

        best[t] = fewest bundles summing to exactly t seats (infinity if impossible)
        best[0] = 0
        best[t] = 1 + min(best[t - s]) over every bundle size s <= t

    `last[t]` remembers which bundle size gave the best answer for t, so we can
    walk back from `group_size` to 0 and count how many of each size were used.

    O(group_size * len(sizes)) time and O(group_size) memory: at most
    10,000 * 10 = 100k steps for this assignment's limits.

    Returns None when no exact combination exists, otherwise a list of
    BundleCount sorted by size descending (largest bundles first).
    """
    if group_size <= 0:
        return None

    unreachable = group_size + 1  # more bundles than seats is impossible (min size is 1)
    best = [unreachable] * (group_size + 1)
    last = [0] * (group_size + 1)
    best[0] = 0

    for total in range(1, group_size + 1):
        for size in sizes:
            if size <= total and best[total - size] + 1 < best[total]:
                best[total] = best[total - size] + 1
                last[total] = size

    if best[group_size] == unreachable:
        return None

    counts: dict[int, int] = {}
    remaining = group_size
    while remaining > 0:
        size = last[remaining]
        counts[size] = counts.get(size, 0) + 1
        remaining -= size

    return [BundleCount(size, counts[size]) for size in sorted(counts, reverse=True)]
