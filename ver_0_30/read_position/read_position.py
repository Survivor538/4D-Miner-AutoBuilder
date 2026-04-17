import os
import re
import json
import time
from collections import Counter

import cv2
import numpy as np
import pyautogui

# =========================
# 路径配置
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)

ROI_CONFIG_PATH = os.path.join(BASE_DIR, "roi_config.json")
COLOR_THRESHOLDS_PATH = os.path.join(BASE_DIR, "color_thresholds.json")
TEMPLATE_COLOR_DIR = os.path.join(BASE_DIR, "templates", "color")
DEBUG_DIR = os.path.join(BASE_DIR, "debug")

# =========================
# 截图区域
# =========================
CAPTURE_X_START = 0.50
CAPTURE_X_END   = 1.00
CAPTURE_Y_START = 0.80
CAPTURE_Y_END   = 1.00

# =========================
# 调试与投票
# =========================
DEBUG = True
VOTE_FRAMES = 1
VOTE_SLEEP = 0.06

# =========================
# 模板匹配阈值
# 这两个值尽量别乱改，先保持稳
# =========================
COLOR_GOOD_SCORE = 0.78
COLOR_MIN_SCORE = 0.58

# =========================
# 字段定义
# =========================
POSITION_FIELDS = [
    ("pos_x", "blue"),
    ("pos_y", "white"),
    ("pos_z", "red"),
    ("pos_w", "green"),
]

FACING_FIELDS = [
    ("face_x", "blue"),
    ("face_z", "red"),
    ("face_w", "green"),
]

FIELDS = [x[0] for x in POSITION_FIELDS + FACING_FIELDS]

# 模板允许识别的字符
# 你要求补：X,Y,Z,W,冒号,P,o,s,i,t,o,n
# 注意：实际统一转成小写处理
TEMPLATE_ALLOWED_CHARS = set("0123456789.-:xyzwpositn")
FINAL_NUMBER_CHARS = set("0123456789.-")

# =========================
# 工具函数
# =========================
def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_debug(name, img):
    if DEBUG:
        ensure_dir(DEBUG_DIR)
        cv2.imwrite(os.path.join(DEBUG_DIR, name), img)

def safe_float(x):
    try:
        return float(x)
    except:
        return None

# =========================
# 截图与裁剪
# =========================
def capture_region():
    screen = pyautogui.screenshot()
    img = np.array(screen)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    h, w, _ = img.shape

    x1 = int(w * CAPTURE_X_START)
    x2 = int(w * CAPTURE_X_END)
    y1 = int(h * CAPTURE_Y_START)
    y2 = int(h * CAPTURE_Y_END)

    crop = img[y1:y2, x1:x2].copy()
    return crop

def crop_field(full_crop, roi):
    x, y, w, h = roi
    return full_crop[y:y + h, x:x + w].copy()

# =========================
# 模板加载
# templates/color/*.png
# =========================
def parse_template_label(filename):
    """
    支持：
    0~9, dot, minus, colon, x, y, z, w, p, o, s, i, t, n
    文件名示例：
      0_1.png
      dot_1.png
      minus_1.png
      colon_1.png
      x_1.png
      y_1.png
      p_1.png
      o_1.png
    """
    name = os.path.splitext(filename)[0].lower()
    base = name.split("_")[0]

    mapping = {
        "dot": ".",
        "minus": "-",
        "colon": ":",
    }

    if base in mapping:
        return mapping[base]

    if base in [str(i) for i in range(10)]:
        return base

    if base in list("xyzwpositn"):
        return base

    # 如果你模板文件名就是单字符，也允许直接识别
    if len(base) == 1 and base in TEMPLATE_ALLOWED_CHARS:
        return base

    return None

