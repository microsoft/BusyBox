from collections import defaultdict
from typing import List, Tuple, Dict, Iterable, Iterator, Optional
import random

from robots.aloha.utils.config import TASKBOX_TASKS

class TaskSelectionHandler(Iterator):
    """Iterator that yields the next task to collect a demonstration for.

    Behavior:
    1. Uniformly sample a task TYPE (e.g., PullWire, InsertWire, PushButton, MoveSlider, TurnKnob, FlipSwitch) based on
       the groups present in `TASKBOX_TASKS`.
    2. For regular task types (all except MoveSlider, TurnKnob): uniformly sample one task instance within that type.
    3. For MoveSlider and TurnKnob:
         - Use `SmartTaskSelector`'s Eulerian circuit to create a deterministic cyclic ordering of (from_pos, to_pos) moves
           that covers every directed pair exactly once, starting from a random start position (so the circuit start is random
           per session, but traversal order is fixed thereafter).
         - Convert each directed edge (u, v) into a concrete task instruction by selecting the matching task whose instruction
           text refers to moving/turning to position v.
         - We return tasks in the sequence order, cycling indefinitely.

    Yields:
        A tuple: (task_id, task_type, instruction_text)

    Notes:
        - If a generated (u, v) edge does not find an exact matching task for v (should not happen if config is consistent),
          we skip it.
        - Iterator never raises StopIteration unless all task types become empty (not expected under static config).
    """

    def __init__(self, seed: Optional[int] = None):
        self.tasks: Dict[int, Tuple[str, str]] = TASKBOX_TASKS
        self._rng = random.Random(seed)
        # Pre-group tasks by type for efficient sampling
        self._tasks_by_type: Dict[str, List[Tuple[int, str]]] = defaultdict(list)
        for tid, (t_type, instr) in self.tasks.items():
            self._tasks_by_type[t_type].append((tid, instr))

        # Identify special types (base labels in TASKBOX_TASKS)
        self._slider_type = "MoveSlider"
        self._knob_type = "TurnKnob"

        # Split slider tasks into top vs bottom variants based on instruction text
        self._top_slider_tasks: List[Tuple[int, str]] = []
        self._bottom_slider_tasks: List[Tuple[int, str]] = []
        for tid, (ttype, instr) in self.tasks.items():
            if ttype == self._slider_type:
                low = instr.lower()
                if "top" in low:
                    self._top_slider_tasks.append((tid, instr))
                elif "bottom" in low:
                    self._bottom_slider_tasks.append((tid, instr))

        # Prepare Eulerian sequences for knob, top slider, bottom slider
        self._knob_sequence: List[Tuple[int, int]] = []
        self._top_slider_sequence: List[Tuple[int, int]] = []
        self._bottom_slider_sequence: List[Tuple[int, int]] = []
        self._knob_index = 0
        self._top_slider_index = 0
        self._bottom_slider_index = 0

        # Track last emitted edges
        self._last_knob_edge: Optional[Tuple[int, int]] = None
        self._last_top_slider_edge: Optional[Tuple[int, int]] = None
        self._last_bottom_slider_edge: Optional[Tuple[int, int]] = None

        # Derive position sets
        knob_positions = self._infer_positions(self._tasks_by_type.get(self._knob_type, []))
        top_positions = self._infer_positions(self._top_slider_tasks)
        bottom_positions = self._infer_positions(self._bottom_slider_tasks)

        if knob_positions:
            max_knob = max(knob_positions)
            start_knob = self._rng.randint(1, max_knob)
            self._knob_sequence = SmartTaskSelector.generate_turn_sequence(max_knob, start_knob)
        if top_positions:
            max_top = max(top_positions)
            start_top = self._rng.randint(1, max_top)
            self._top_slider_sequence = SmartTaskSelector.generate_turn_sequence(max_top, start_top)
        if bottom_positions:
            max_bottom = max(bottom_positions)
            start_bottom = self._rng.randint(1, max_bottom)
            self._bottom_slider_sequence = SmartTaskSelector.generate_turn_sequence(max_bottom, start_bottom)

        # Build position target maps
        self._knob_tasks_by_target = self._build_position_map(self._tasks_by_type.get(self._knob_type, []))
        self._top_slider_tasks_by_target = self._build_position_map(self._top_slider_tasks)
        self._bottom_slider_tasks_by_target = self._build_position_map(self._bottom_slider_tasks)

        # Cached list of task types for sampling (only those with tasks)
        self._task_types: List[str] = list(self._tasks_by_type.keys())

    # --------- Iterator Protocol ---------
    def __iter__(self) -> "TaskSelectionHandler":
        return self

    def __next__(self):  # -> Tuple[int, str, str]
        if not self._task_types:
            raise StopIteration
        # Sample a task type uniformly
        task_type = self._rng.choice(self._task_types)
        if task_type == self._slider_type:
            # Decide top vs bottom 50/50 (fallbacks if one list empty)
            choose_top = True
            if self._top_slider_sequence and self._bottom_slider_sequence:
                choose_top = bool(self._rng.getrandbits(1))
            elif self._bottom_slider_sequence and not self._top_slider_sequence:
                choose_top = False
            # Select appropriate sequence/mapping
            if choose_top and self._top_slider_sequence:
                return self._next_slider_variant(True)
            if (not choose_top) and self._bottom_slider_sequence:
                return self._next_slider_variant(False)
            # If neither sequence exists (should not happen), fall through to uniform sampling
        if task_type == self._knob_type and self._knob_sequence:
            return self._next_knob()
        # Regular type: uniform sample among tasks for that type
        tid, instr = self._rng.choice(self._tasks_by_type[task_type])
        return (tid, task_type, instr)

    # ------------- Helpers -------------
    def _next_knob(self):
        idx = self._knob_index
        self._knob_index = (self._knob_index + 1) % len(self._knob_sequence)
        _from, to = self._knob_sequence[idx]
        self._last_knob_edge = (_from, to)
        candidates = self._knob_tasks_by_target.get(to, [])
        if not candidates:
            tid, instr = self._rng.choice(self._tasks_by_type[self._knob_type])
            return (tid, self._knob_type, instr)
        tid, instr = self._rng.choice(candidates)
        return (tid, self._knob_type, instr)

    def _next_slider_variant(self, top: bool):
        if top:
            seq = self._top_slider_sequence
            idx = self._top_slider_index
            self._top_slider_index = (self._top_slider_index + 1) % len(seq)
            _from, to = seq[idx]
            self._last_top_slider_edge = (_from, to)
            mapping = self._top_slider_tasks_by_target
            variant_label = "Top"
        else:
            seq = self._bottom_slider_sequence
            idx = self._bottom_slider_index
            self._bottom_slider_index = (self._bottom_slider_index + 1) % len(seq)
            _from, to = seq[idx]
            self._last_bottom_slider_edge = (_from, to)
            mapping = self._bottom_slider_tasks_by_target
            variant_label = "Bottom"
        candidates = mapping.get(to, [])
        if not candidates:
            # Fallback: uniform among all MoveSlider tasks
            tid, instr = self._rng.choice(self._tasks_by_type[self._slider_type])
            return (tid, f"{self._slider_type}:{variant_label}", instr)
        tid, instr = self._rng.choice(candidates)
        return (tid, f"{self._slider_type}:{variant_label}", instr)

    def last_special_edges(self) -> Dict[str, Optional[Tuple[int, int]]]:
        """Return last emitted Eulerian edges for knob, top slider, bottom slider."""
        return {
            self._knob_type: self._last_knob_edge,
            f"{self._slider_type}:Top": self._last_top_slider_edge,
            f"{self._slider_type}:Bottom": self._last_bottom_slider_edge,
        }

    def _infer_positions(self, tasks: List[Tuple[int, str]]) -> List[int]:
        positions = set()
        for _, instr in tasks:
            # Expect patterns like "position X." or "to position X." where X is int
            parts = instr.split()
            for i, p in enumerate(parts):
                if p.lower() == "position" and i + 1 < len(parts):
                    num = ''.join(ch for ch in parts[i + 1] if ch.isdigit())
                    if num:
                        positions.add(int(num))
        return sorted(positions)

    def _build_position_map(self, tasks: List[Tuple[int, str]]) -> Dict[int, List[Tuple[int, str]]]:
        mapping: Dict[int, List[Tuple[int, str]]] = defaultdict(list)
        for tid, instr in tasks:
            parts = instr.split()
            for i, p in enumerate(parts):
                if p.lower() == "position" and i + 1 < len(parts):
                    num = ''.join(ch for ch in parts[i + 1] if ch.isdigit())
                    if num:
                        mapping[int(num)].append((tid, instr))
        return mapping



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
    # ------------------------------------------------------------------
    # Demo 1: SmartTaskSelector raw Eulerian sequences
    # ------------------------------------------------------------------
    n = 6      # number of knob positions
    start_pos = 1
    knob_turns = SmartTaskSelector.generate_turn_sequence(n, start_pos)
    print("=== SmartTaskSelector Demo (Knob) ===")
    print(f"Total directed edges (should be {n*(n-1)}): {len(knob_turns)}")
    print(knob_turns, "\n")

    slider_turns = SmartTaskSelector.generate_turn_sequence(5, 1)
    print("=== SmartTaskSelector Demo (Slider) ===")
    print(slider_turns, "\n")

    # ------------------------------------------------------------------
    # Demo 2: TaskSelectionHandler iterator usage
    # ------------------------------------------------------------------
    print("=== TaskSelectionHandler Iterator Demo ===")
    tsh = TaskSelectionHandler(seed=None)
    print("Sampling 15 tasks (uniform over types; slider/knob follow Eulerian order on target positions):")
    for i in range(15):
        tid, ttype, instr = next(tsh)
        print(f"{i:02d}: [" + ttype + f"] id={tid} -> {instr}")

    # Show progression specifically for MoveSlider and TurnKnob types.
    print("\n=== Focus: Sequential Slider/Knob Progression (first 8 occurrences each) ===")
    slider_seen = []  # list of (tid, instr, edge, variant)
    knob_seen = []    # list of (tid, instr, edge)
    # Continue drawing until we collect enough examples of each special type
    attempts = 0
    slider_seen_cap = 30
    knob_seen_cap = 20
    while (len(slider_seen) < slider_seen_cap or len(knob_seen) < knob_seen_cap) and attempts < 1000:
        attempts += 1
        tid, ttype, instr = next(tsh)
        if ttype.startswith("MoveSlider") and len(slider_seen) < slider_seen_cap:
            # Determine variant key
            variant = "Top" if ":Top" in ttype else ("Bottom" if ":Bottom" in ttype else "Unknown")
            edge_map = tsh.last_special_edges()
            edge_key = f"MoveSlider:{variant}" if variant != "Unknown" else "MoveSlider:Top"
            edge = edge_map.get(edge_key)
            slider_seen.append((tid, instr, edge, variant))
        elif ttype == "TurnKnob" and len(knob_seen) < knob_seen_cap:
            edge = tsh.last_special_edges()["TurnKnob"]
            knob_seen.append((tid, instr, edge))

    print("Slider tasks (sequence of target positions inferred from instructions):")
    for i, (tid, instr, edge, variant) in enumerate(slider_seen):
        print(f"  S{i}: id={tid} variant={variant} edge={edge} -> {instr}")
    print("Knob tasks (sequence of target positions inferred from instructions):")
    for i, (tid, instr, edge) in enumerate(knob_seen):
        print(f"  K{i}: id={tid} edge={edge} -> {instr}")
    print("\nDone.")
