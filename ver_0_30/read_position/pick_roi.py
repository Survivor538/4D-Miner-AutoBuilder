import os
import cv2
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

IMG_PATH = os.path.join(BASE_DIR, "debug", "full_crop.png")
OUT_PATH = os.path.join(BASE_DIR, ", "roi_config.json")

img = cv2.imread(IMG_PATH)
if img is None:
    print(f"找不到 {IMG_PATH}，请先运行一次 main.py 生成截图")
    exit()

print("请先选择 position 整行区域")
roi_pos = cv2.selectROI("select position_line", img, False, False)
cv2.destroyAllWindows()

print("请再选择 facing_direction 整行区域")
roi_face = cv2.selectROI("select facing_line", img, False, False)
cv2.destroyAllWindows()

x1, y1, w1, h1 = map(int, roi_pos)
x2, y2, w2, h2 = map(int, roi_face)

data = {
    "position_line": {
        "roi": [x1, y1, w1, h1]
    },
    "facing_line": {
        "roi": [x2, y2, w2, h2]
    }
}

with open(OUT_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("已保存到", OUT_PATH)
print(json.dumps(data, ensure_ascii=False, indent=2))