def normalize_binary_image(img_bin, out_w=24, out_h=36):
    """
    把二值图归一化到固定大小，便于模板匹配
    """
    if img_bin is None or img_bin.size == 0:
        return np.zeros((out_h, out_w), dtype=np.uint8)

    # 确保是二值图
    if len(img_bin.shape) == 3:
        img_bin = cv2.cvtColor(img_bin, cv2.COLOR_BGR2GRAY)

    _, img_bin = cv2.threshold(img_bin, 127, 255, cv2.THRESH_BINARY)

    ys, xs = np.where(img_bin > 0)
    if len(xs) == 0 or len(ys) == 0:
        return np.zeros((out_h, out_w), dtype=np.uint8)

    x1, x2 = xs.min(), xs.max() + 1
    y1, y2 = ys.min(), ys.max() + 1
    cropped = img_bin[y1:y2, x1:x2]

    h, w = cropped.shape[:2]
    if h == 0 or w == 0:
        return np.zeros((out_h, out_w), dtype=np.uint8)

    scale = min((out_w - 4) / max(w, 1), (out_h - 4) / max(h, 1))
    nw = max(1, int(round(w * scale)))
    nh = max(1, int(round(h * scale)))

    resized = cv2.resize(cropped, (nw, nh), interpolation=cv2.INTER_NEAREST)

    canvas = np.zeros((out_h, out_w), dtype=np.uint8)
    ox = (out_w - nw) // 2
    oy = (out_h - nh) // 2
    canvas[oy:oy + nh, ox:ox + nw] = resized
    return canvas

def load_color_templates(template_dir):
    if not os.path.exists(template_dir):
        raise FileNotFoundError(f"找不到模板目录: {template_dir}")

    templates = []
    for fn in sorted(os.listdir(template_dir)):
        if not fn.lower().endswith(".png"):
            continue

        label = parse_template_label(fn)
        if label is None:
            continue

        path = os.path.join(template_dir, fn)
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            continue

        _, img_bin = cv2.threshold(img, 127, 255, cv2.THRESH_BINARY)
        img_norm = normalize_binary_image(img_bin)

        templates.append({
            "label": label,
            "name": fn,
            "img": img_norm
        })

    return templates

