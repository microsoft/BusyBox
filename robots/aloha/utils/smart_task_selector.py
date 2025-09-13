from collections import defaultdict
from typing import List, Tuple

class SmartTaskSelector:
    """
    A class that generates optimal task selection sequences using Eulerian circuits
    on complete digraphs.
    """
    
    @staticmethod
    def _eulerian_circuit_complete_digraph(n: int, start: int) -> List[Tuple[int, int]]:
        """
        Return an Eulerian circuit on the complete digraph with vertices 1..n,
        starting at `start`.  Each directed edge (u, v) with u ≠ v appears exactly once.
        """
        # Build adjacency lists (store in reverse order so we can .pop() in O(1)).
        adj = defaultdict(list)
        for u in range(1, n + 1):
            adj[u] = [v for v in range(1, n + 1) if v != u][::-1]

        stack = [start]
        circuit_vertices = []

        # Iterative Hierholzer
        while stack:
            v = stack[-1]
            if adj[v]:                 # still have unused outgoing edges
                stack.append(adj[v].pop())
            else:                      # dead end – add vertex to circuit
                circuit_vertices.append(stack.pop())

        circuit_vertices.reverse()     # forward order
        # Convert vertex list to edge list
        return [(circuit_vertices[i], circuit_vertices[i + 1])
                for i in range(len(circuit_vertices) - 1)]
    
    @classmethod
    def generate_turn_sequence(self, max_number: int = 6, start_position: int = 1) -> List[Tuple[int, int]]:
        """
        Wrapper that validates input, then returns the full turn sequence.
        
        Args:
            max_number: The maximum position number (total number of positions)
            start_position: The initial position to start from
            
        Returns:
            A list of tuples representing the sequence of turns (from_position, to_position)
        """
        if not (1 <= start_position <= max_number):
            raise ValueError("start_position must be between 1 and max_number (inclusive).")

        sequence = self._eulerian_circuit_complete_digraph(max_number, start_position)

        # Sanity checks
        assert len(sequence) == max_number * (max_number - 1)
        assert len(set(sequence)) == len(sequence)          # all edges unique

        return sequence


if __name__ == "__main__":
    n = 6      # top number on the knob (hyper-parameter)
    P = 1      # starting position
    turns = SmartTaskSelector.generate_turn_sequence(n, P)
    print(turns)

    for i, (u, v) in enumerate(turns, 1):
        print(f"{i:2d}: {u} → {v}")
