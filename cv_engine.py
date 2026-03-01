import cv2
import numpy as np
from sklearn.cluster import KMeans  # type: ignore
from typing import List, Tuple, Optional


class CVEngine:
    def __init__(self):
        pass

    def detect_grid(
        self, img: np.ndarray
    ) -> Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]]]:
        """
        Detects the 5x5 board in the screenshot by finding the centers of colored circles.
        Returns the cropped board image and its (x, y, w, h) coordinates.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (7, 7), 0)
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV, 11, 2
        )

        # Join gaps in circle outlines
        kernel = np.ones((5, 5), np.uint8)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)
        cv2.imwrite("thresh_debug.jpg", thresh)

        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        height, width = img.shape[:2]

        # 1. Find all circle-ish candidates (the colored dots)
        candidates = []
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 500 < area < 15000:
                x, y, w, h = cv2.boundingRect(cnt)
                if 0.7 <= float(w) / h <= 1.3:
                    # In the top 70% of the screen
                    if height * 0.1 < y < height * 0.7:
                        candidates.append((x + w // 2, y + h // 2, w, h))

        print(f"DEBUG: Found {len(candidates)} potential dot candidates.")

        # 2. Group into rows
        candidates.sort(key=lambda c: c[1])
        rows = []
        if candidates:
            curr_row = [candidates[0]]
            for i in range(1, len(candidates)):
                if candidates[i][1] - curr_row[-1][1] < candidates[i][3] * 0.7:
                    curr_row.append(candidates[i])
                else:
                    if len(curr_row) >= 3:
                        rows.append(sorted(curr_row, key=lambda r: r[0]))
                    curr_row = [candidates[i]]
            if len(curr_row) >= 3:
                rows.append(sorted(curr_row, key=lambda r: r[0]))

        print(f"DEBUG: Grouped into {len(rows)} potential rows.")

        # 3. Find 5 rows that form the grid
        best_rows = []
        for i in range(len(rows) - 4):
            candidate_rows = rows[i : i + 5]
            if all(4 <= len(r) <= 12 for r in candidate_rows):
                best_rows = candidate_rows
                break

        if not best_rows and len(rows) >= 5:
            # Try to find any 5 rows with ~5-10 elements
            potentials = [r for r in rows if 4 <= len(r) <= 12]
            if len(potentials) >= 5:
                # Prioritize top 5 rows
                best_rows = potentials[:5]

        if best_rows:
            all_dots = []
            for r in best_rows:
                # Deduplicate dots in the same row that are too close (X distance < dot_width/2)
                row_dots = []
                if r:
                    row_dots.append(r[0])
                    for d in r[1:]:
                        if d[0] - row_dots[-1][0] > d[2] // 2:
                            row_dots.append(d)
                all_dots.extend(row_dots)

            if len(all_dots) < 15:
                return None, None

            min_x = min(d[0] - d[2] for d in all_dots)
            max_x = max(d[0] + d[2] for d in all_dots)
            min_y = min(d[1] - d[3] for d in all_dots)
            max_y = max(d[1] + d[3] for d in all_dots)

            # Add margin for the pale square background (approx one cell width)
            # The distance between dots is ~160px.
            pitch = (max_x - min_x) // 4 if len(best_rows[0]) > 1 else 100

            x1, y1 = max(0, min_x - int(pitch * 0.6)), max(0, min_y - int(pitch * 0.6))
            x2, y2 = min(width, max_x + int(pitch * 0.6)), min(
                height, max_y + int(pitch * 0.6)
            )

            board_rect = (x1, y1, x2 - x1, y2 - y1)
            print(f"Detected 5x5 board via dot structure: {board_rect}")
            # Save for debugging in the engine instance
            self.debug_dots = [(d[0], d[1]) for d in all_dots]
            return img[y1:y2, x1:x2], board_rect

        return None, None

        return None, None

    def classify_colors(
        self, img: np.ndarray, k: int = 5
    ) -> Tuple[np.ndarray, List[List[int]]]:
        """
        Uses K-Means to identify colors using the pre-detected dot centers.
        Returns (labels_grid, cluster_centers_bgr)
        """
        cell_centers: List[List[float]] = []

        # If we have pre-detected dots, sample them directly from the ORIGINAL image
        if hasattr(self, "debug_dots") and len(self.debug_dots) == 25:
            for dx, dy in self.debug_dots:
                # Sample a tiny 5x5 area around the center of the dot
                x1, x2 = max(0, dx - 5), min(img.shape[1], dx + 6)
                y1, y2 = max(0, dy - 5), min(img.shape[0], dy + 6)
                roi = img[y1:y2, x1:x2]
                if roi.size == 0:
                    avg_color = [255.0, 255.0, 255.0]
                else:
                    avg_color = list(cv2.mean(roi)[:3])
                cell_centers.append(avg_color)
        else:
            # Fallback to board-img grid sampling (should not happen with good detection)
            # This part remains mostly for safety or older code versions.
            h, w = img.shape[:2]
            cell_h, cell_w = h // 5, w // 5
            for r in range(5):
                for c in range(5):
                    y1, y2 = r * cell_h + int(cell_h * 0.35), (r + 1) * cell_h - int(
                        cell_h * 0.35
                    )
                    x1, x2 = c * cell_w + int(cell_w * 0.35), (c + 1) * cell_w - int(
                        cell_w * 0.35
                    )
                    roi = img[y1:y2, x1:x2]
                    avg_color = (
                        list(cv2.mean(roi)[:3])
                        if roi.size > 0
                        else [255.0, 255.0, 255.0]
                    )
                    cell_centers.append(avg_color)

        # Cluster the 25 average colors into K clusters
        cell_centers_np = np.array(cell_centers, dtype=np.float32)
        kmeans = KMeans(n_clusters=k, n_init=10, random_state=0).fit(cell_centers_np)
        labels = kmeans.labels_

        # Convert cluster centers to standard Python ints [B, G, R]
        cluster_centers = kmeans.cluster_centers_.astype(int).tolist()

        # Reshape labels into 5x5 grid
        return labels.reshape((5, 5)).tolist(), cluster_centers

    def extract_pieces(
        self, img: np.ndarray, board_rect: Tuple[int, int, int, int]
    ) -> List[List[Tuple[int, int]]]:
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
        if in_band:
            bands.append((start, len(active_rows)))

        # For each band, check if it contains multiple squares by looking for local minima
        all_square_heights = []
        for start, end in bands:
            if end - start < 20:
                continue
            if end - start > 150:
                continue  # Likely bottom artifact

            # Find local minima in this band to detect gaps between squares

            # If there's a significant dip, split the band
            # For now, let's just use the band heights to estimate B
            all_square_heights.append(end - start)

        print(f"Detected potential bands: {bands}")

        # Estimate B more robustly
        # Many squares are ~40px. Let's find the best B in [30, 60]
        if all_square_heights:
            best_b = 40.0
            best_err = float("inf")
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
            if r_start < 60:
                continue
            if r_end - r_start < 25:
                continue
            if r_end - r_start > 150:
                continue

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
            if in_col:
                col_segments.append((c_start, len(col_sums)))

            for c_start, c_end in col_segments:
                w = c_end - c_start
                if w < B * 0.7:
                    continue
                n_cols = max(1, int(np.round(w / B)))
                n_rows = max(1, int(np.round((r_end - r_start) / B)))

                cw, ch = w / n_cols, (r_end - r_start) / n_rows
                for rb in range(n_rows):
                    for cb in range(n_cols):
                        y1, y2 = r_start + int(rb * ch), r_start + int((rb + 1) * ch)
                        x1, x2 = c_start + int(cb * cw), c_start + int((cb + 1) * cw)
                        # Check occupancy on the raw (un-dilated) mask for precision
                        cell = mask[y1:y2, x1:x2]
                        # 40% occupancy is safer for smaller blocks
                        if cell.size > 0 and np.sum(cell) > (cell.size * 255 * 0.4):
                            square_centers.append(
                                (
                                    r_start + int((rb + 0.5) * ch),
                                    c_start + int((cb + 0.5) * cw),
                                )
                            )

        print(f"Collected {len(square_centers)} square centers.")

        # 4. Cluster adjacent squares into pieces using BFS
        pieces = []
        visited = set()
        for i in range(len(square_centers)):
            if i in visited:
                continue
            q = [i]
            visited.add(i)
            piece_centers = []
            while q:
                curr_idx = q.pop(0)
                curr_p = square_centers[curr_idx]
                piece_centers.append(curr_p)
                for j in range(len(square_centers)):
                    if j not in visited:
                        other_p = square_centers[j]
                        dist = np.sqrt(
                            (curr_p[0] - other_p[0]) ** 2
                            + (curr_p[1] - other_p[1]) ** 2
                        )
                        # Adjacency: B is square size, pitch is ~B+5. Use 1.3*B (~40px)
                        if dist < B * 1.3 or dist < 45.0:
                            visited.add(j)
                            q.append(j)

            # Normalize piece to grid coordinates
            min_y, min_x = min(p[0] for p in piece_centers), min(
                p[1] for p in piece_centers
            )
            grid_coords = set()
            for py, px in piece_centers:
                grid_coords.add(
                    (int(np.round((py - min_y) / B)), int(np.round((px - min_x) / B)))
                )

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
    if board_img is None or board_rect is None:
        print("Error: Could not detect grid.")
        return None

    print("Classifying colors...")
    grid, cluster_colors = engine.classify_colors(img)
    print("Extracting pieces...")
    pieces = engine.extract_pieces(img, board_rect)

    return {
        "grid": grid,
        "cluster_colors": cluster_colors,
        "pieces": pieces,
        "board_rect": board_rect,
        "debug_dots": getattr(engine, "debug_dots", []),
    }
