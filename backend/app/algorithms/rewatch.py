from collections.abc import Iterator, Mapping, Sequence


class CycleError(Exception):
    """Raised if the prerequisite data contains a cycle (should never be stored)."""


def rewatch_order(target: int, graph: Mapping[int, Sequence[int]]) -> list[int]:
    """Every transitive prerequisite of `target`, each exactly once, ordered so a
    movie always comes after all of its own prerequisites. `target` is excluded.

    This is a topological sort done as an iterative depth-first search with
    post-order emission: a movie is appended only after all its prerequisites
    have been appended. A `visited` set guarantees each movie appears once even
    when it is reachable through several paths (diamonds).

    Colours: absent = unvisited, 1 = on the current DFS path, 2 = finished.
    Meeting a colour-1 node means a back edge, i.e. a cycle.

    O(V + E) time, no recursion (so long franchise chains cannot overflow the stack).
    Prerequisites are visited in ascending id order so the output is deterministic.
    """
    order: list[int] = []
    colour: dict[int, int] = {target: 1}
    stack: list[tuple[int, Iterator[int]]] = [(target, iter(sorted(graph.get(target, ()))))]

    while stack:
        node, children = stack[-1]
        for child in children:
            state = colour.get(child)
            if state is None:
                colour[child] = 1
                stack.append((child, iter(sorted(graph.get(child, ())))))
                break  # go deeper; resume this node's iterator later
            if state == 1:
                raise CycleError(f"cycle detected through movie {child}")
            # state == 2: already emitted, skip
        else:
            stack.pop()
            colour[node] = 2
            if node != target:
                order.append(node)

    return order
