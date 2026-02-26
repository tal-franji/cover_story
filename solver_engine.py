from typing import List, Tuple, Dict, Optional, Set

class Solver:
    def __init__(self, grid: List[List[int]], pieces: List[List[Tuple[int, int]]]):
        self.grid = grid
        self.rows = len(grid)
        self.cols = len(grid[0])
        # Sort pieces by size descending for better pruning
        self.pieces = sorted(pieces, key=len, reverse=True)
        self.num_pieces = len(pieces)

    def is_valid_placement(self, piece: List[Tuple[int, int]], r: int, c: int, mask: List[List[bool]]) -> bool:
        covered_colors = set()
        for dr, dc in piece:
            nr, nc = r + dr, c + dc
            if not (0 <= nr < self.rows and 0 <= nc < self.cols):
                return False
            if mask[nr][nc]:
                return False
            
            color = self.grid[nr][nc]
            if color in covered_colors:
                return False
            covered_colors.add(color)
        return True

    def solve(self) -> Optional[List[Dict]]:
        mask = [[False for _ in range(self.cols)] for _ in range(self.rows)]
        placements = []
        if self._backtrack(0, mask, placements):
            return placements
        return None

    def _backtrack(self, piece_idx: int, mask: List[List[bool]], placements: List[Dict]) -> bool:
        if piece_idx == self.num_pieces:
            # Check if all cells are covered (sum of sizes should be 25, but double check)
            for r in range(self.rows):
                for c in range(self.cols):
                    if not mask[r][c]:
                        return False
            return True

        piece = self.pieces[piece_idx]
        
        # Optimization: Try placing piece at all possible (r, c)
        for r in range(self.rows):
            for c in range(self.cols):
                if self.is_valid_placement(piece, r, c, mask):
                    # Place piece
                    for dr, dc in piece:
                        mask[r + dr][c + dc] = True
                    
                    placements.append({
                        "piece_idx": piece_idx,
                        "origin": (r, c),
                        "coords": [(r + dr, c + dc) for dr, dc in piece]
                    })

                    if self._backtrack(piece_idx + 1, mask, placements):
                        return True

                    # Backtrack
                    placements.pop()
                    for dr, dc in piece:
                        mask[r + dr][c + dc] = False
        
        return False

def solve_puzzle(grid: List[List[int]], pieces: List[List[Tuple[int, int]]]):
    solver = Solver(grid, pieces)
    return solver.solve()
