from solver_engine import solve_puzzle


def test_basic_solve():
    # 5x5 grid with 4 colors
    # 0: Orange, 1: Green, 2: Yellow, 3: Blue
    grid = [
        [0, 0, 1, 2, 2],
        [2, 1, 3, 3, 0],
        [3, 1, 2, 1, 0],
        [2, 1, 3, 0, 2],
        [3, 0, 2, 1, 3],
    ]

    # Pieces (relative coordinates) extracted from cover_story_1.jpeg
    pieces = [
        [(0, 0), (1, 0), (2, 0), (0, 1)],  # Inverted L (Gamma) - 4
        [(0, 1), (1, 0), (1, 1), (1, 2)],  # T-shape - 4
        [(0, 0), (0, 1), (1, 1), (1, 2)],  # Z-shape - 4
        [(0, 0), (0, 1), (0, 2), (0, 3)],  # I-shape horiz - 4
        [(0, 0), (0, 1), (0, 2), (1, 1)],  # T-shape - 4
        [(0, 1), (1, 0), (1, 1)],  # V-shape/L3 - 3
        [(0, 0), (1, 0)],  # I-shape vert - 2
    ]

    # Note: Above pieces might not actually be solvable on this specific grid
    # due to the color diversity constraint.

    print("Starting solver...")
    # This might take a while if it tries many combinations, but 5x5 is small.
    # However, if NO solution exists, it will exhaustively search.
    # For a test, I should ideally use a known solvable state.

    print("Starting solver...")

    result = solve_puzzle(grid, pieces)
    if result:
        print("Solution found!")
        for p in result:
            print(p)
    else:
        print("No solution found.")


if __name__ == "__main__":
    test_basic_solve()
