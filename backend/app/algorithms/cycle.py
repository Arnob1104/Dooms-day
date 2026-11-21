from collections.abc import Iterable, Mapping, Sequence


def creates_cycle(
    movie_id: int,
    new_prerequisites: Iterable[int],
    graph: Mapping[int, Sequence[int]],
) -> bool:
    """Would giving `movie_id` these prerequisites create a circular dependency?

    `graph` maps movie id -> its current prerequisite ids.

    Adding the edges movie_id -> p creates a cycle exactly when `movie_id` can be
    reached by walking prerequisites starting from one of the new prerequisites
    (or when `movie_id` is one of them, i.e. a direct self-dependency).

    We never expand `movie_id` itself: reaching it already answers the question,
    so its old prerequisites (which are being replaced) are irrelevant.

    Iterative DFS, O(V + E), safe for very deep chains (no recursion limit).
    """
    seen: set[int] = set()
    stack = list(new_prerequisites)
    while stack:
        node = stack.pop()
        if node == movie_id:
            return True
        if node in seen:
            continue
        seen.add(node)
        stack.extend(graph.get(node, ()))
    return False
