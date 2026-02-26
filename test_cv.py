from cv_engine import process_screenshot
import cv2
import json

def test_cv_engine():
    img_path = "cover_story_screen.jpeg"
    print(f"Processing {img_path}...")
    
    result = process_screenshot(img_path)
    
    if result:
        print("CV Analysis Successful!")
        print("\nGrid (Color Clusters):")
        for row in result['grid']:
            print(row)
            
        print(f"\nDetected {len(result['pieces'])} pieces.")
        for i, piece in enumerate(result['pieces']):
            print(f"Piece {i}: {piece}")
            
        # Optional: Save a visual check image
        img = cv2.imread(img_path)
        x, y, w, h = result['board_rect']
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 3)
        cv2.imwrite("cv_check.jpg", img)
        print("\nVisual check saved to cv_check.jpg")
    else:
        print("Failed to detect board in the screenshot.")

if __name__ == "__main__":
    test_cv_engine()