# =========================
# 颜色阈值加载
# 保持你当前成功版本，不硬编码
# =========================
def load_color_thresholds(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到颜色阈值文件: {path}")
    return load_json(path)

# =========================
# 纯颜色 mask
# 从 color_thresholds.json 读取
# 支持:
#   single: lower / upper
#   dual: lower1 / upper1 / lower2 / upper2
# =========================
def extract_color_mask(img_bgr, color_name, color_thresholds):
    hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    color_name = color_name.lower()

    if color_name not in color_thresholds:
        raise KeyError(f"颜色阈值中不存在: {color_name}")

    cfg = color_thresholds[color_name]
    ctype = cfg.get("type", "single").lower()

    if ctype == "single":
        lower = np.array(cfg["lower"], dtype=np.uint8)
        upper = np.array(cfg["upper"], dtype=np.uint8)
        mask = cv2.inRange(hsv, lower, upper)

    elif ctype == "dual":
        lower1 = np.array(cfg["lower1"], dtype=np.uint8)
        upper1 = np.array(cfg["upper1"], dtype=np.uint8)
        lower2 = np.array(cfg["lower2"], dtype=np.uint8)
        upper2 = np.array(cfg["upper2"], dtype=np.uint8)

        mask1 = cv2.inRange(hsv, lower1, upper1)
        mask2 = cv2.inRange(hsv, lower2, upper2)
        mask = cv2.bitwise_or(mask1, mask2)

    else:
        raise ValueError(f"未知颜色阈值类型: {ctype}")

    # 轻量形态学，尽量不破坏你现在的效果
    kernel = np.ones((2, 2), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=1)

    return mask

# =========================
# 连通域 / span 处理
# =========================
def get_connected_components(mask):
    """
    返回过滤后的连通域列表：
    每项包含 x, y, w, h, area
    """
    h, w = mask.shape[:2]
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(mask, connectivity=8)

    comps = []
    for i in range(1, num_labels):
        x = int(stats[i, cv2.CC_STAT_LEFT])
        y = int(stats[i, cv2.CC_STAT_TOP])
        ww = int(stats[i, cv2.CC_STAT_WIDTH])
        hh = int(stats[i, cv2.CC_STAT_HEIGHT])
        area = int(stats[i, cv2.CC_STAT_AREA])

        # 保留小点和负号，所以这里不能太严格
        if area < 2:
            continue
        if ww < 1 or hh < 1:
            continue
        if ww > w * 0.95 and hh > h * 0.95:
            continue

        comps.append({
            "x": x,
            "y": y,
            "w": ww,
            "h": hh,
            "area": area
        })

    comps.sort(key=lambda c: c["x"])
    return comps

def merge_vertical_char_components(comps, mask_h,
                                   x_center_tol=4,
                                   x_overlap_min=0,
                                   y_gap_tol_ratio=0.35,
                                   narrow_width_ratio=0.40,
                                   max_area_ratio=0.30):
    """
    合并上下分离、但属于同一字符的连通域，例如：
    - ':' -> 上点 + 下点
    - 'i' -> 上点 + 下方主体

    参数：
    - x_center_tol: 两个连通域中心x允许偏差
    - x_overlap_min: x方向至少重叠多少像素（可为0）
    - y_gap_tol_ratio: 上下间距占整行高度的最大比例
    - narrow_width_ratio: 细字符宽度阈值（相对整行高度）
    - max_area_ratio: 仅合并较小块，避免误并大字符
    """
    if not comps:
        return []

    used = [False] * len(comps)
    merged = []

    y_gap_tol = max(2, int(mask_h * y_gap_tol_ratio))
    narrow_width = max(2, int(mask_h * narrow_width_ratio))
    max_area = max(6, int(mask_h * mask_h * max_area_ratio * 0.08))

    for i, a in enumerate(comps):
        if used[i]:
            continue

        best_j = -1
        best_score = 10**9

        ax1, ay1, aw, ah = a["x"], a["y"], a["w"], a["h"]
        ax2, ay2 = ax1 + aw, ay1 + ah
        acx = ax1 + aw / 2.0

        for j, b in enumerate(comps):
            if j == i or used[j]:
                continue

            bx1, by1, bw, bh = b["x"], b["y"], b["w"], b["h"]
            bx2, by2 = bx1 + bw, by1 + bh
            bcx = bx1 + bw / 2.0

            # 只考虑上下关系
            if ay1 <= by1:
                top = a
                bottom = b
                tx1, ty1, tw, th = ax1, ay1, aw, ah
                tx2, ty2 = ax2, ay2
                bx1_, by1_, bw_, bh_ = bx1, by1, bw, bh
                bx2_, by2_ = bx2, by2
                tcx, bcx_ = acx, bcx
            else:
                top = b
                bottom = a
                tx1, ty1, tw, th = bx1, by1, bw, bh
                tx2, ty2 = bx2, by2
                bx1_, by1_, bw_, bh_ = ax1, ay1, aw, ah
                bx2_, by2_ = ax2, ay2
                tcx, bcx_ = bcx, acx

            vertical_gap = by1_ - ty2
            if vertical_gap < 0:
                # 已经上下重叠了，通常不需要走这个合并
                continue
            if vertical_gap > y_gap_tol:
                continue

            center_dx = abs(tcx - bcx_)
            if center_dx > x_center_tol:
                continue

            overlap_x = min(tx2, bx2_) - max(tx1, bx1_)
            if overlap_x < x_overlap_min:
                continue

            # 至少有一个要比较窄，防止把普通相邻字符误合并
            if not (tw <= narrow_width or bw_ <= narrow_width):
                continue

            # 限制面积，优先合并小块（点、冒号点、i的点）
            if a["area"] > max_area and b["area"] > max_area:
                continue

            # 分数越小越好
            score = center_dx * 3 + vertical_gap

            if score < best_score:
                best_score = score
                best_j = j

        if best_j >= 0:
            b = comps[best_j]
            used[i] = True
            used[best_j] = True

            nx1 = min(a["x"], b["x"])
            ny1 = min(a["y"], b["y"])
            nx2 = max(a["x"] + a["w"], b["x"] + b["w"])
            ny2 = max(a["y"] + a["h"], b["y"] + b["h"])

            merged.append({
                "x": nx1,
                "y": ny1,
                "w": nx2 - nx1,
                "h": ny2 - ny1,
                "area": a["area"] + b["area"]
            })
        else:
            used[i] = True
            merged.append(a)

    merged.sort(key=lambda c: c["x"])
    return merged

def get_color_span(mask, pad_x=2):
    """
    找某一颜色在整行中的总体横向范围。
    注意：这里故意取“总包围盒”，因为白色可能同时包含 Position 和 Y 数值，
    后续识别会靠模板+清洗去掉字母。
    """
    comps = get_connected_components(mask)
    if not comps:
        return None

    h, w = mask.shape[:2]
    x1 = max(0, min(c["x"] for c in comps) - pad_x)
    x2 = min(w, max(c["x"] + c["w"] for c in comps) + pad_x)

    if x2 <= x1:
        return None

    return (x1, x2)

# =========================
# 大框拆成字段
# 你当前规则：
# position_line: blue -> white -> red -> green
# facing_line:   blue -> red   -> green
# =========================
def split_line_by_colors(line_img, line_name, color_thresholds):
    if line_name == "position_line":
        order = POSITION_FIELDS
    elif line_name == "facing_line":
        order = FACING_FIELDS
    else:
        raise ValueError(f"未知 line_name: {line_name}")

    result = {}
    debug_vis = line_img.copy()

    for field_name, color_name in order:
        mask = extract_color_mask(line_img, color_name, color_thresholds)
        save_debug(f"{line_name}_{field_name}_{color_name}_mask.png", mask)

        span = get_color_span(mask)
        if span is None:
            result[field_name] = None
            continue

        x1, x2 = span
        crop = line_img[:, x1:x2].copy()
        result[field_name] = crop

        cv2.rectangle(debug_vis, (x1, 0), (x2, line_img.shape[0] - 1), (0, 255, 0), 1)
        cv2.putText(
            debug_vis,
            field_name,
            (x1, min(line_img.shape[0] - 2, 12)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (0, 255, 0),
            1,
            cv2.LINE_AA
        )

        save_debug(f"{field_name}_roi.png", crop)

    save_debug(f"{line_name}_split_debug.png", debug_vis)
    return result

# =========================
# 模板匹配 OCR
# =========================
def compute_match_score(a_bin, b_bin):
    """
    a_bin / b_bin: 已经 normalize_binary_image 后的 0/255 二值图
    输出 0~1 分数
    """
    a = (a_bin > 0).astype(np.uint8)
    b = (b_bin > 0).astype(np.uint8)

    inter = np.logical_and(a, b).sum()
    union = np.logical_or(a, b).sum()
    iou = inter / union if union > 0 else 0.0

    xor_ratio = np.logical_xor(a, b).mean()
    pixel_agree = 1.0 - xor_ratio

    score = 0.65 * iou + 0.35 * pixel_agree
    return float(score)

def split_mask_to_chars(mask):
    """
    从字段 mask 中切出字符
    先找连通域，再把 ':'、'i' 这类上下分离结构合并
    """
    comps = get_connected_components(mask)

    # 关键：先合并上下结构字符
    comps = merge_vertical_char_components(comps, mask.shape[0])

    chars = []

    for c in comps:
        x, y, w, h = c["x"], c["y"], c["w"], c["h"]
        char = mask[y:y + h, x:x + w].copy()
        chars.append({
            "x": x,
            "y": y,
            "w": w,
            "h": h,
            "img": char
        })

    chars.sort(key=lambda t: t["x"])
    return chars

def match_one_char(char_img, templates):
    char_norm = normalize_binary_image(char_img)

    best = None
    best_score = -1.0

    for tpl in templates:
        score = compute_match_score(char_norm, tpl["img"])
        if score > best_score:
            best_score = score
            best = tpl

    if best is None:
        return None, 0.0, char_norm

    return best["label"], best_score, char_norm

def recognize_by_templates(mask, templates, debug_prefix="ocr"):
    chars = split_mask_to_chars(mask)

    if not chars:
        return None, 0.0, []

    text = ""
    scores = []
    detail = []

    for i, ch in enumerate(chars):
        label, score, norm_img = match_one_char(ch["img"], templates)
        if label is None:
            continue

        text += label
        scores.append(score)
        detail.append({
            "index": i,
            "label": label,
            "score": score,
            "x": ch["x"],
            "y": ch["y"],
            "w": ch["w"],
            "h": ch["h"]
        })

        save_debug(f"{debug_prefix}_char_{i}_{label}_{score:.3f}.png", norm_img)

    if not text:
        return None, 0.0, detail

    avg_score = float(sum(scores) / len(scores)) if scores else 0.0
    return text, avg_score, detail

# =========================
# 文本清洗
# 把 Position/Y:/X: 等字母和冒号清掉，只留数字
# =========================
def clean_number_text(text):
    if text is None:
        return None

    # 全转小写，防止模板文件名大小写不同
    text = text.lower()

    # 先直接尝试用正则抽取“最后一个数”
    # 这样对 "positiony:64.0"、"x:-123.4" 都比较稳
    matches = re.findall(r"-?\d+(?:\.\d+)?", text)
    if matches:
        return matches[-1]

    # 如果正则没抽到，再做保底清洗
    filtered = "".join(ch for ch in text if ch in FINAL_NUMBER_CHARS)

    if not filtered:
        return None

    # 处理多个负号
    if filtered.count("-") > 1:
        first = filtered.find("-")
        filtered = "-" + filtered[first + 1:].replace("-", "")

    # 负号只允许在最前
    if "-" in filtered and not filtered.startswith("-"):
        filtered = filtered.replace("-", "")

    # 处理多个小数点
    if filtered.count(".") > 1:
        first = filtered.find(".")
        filtered = filtered[:first + 1] + filtered[first + 1:].replace(".", "")

    # 至少要有一个数字
    if not re.search(r"\d", filtered):
        return None

    return filtered.strip() if filtered.strip() else None

def plausible_value(field_name, text):
    """
    这里保持宽松，不做过强限制，避免影响你现在已经成功的效果。
    """
    val = safe_float(text)
    return val is not None

# =========================
# 单字段识别
# 仅颜色识别，不使用 shadow
# =========================
def recognize_field(field_img, field_name, color_name, color_templates, color_thresholds):
    if field_img is None or field_img.size == 0:
        return None, 0.0, "empty", []

    color_mask = extract_color_mask(field_img, color_name, color_thresholds)
    save_debug(f"{field_name}_color_mask.png", color_mask)

    color_text, color_score, color_detail = recognize_by_templates(
        color_mask,
        color_templates,
        debug_prefix=f"{field_name}_color"
    )

    cleaned = clean_number_text(color_text)

    if cleaned is None:
        return None, color_score, "color_none", color_detail

    if color_score < COLOR_MIN_SCORE:
        return cleaned, color_score, "color_low", color_detail

    if not plausible_value(field_name, cleaned):
        return cleaned, color_score, "color_unplausible", color_detail

    return cleaned, color_score, "color", color_detail

# =========================
# 单次识别流程
# =========================
def read_once(roi_cfg, color_thresholds, color_templates):
    full_crop = capture_region()
    save_debug("full_crop.png", full_crop)

    if "position_line" not in roi_cfg or "facing_line" not in roi_cfg:
        raise KeyError("roi_config.json 必须包含 position_line 和 facing_line")

    pos_roi = roi_cfg["position_line"]["roi"]
    face_roi = roi_cfg["facing_line"]["roi"]

    position_line = crop_field(full_crop, pos_roi)
    facing_line = crop_field(full_crop, face_roi)

    save_debug("position_line.png", position_line)
    save_debug("facing_line.png", facing_line)

    split_pos = split_line_by_colors(position_line, "position_line", color_thresholds)
    split_face = split_line_by_colors(facing_line, "facing_line", color_thresholds)

    field_imgs = {}
    field_imgs.update(split_pos)
    field_imgs.update(split_face)

    color_map = dict(POSITION_FIELDS + FACING_FIELDS)
    final_results = {}

    for field_name in FIELDS:
        field_img = field_imgs.get(field_name)
        color_name = color_map[field_name]

        text, score, source, detail = recognize_field(
            field_img, field_name, color_name, color_templates, color_thresholds
        )

        final_results[field_name] = {
            "text": text,
            "score": score,
            "source": source,
            "detail": detail,
        }

    position = (
        safe_float(final_results["pos_x"]["text"]),
        safe_float(final_results["pos_y"]["text"]),
        safe_float(final_results["pos_z"]["text"]),
        safe_float(final_results["pos_w"]["text"]),
    )

    facing = (
        safe_float(final_results["face_x"]["text"]),
        safe_float(final_results["face_z"]["text"]),
        safe_float(final_results["face_w"]["text"]),
    )

    return final_results, position, facing

# =========================
# 多帧投票
# =========================
def tuple_is_valid(t):
    return t is not None and all(v is not None for v in t)

def read_with_vote():
    ensure_dir(DEBUG_DIR)

    roi_cfg = load_json(ROI_CONFIG_PATH)
    color_thresholds = load_color_thresholds(COLOR_THRESHOLDS_PATH)
    color_templates = load_color_templates(TEMPLATE_COLOR_DIR)

    #print(f"[模板数量] color: {len(color_templates)}")

    results = []

    for i in range(VOTE_FRAMES):
        final_results, position, facing = read_once(roi_cfg, color_thresholds, color_templates)

        coords7 = position + facing
        ok = tuple_is_valid(coords7)

        #print(f"\n===== 第 {i + 1}/{VOTE_FRAMES} 次识别 =====")
        out_parts = []
        for field_name in FIELDS:
            item = final_results[field_name]
            out_parts.append(
                f"{field_name}={item['text']} ({item['source']}, {item['score']:.3f})"
            )
        #print(" | ".join(out_parts))

        results.append({
            "final": final_results,
            "position": position,
            "facing": facing,
            "coords7": coords7 if ok else None
        })

        if i != VOTE_FRAMES - 1:
            time.sleep(VOTE_SLEEP)

    # 单帧直接返回
    if VOTE_FRAMES <= 1:
        r = results[0]
        return r["final"], r["position"], r["facing"]

    # 多帧投票：只在完整成功的结果中投票
    valid_results = [r for r in results if r["coords7"] is not None]
    if not valid_results:
        # 没有完整成功结果，就返回最后一次
        r = results[-1]
        return r["final"], r["position"], r["facing"]

    keys = [tuple(round(v, 6) for v in r["coords7"]) for r in valid_results]
    best_key, _ = Counter(keys).most_common(1)[0]

    for r in valid_results:
        key = tuple(round(v, 6) for v in r["coords7"])
        if key == best_key:
            return r["final"], r["position"], r["facing"]

    # 理论上不会到这里
    r = valid_results[0]
    return r["final"], r["position"], r["facing"]

# =========================
# 对外接口
# 成功返回 7 个值
# 失败返回 False
# =========================
def get_7coords():
    """
    成功:
        (pos_x, pos_y, pos_z, pos_w, face_x, face_z, face_w)
    失败:
        False
    """
    try:
        _, position, facing = read_with_vote()
        coords = position + facing

        if len(coords) != 7:
            return False

        if any(v is None for v in coords):
            return False

        return coords
    except Exception as e:
        print(f"[get_7coords] 调用失败: {e}")
        return False

# =========================
# 主程序测试入口
# =========================
def main():
    print("4 秒后截图，请切回游戏画面...")
    time.sleep(4)

    coords = get_7coords()

    print("\n===== 最终结果 =====")
    if coords is False:
        print(False)
    else:
        print(coords)

if __name__ == "__main__":
    main()
