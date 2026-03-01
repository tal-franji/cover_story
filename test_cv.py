from cv_engine import process_screenshot
import cv2
import json

def test_cv_engine():
    img_path = "cover_story_2.jpeg"
    print(f"Processing {img_path}...")
    
    result = process_screenshot(img_path)
    
    if result:
        print("CV Analysis Successful!")
        # Optional: Save a visual check image
        img = cv2.imread(img_path)
        x, y, w, h = result['board_rect']
        # Draw the board boundary in green
        cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 4)
        
        # Draw individual cells (center dots) if we have them
        if 'debug_dots' in result:
            for dx, dy in result['debug_dots']:
                cv2.circle(img, (dx, dy), 5, (0, 0, 255), -1)
                
        cv2.imwrite("cv_check.jpg", img)
        print("\nVisual check saved to cv_check.jpg")
    else:
        print("Failed to detect board in the screenshot.")

if __name__ == "__main__":
    test_cv_engine()
