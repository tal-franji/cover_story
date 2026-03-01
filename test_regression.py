import json
import os
import sys
import cv2
import numpy as np
from cv_engine import process_screenshot
from solver_engine import solve_puzzle

REGRESSION_FILE = "regression_data.json"

def load_regression():
    if os.path.exists(REGRESSION_FILE):
        with open(REGRESSION_FILE, "r") as f:
            return json.load(f)
    return {}

def save_regression(data):
    with open(REGRESSION_FILE, "w") as f:
        json.dump(data, f, indent=4)

def compare_rects(rect1, rect2, tol=20):
    for a, b in zip(rect1, rect2):
        if abs(a - b) > tol:
            return False
    return True

def run_tests(update=False):
    files = [f for f in os.listdir(".") if f.startswith("cover_story_") and f.endswith(".jpeg")]
    files.sort()
    
    regression_data = load_regression()
    all_passed = True
    
    for filename in files:
        print(f"\n--- Testing {filename} ---")
        result = process_screenshot(filename)
        if not result:
            print(f"FAILED: Could not process {filename}")
            all_passed = False
            continue
            
        # 1. Bounding Box check
        board_rect = result['board_rect']
        print(f"  Board Rect: {board_rect}")
        
        # 2. Color info
        grid = result['grid']
        num_colors = len(result['cluster_colors'])
        print(f"  Colors found: {num_colors}")
        
        # 3. Piece sum check
        pieces = result['pieces']
        total_blocks = sum(len(p) for p in pieces)
        print(f"  Pieces: {len(pieces)}, Total Blocks: {total_blocks}")
        
        # 4. Solver check
        solution = solve_puzzle(grid, pieces)
        has_solution = solution is not None
        print(f"  Solver: {'Success' if has_solution else 'Failed'}")
        
        current_v = {
            "board_rect": list(board_rect),
            "num_colors": num_colors,
            "grid": grid,
            "total_blocks": total_blocks,
            "has_solution": has_solution,
            # We don't store the full solution yet to keep it simple, 
            # but we could store the placement count.
            "num_pieces": len(pieces)
        }
        
        if update:
            regression_data[filename] = current_v
            print(f"  UPDATED baseline for {filename}")
        else:
            if filename not in regression_data:
                print(f"  SKIPPING comparison: No baseline for {filename}")
                all_passed = False
                continue
            
            baseline = regression_data[filename]
            
            # Compare
            match = True
            if not compare_rects(baseline['board_rect'], current_v['board_rect']):
                print(f"  FAILED: Board Rect mismatch. Expected {baseline['board_rect']}, got {current_v['board_rect']}")
                match = False
            if baseline['num_colors'] != current_v['num_colors']:
                print(f"  FAILED: Color count mismatch. Expected {baseline['num_colors']}, got {current_v['num_colors']}")
                match = False
            if baseline['grid'] != current_v['grid']:
                print(f"  FAILED: Grid layout mismatch.")
                match = False
            if baseline['total_blocks'] != 25:
                print(f"  WARNING: Total blocks is {current_v['total_blocks']}, expected 25 for a full board.")
                # We don't necessarily fail here if the baseline also had this, 
                # but for Cover Story it should ALWAYS be 25.
            if baseline['total_blocks'] != current_v['total_blocks']:
                print(f"  FAILED: Block count mismatch. Expected {baseline['total_blocks']}, got {current_v['total_blocks']}")
                match = False
            if baseline['has_solution'] != current_v['has_solution']:
                print(f"  FAILED: Solver status mismatch.")
                match = False
                
            if match:
                print(f"  PASSED regression for {filename}")
            else:
                all_passed = False
                
    if update:
        save_regression(regression_data)
        print("\nRegression data updated successfully.")
        
    return all_passed

if __name__ == "__main__":
    update_flag = "--update" in sys.argv
    success = run_tests(update=update_flag)
    sys.exit(0 if success else 1)
