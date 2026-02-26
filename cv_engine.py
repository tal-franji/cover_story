import cv2
import numpy as np
from sklearn.cluster import KMeans
from typing import List, Tuple, Dict, Any

class CVEngine:
    def __init__(self):
        pass

    def detect_grid(self, img: np.ndarray) -> Tuple[np.ndarray, Tuple[int, int, int, int]]:
        """
        Detects the 5x5 board in the screenshot.
        Returns the cropped board image and its (x, y, w, h) coordinates.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2)
        cv2.imwrite("thresh_debug.jpg", thresh)
        
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        height, width = img.shape[:2]
        board_contour = None
        max_area = 0
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 5000: continue # Ignore very small noise
            
            x, y, w, h = cv2.boundingRect(cnt)
            aspect_ratio = float(w)/h
            
            # The board area (800x800) is ~640k. 
            # A single cell (160x160) is ~25k.
            # We are looking for the total board area.
            if 0.8 <= aspect_ratio <= 1.2 and area > 100000 and y < height * 0.5:
                # This is likely the board!
                if area > max_area:
                    max_area = area
                    board_contour = (x, y, w, h)
                    print(f"Found Board Candidate: {board_contour} area={area}")
        
        # Fallback: if no clear square board found, use the top half of the main container
        if not board_contour:
             # Find the large container again (from previous logs we know it's around 800x1200)
             for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > 500000:
                    x, y, w, h = cv2.boundingRect(cnt)
                    if y < height * 0.4:
                        # Estimate board as a square at the top of this container
                        board_contour = (x, y, w, w) # Use width as height for squareness
                        print(f"Fallback Board (using container top): {board_contour}")
                        break
        
        if board_contour:
            x, y, w, h = board_contour
            return img[y:y+h, x:x+w], board_contour
        return None, None

    def classify_colors(self, board_img: np.ndarray, k: int = 5) -> Tuple[np.ndarray, List[List[int]]]:
        """
        Uses K-Means to identify colors on the 5x5 grid.
        Returns (labels_grid, cluster_centers_bgr)
        """
        h, w = board_img.shape[:2]
        cell_h, cell_w = h // 5, w // 5
        
        grid_data = []
        cell_centers = []
        
        for r in range(5):
            row = []
            for c in range(5):
                # Extract the center of the cell to avoid borders
                y1, y2 = r * cell_h + cell_h // 4, (r + 1) * cell_h - cell_h // 4
                x1, x2 = c * cell_w + cell_w // 4, (c + 1) * cell_w - cell_w // 4
                cell_roi = board_img[y1:y2, x1:x2]
                
                # Average color of the cell center
                avg_color = cv2.mean(cell_roi)[:3]
                cell_centers.append(avg_color)
                row.append(avg_color)
            grid_data.append(row)
            
        # Cluster the 25 average colors into K clusters
        cell_centers_np = np.array(cell_centers, dtype=np.float32)
        kmeans = KMeans(n_clusters=k, random_state=0).fit(cell_centers_np)
        labels = kmeans.labels_
        
        # Convert cluster centers to standard Python ints [B, G, R]
        cluster_centers = kmeans.cluster_centers_.astype(int).tolist()
        
        # Reshape labels into 5x5 grid
        return labels.reshape((5, 5)).tolist(), cluster_centers

    def extract_pieces(self, img: np.ndarray, board_rect: Tuple[int, int, int, int]) -> List[List[Tuple[int, int]]]:
        """
        Extracts pieces from the bottom section of the image.
        """
        height, width = img.shape[:2]
        bx, by, bw, bh = board_rect
        
        # Search area is below the board
        search_y = by + bh
        piece_area = img[search_y:, :]
        
        # Pieces are light blue. Stricter saturation/value might help see gaps.
        hsv = cv2.cvtColor(piece_area, cv2.COLOR_BGR2HSV)
        # Narrower range to capture רק the blue centers
        lower_blue = np.array([90, 40, 180])
        upper_blue = np.array([120, 255, 255])
        mask = cv2.inRange(hsv, lower_blue, upper_blue)
        
        # Save raw mask before any merging to see the squares
        cv2.imwrite("piece_mask_debug.jpg", mask)
        
        # For the internal logic, we might still want a slight dilation to help findContours,
        # but let's keep it minimal or separate it from the debug output.
        proc_mask = cv2.dilate(mask, np.ones((2, 2), np.uint8), iterations=1)
        
        # 1. Horizontal Projection -> Find Rows and detect sub-gaps
        row_sums = np.sum(proc_mask, axis=1)
        # Find peaks in the derivative or just local minima to see if we can find square edges
        # But first, let's just find the large bands.
        h_threshold = np.max(row_sums) * 0.05
        active_rows = row_sums > h_threshold
        
        # Determine ranges of activity
        bands = []
        in_band = False
        for i, val in enumerate(active_rows):
            if val and not in_band:
                start = i
                in_band = True
            elif not val and in_band:
                bands.append((start, i))
                in_band = False
        if in_band: bands.append((start, len(active_rows)))
        
        # For each band, check if it contains multiple squares by looking for local minima
        all_square_heights = []
        for start, end in bands:
            if end - start < 20: continue
            if end - start > 150: continue # Likely bottom artifact
            
            # Find local minima in this band to detect gaps between squares
            band_data = row_sums[start:end]
            # Smooth it slightly
            smoothed = np.convolve(band_data, np.ones(5)/5, mode='same')
            
            # If there's a significant dip, split the band
            # For now, let's just use the band heights to estimate B
            all_square_heights.append(end - start)
            
        print(f"Detected potential bands: {bands}")
        
        # Estimate B more robustly
        # Many squares are ~40px. Let's find the best B in [30, 60]
        if all_square_heights:
            best_b = 40.0
            best_err = float('inf')
            for b_test in np.linspace(30, 60, 61):
                # Total error for this b_test: how well it divides the heights
                err = 0
                for h in all_square_heights:
                    n = max(1, round(h / b_test))
                    err += abs(h - n * b_test)
                if err < best_err:
                    best_err = err
                    best_b = b_test
            B = best_b
            print(f"Discovered block height B from projections: {B:.1f}")
        else:
            B = 40.0
        
        # 3. Collect all detected squares as pixel centers
        square_centers = []
        for r_start, r_end in bands:
            # Ignore the very top band if it's an artifact from the board edge
            if r_start < 60: continue
            if r_end - r_start < 25: continue
            if r_end - r_start > 150: continue
            
            row_strip = proc_mask[r_start:r_end, :]
            col_sums = np.sum(row_strip, axis=0)
            v_threshold = 20
            
            in_col = False
            col_segments = []
            for i, s in enumerate(col_sums):
                if s > v_threshold and not in_col:
                    c_start = i
                    in_col = True
                elif s <= v_threshold and in_col:
                    col_segments.append((c_start, i))
                    in_col = False
            if in_col: col_segments.append((c_start, len(col_sums)))
            
            for c_start, c_end in col_segments:
                w = c_end - c_start
                if w < B * 0.7: continue
                n_cols = max(1, int(np.round(w / B)))
                n_rows = max(1, int(np.round((r_end - r_start) / B)))
                
                cw, ch = w / n_cols, (r_end - r_start) / n_rows
                for rb in range(n_rows):
                    for cb in range(n_cols):
                        y1, y2 = r_start + int(rb * ch), r_start + int((rb+1) * ch)
                        x1, x2 = c_start + int(cb * cw), c_start + int((cb+1) * cw)
                        # Check occupancy on the raw (un-dilated) mask for precision
                        cell = mask[y1:y2, x1:x2]
                        # 50% occupancy is very safe
                        if cell.size > 0 and np.sum(cell) > (cell.size * 255 * 0.5):
                            square_centers.append((r_start + int((rb+0.5)*ch), c_start + int((cb+0.5)*cw)))
        
        print(f"Collected {len(square_centers)} square centers.")
        
        # 4. Cluster adjacent squares into pieces using BFS
        pieces = []
        visited = set()
        for i in range(len(square_centers)):
            if i in visited: continue
            q = [i]; visited.add(i)
            piece_centers = []
            while q:
                curr_idx = q.pop(0)
                curr_p = square_centers[curr_idx]
                piece_centers.append(curr_p)
                for j in range(len(square_centers)):
                    if j not in visited:
                        other_p = square_centers[j]
                        dist = np.sqrt((curr_p[0]-other_p[0])**2 + (curr_p[1]-other_p[1])**2)
                        # Adjacency: B is square size, pitch is ~B+5. Use 1.3*B (~40px)
                        if dist < B * 1.3 or dist < 45.0: 
                            visited.add(j); q.append(j)
            
            # Normalize piece to grid coordinates
            min_y, min_x = min(p[0] for p in piece_centers), min(p[1] for p in piece_centers)
            grid_coords = set()
            for py, px in piece_centers:
                grid_coords.add((int(np.round((py - min_y) / B)), int(np.round((px - min_x) / B))))
            
            norm_piece = sorted(list(grid_coords))
            # Filter out tiny noise pieces (1 block pieces are only allowed if they are the last block)
            if len(norm_piece) >= 1:
                pieces.append(norm_piece)
                print(f"  Extracted Piece: {norm_piece}")

        total_blocks = sum(len(p) for p in pieces)
        print(f"Total pieces: {len(pieces)}, Total blocks: {total_blocks}")
        return pieces

def process_screenshot(img_path: str):
    print("Loading image...")
    img = cv2.imread(img_path)
    if img is None:
        print(f"Error: Could not load image {img_path}")
        return None
    print("Initializing CVEngine...")
    engine = CVEngine()
    
    print("Detecting grid...")
    board_img, board_rect = engine.detect_grid(img)
    if board_img is None:
        print("Error: Could not detect grid.")
        return None
    
    print("Classifying colors...")
    grid, cluster_colors = engine.classify_colors(board_img)
    print("Extracting pieces...")
    pieces = engine.extract_pieces(img, board_rect)
    
    return {
        "grid": grid,
        "cluster_colors": cluster_colors,
        "pieces": pieces,
        "board_rect": board_rect
    }
