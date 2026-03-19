from PIL import Image, ImageEnhance
import time
from pathlib import Path
import numpy as np

# ==============================================  核心配置区 ==============================================
# 屏幕硬件参数（SSD1683 400*300固定）
EPD_WIDTH = 400
EPD_HEIGHT = 300

# 文件路径
INPUT_IMAGE_PATH = Path(r"C:\Users\Administrator\Desktop\OIP-C.webp")  
OUTPUT_FOLDER = Path(r"C:\Users\Administrator\Desktop")

# 输出配置
OUTPUT_PYTHON_FILE = True
OUTPUT_C_HEADER_FILE = False
SAVE_INTERMEDIATE_BMP = False  
SAVE_SCREEN_PREVIEW = True 
SAVE_PREPROCESSED_IMG = True   # 保存预处理后的图片，方便调试

# 黑白极性开关
INVERT_BLACK_WHITE = False

# 图片缩放模式
RESIZE_MODE = "stretch"  # stretch/crop/pad

# =====================  颜色识别核心参数（全彩图通用） =====================
# 黑色判断：亮度低于该值判定为黑色（0-255）
BLACK_LUMINANCE_THRESHOLD = 45
# 黑色二级阈值：低于该值强制为黑，高于该值按亮度映射
BLACK_FORCE_THRESHOLD = 20

# 红色HSV双区间判断（覆盖正红、橙红、紫红）
RED_HUE_RANGE1 = (0, 25)    # 正红→橙红区间
RED_HUE_RANGE2 = (340, 360) # 紫红区间
RED_SAT_MIN = 40             # 饱和度下限（0-255，越低越容易识别暗红）
RED_VAL_MIN = 40             # 亮度下限（0-255，越低越容易识别暗部红）
# 红色LAB通道判断（抗亮度干扰，识别暗部红）
RED_A_CHANNEL_MIN = 10       # LAB a通道（红-绿）下限，越大越严格

# 防白色误判红线：G+B通道超过该值，绝对不判定为红色
WHITE_GB_THRESHOLD = 480     # 白色G+B≈510，超过直接排除

# =====================  全彩图优化功能开关 =====================
ENABLE_PREPROCESS = True     # 开启图片预处理（全彩图必须开）
ENABLE_DITHER = True          # 开启三色抖动（渐变/照片必须开）
DITHER_STRENGTH = 0.8         # 抖动强度0.1-1.0，照片建议0.6-0.9
# =========================================================================================================

# =====================  工具函数 =====================
def rgb2lab(r, g, b):
    """RGB转LAB颜色空间，用于抗亮度干扰的红色识别"""
    # 归一化
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0

    # 伽马校正
    r = pow(r, 2.2) if r > 0.04045 else r / 12.92
    g = pow(g, 2.2) if g > 0.04045 else g / 12.92
    b = pow(b, 2.2) if b > 0.04045 else b / 12.92

    # XYZ转换
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9503

    # 归一化到D65白点
    x /= 0.95047
    y /= 1.0
    z /= 1.08883

    # 非线性转换
    def f(t):
        return pow(t, 1/3) if t > 0.008856 else (7.787 * t) + 16/116

    fx = f(x)
    fy = f(y)
    fz = f(z)

    # 计算LAB
    l = 116 * fy - 16
    a = 500 * (fx - fy)
    b_val = 200 * (fy - fz)

    return l, a, b_val

def calculate_luminance(r, g, b):
    """ITU-R BT.601亮度公式"""
    return 0.299 * r + 0.587 * g + 0.114 * b

def preprocess_image(img: Image.Image) -> Image.Image:
    """全彩图预处理：适配三色屏，拉大红黑对比，强化红色，降噪"""
    # 1. 对比度增强，拉开黑/白/红的差距
    contrast_enhancer = ImageEnhance.Contrast(img)
    img = contrast_enhancer.enhance(1.3)

    # 2. 饱和度增强，提升红色系辨识度
    color_enhancer = ImageEnhance.Color(img)
    img = color_enhancer.enhance(1.2)

    # 3. 轻微锐化，保留边缘细节
    sharp_enhancer = ImageEnhance.Sharpness(img)
    img = sharp_enhancer.enhance(1.1)

    # 4. 轻微高斯模糊降噪，避免抖动后出现杂色噪点
    img = img.filter(ImageFilter.GaussianBlur(radius=0.5))

    return img

def three_color_quantize_dither(img: Image.Image,
                                red_boost=1.15,
                                dither_strength=0.85):
    """
    基于颜色距离的三色量化 + Floyd-Steinberg误差扩散
    red_boost: 红色权重增强系数（1.0-1.3推荐）
    dither_strength: 抖动强度（0.6-0.9推荐）
    """

    img_np = np.array(img, dtype=np.float32)
    height, width = img_np.shape[:2]

    # 定义三种真实屏幕颜色
    EPD_WHITE = np.array([255, 255, 255], dtype=np.float32)
    EPD_BLACK = np.array([0, 0, 0], dtype=np.float32)
    EPD_RED   = np.array([180, 0, 0], dtype=np.float32)

    palette = [EPD_BLACK, EPD_WHITE, EPD_RED]

    # 输出标签图（0=黑,1=白,2=红）
    label_map = np.zeros((height, width), dtype=np.uint8)

    for y in range(height):
        for x in range(width):
            old_pixel = img_np[y, x]

            # ---- 计算到三色的加权欧氏距离 ----
            distances = []

            for idx, color in enumerate(palette):
                diff = old_pixel - color

                # 红色通道权重增强（让红更容易被选中）
                weight = np.array([red_boost, 1.0, 1.0])
                dist = np.sum((diff * weight) ** 2)

                distances.append(dist)

            nearest_index = np.argmin(distances)
            new_pixel = palette[nearest_index]

            label_map[y, x] = nearest_index

            # ---- 误差扩散 ----
            error = (old_pixel - new_pixel) * dither_strength

            if x + 1 < width:
                img_np[y, x+1] += error * 7/16
            if x - 1 >= 0 and y + 1 < height:
                img_np[y+1, x-1] += error * 3/16
            if y + 1 < height:
                img_np[y+1, x] += error * 5/16
            if x + 1 < width and y + 1 < height:
                img_np[y+1, x+1] += error * 1/16

            img_np[y, x] = new_pixel

    img_np = np.clip(img_np, 0, 255).astype(np.uint8)
    quantized_img = Image.fromarray(img_np)

    return quantized_img, label_map

def labelmap_to_planes(label_map):
    height, width = label_map.shape

    bw_plane = Image.new("1", (width, height), 1)
    red_plane = Image.new("1", (width, height), 0)

    bw_pixels = bw_plane.load()
    red_pixels = red_plane.load()

    for y in range(height):
        for x in range(width):
            label = label_map[y, x]

            if label == 0:      # 黑
                bw_pixels[x, y] = 0
                red_pixels[x, y] = 0
            elif label == 1:    # 白
                bw_pixels[x, y] = 1
                red_pixels[x, y] = 0
            else:               # 红
                bw_pixels[x, y] = 0
                red_pixels[x, y] = 1

    return bw_plane, red_plane
    
def get_hue(r, g, b):
    """获取RGB像素的色相值(0-360)"""
    r_norm, g_norm, b_norm = r/255.0, g/255.0, b/255.0
    max_c = max(r_norm, g_norm, b_norm)
    min_c = min(r_norm, g_norm, b_norm)
    delta = max_c - min_c

    if delta == 0:
        return 0
    elif max_c == r_norm:
        h = (60 * ((g_norm - b_norm)/delta) + 360) % 360
    elif max_c == g_norm:
        h = 60 * ((b_norm - r_norm)/delta) + 120
    else:
        h = 60 * ((r_norm - g_norm)/delta) + 240
    return h

# =====================  核心处理函数 =====================
def load_and_resize_image(input_path: Path) -> Image.Image:
    """图片加载、缩放、透明通道处理"""
    if not input_path.exists():
        raise FileNotFoundError(f"图片文件不存在: {input_path.absolute()}")
    
    try:
        img = Image.open(input_path)
    except Exception as e:
        raise RuntimeError(f"图片打开失败: {e}")

    # 处理透明通道，透明区域转为白色
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        alpha = img.convert("RGBA").split()[-1]
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.paste(img, mask=alpha)
        img = bg.convert("RGB")
    else:
        img = img.convert("RGB")

    # 缩放适配
    orig_w, orig_h = img.size
    if RESIZE_MODE == "stretch":
        img = img.resize((EPD_WIDTH, EPD_HEIGHT), Image.Resampling.NEAREST)
    elif RESIZE_MODE == "crop":
        ratio = max(EPD_WIDTH / orig_w, EPD_HEIGHT / orig_h)
        new_w, new_h = int(orig_w * ratio), int(orig_h * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        left = (new_w - EPD_WIDTH) // 2
        top = (new_h - EPD_HEIGHT) // 2
        img = img.crop((left, top, left + EPD_WIDTH, top + EPD_HEIGHT))
    elif RESIZE_MODE == "pad":
        ratio = min(EPD_WIDTH / orig_w, EPD_HEIGHT / orig_h)
        new_w, new_h = int(orig_w * ratio), int(orig_h * ratio)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        bg = Image.new("RGB", (EPD_WIDTH, EPD_HEIGHT), (255, 255, 255))
        left = (EPD_WIDTH - new_w) // 2
        top = (EPD_HEIGHT - new_h) // 2
        bg.paste(img, (left, top))
        img = bg

    return img

def split_color_planes(img: Image.Image) -> tuple[Image.Image, Image.Image, dict]:
    """
    严格对齐SSD1683规格书，HSV+LAB双空间颜色分类
    映射规则：
    | 屏幕颜色 | 黑白层PIL像素 | 红层PIL像素 | 黑白RAM位 | 红RAM位 |
    |----------|---------------|-------------|-----------|---------|
    | 黑色     | 0             | 0           | 0         | 0       |
    | 白色     | 1             | 0           | 1         | 0       |
    | 红色     | 0             | 1           | 0         | 1       |
    """
    # 初始化图层
    black_plane = Image.new("1", (EPD_WIDTH, EPD_HEIGHT), 1)
    red_plane = Image.new("1", (EPD_WIDTH, EPD_HEIGHT), 0)
    
    img_pixels = img.load()
    bw_pixels = black_plane.load()
    red_pixels = red_plane.load()

    stats = {"black": 0, "red": 0, "white": 0, "total": EPD_WIDTH * EPD_HEIGHT}

    for y in range(EPD_HEIGHT):
        for x in range(EPD_WIDTH):
            r, g, b = img_pixels[x, y]
            lum = calculate_luminance(r, g, b)
            h = get_hue(r, g, b)
            _, a, _ = rgb2lab(r, g, b)

            # 1. 强制黑色：极暗区域直接判定为黑
            if lum < BLACK_FORCE_THRESHOLD:
                bw_pixels[x, y] = 0
                red_pixels[x, y] = 0
                stats["black"] += 1
                continue

            # 2. 双空间红色判断，杜绝白色误判
            is_red = (
                # HSV色相在红色区间
                (RED_HUE_RANGE1[0] <= h <= RED_HUE_RANGE1[1] or RED_HUE_RANGE2[0] <= h <= RED_HUE_RANGE2[1])
                # LAB a通道足够红
                and a >= RED_A_CHANNEL_MIN
                # 饱和度和亮度达标
                and (r - g) >= (RED_CHANNEL_GAP if 'RED_CHANNEL_GAP' in globals() else 20)
                and (r - b) >= (RED_CHANNEL_GAP if 'RED_CHANNEL_GAP' in globals() else 20)
                and r >= RED_VAL_MIN
                # 防白色误判红线
                and (g + b) < WHITE_GB_THRESHOLD
            )

            if is_red:
                bw_pixels[x, y] = 0
                red_pixels[x, y] = 1
                stats["red"] += 1
                continue

            # 3. 普通黑色判断
            if lum < BLACK_LUMINANCE_THRESHOLD:
                bw_pixels[x, y] = 0
                red_pixels[x, y] = 0
                stats["black"] += 1
                continue

            # 4. 剩余全部为白色，红层强制为0
            bw_pixels[x, y] = 1
            red_pixels[x, y] = 0
            stats["white"] += 1

    # 黑白极性反转
    if INVERT_BLACK_WHITE:
        inverted_bw = Image.new("1", (EPD_WIDTH, EPD_HEIGHT), 0)
        inv_bw_pixels = inverted_bw.load()
        for y in range(EPD_HEIGHT):
            for x in range(EPD_WIDTH):
                inv_bw_pixels[x, y] = 1 if bw_pixels[x, y] == 0 else 0
        black_plane = inverted_bw
        stats["black"], stats["white"] = stats["white"], stats["black"]

    return black_plane, red_plane, stats

def image_to_epd_buffer(img: Image.Image) -> bytearray:
    pixels = img.load()
    buffer_size = (EPD_WIDTH * EPD_HEIGHT) // 8
    buffer = bytearray(buffer_size)

    for y in range(EPD_HEIGHT):
        for x in range(EPD_WIDTH):
            index = x + y * EPD_WIDTH
            byte_index = index >> 3
            bit_index = 7 - (index & 0x07)

            if pixels[x, y] == 0:
                buffer[byte_index] &= ~(1 << bit_index)
            else:
                buffer[byte_index] |= (1 << bit_index)

    if len(buffer) != buffer_size:
        raise RuntimeError(f"Buffer长度错误: 预期{buffer_size}字节，实际{len(buffer)}字节")
    return buffer

def save_output_files(bw_buf: bytearray, red_buf: bytearray, bw_plane: Image.Image, red_plane: Image.Image, stats: dict, process_time: float, preprocessed_img: Image.Image = None):
    """保存所有输出文件"""
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

    # 保存预处理后的图片
    if SAVE_PREPROCESSED_IMG and preprocessed_img is not None:
        pre_path = OUTPUT_FOLDER / "preprocessed_image.png"
        preprocessed_img.save(pre_path)
        print(f"✅ 已保存预处理图片: {pre_path.absolute()}")

    # 保存Python数组
    if OUTPUT_PYTHON_FILE:
        py_path = OUTPUT_FOLDER / "epd_image_data.py"
        with open(py_path, "w", encoding="utf-8") as f:
            f.write(f"# SSD1683 400*300 红黑白墨水屏图像数据\n")
            f.write(f"# 生成时间: {timestamp}\n")
            f.write(f"# 分辨率: {EPD_WIDTH} * {EPD_HEIGHT}\n")
            f.write(f"# 像素统计: 黑色{stats['black']}个, 红色{stats['red']}个, 白色{stats['white']}个\n\n")
            
            f.write("# 黑白图层数据 (写入0x24 BW RAM)\n")
            f.write("bw_ram_data = bytearray([\n")
            for i in range(0, len(bw_buf), 16):
                line = ", ".join(f"0x{b:02X}" for b in bw_buf[i:i+16])
                f.write(f"    {line},\n")
            f.write("])\n\n")

            f.write("# 红色图层数据 (写入0x26 RED RAM)\n")
            f.write("red_ram_data = bytearray([\n")
            for i in range(0, len(red_buf), 16):
                line = ", ".join(f"0x{b:02X}" for b in red_buf[i:i+16])
                f.write(f"    {line},\n")
            f.write("])\n")
        print(f"✅ 已生成Python数组文件: {py_path.absolute()}")

    # 保存C语言头文件
    if OUTPUT_C_HEADER_FILE:
        h_path = OUTPUT_FOLDER / "epd_image_data.h"
        with open(h_path, "w", encoding="utf-8") as f:
            f.write(f"/* SSD1683 400*300 红黑白墨水屏图像数据 */\n")
            f.write(f"/* 生成时间: {timestamp} */\n")
            f.write(f"/* 分辨率: {EPD_WIDTH} * {EPD_HEIGHT} */\n\n")
            f.write("#ifndef __EPD_IMAGE_DATA_H\n")
            f.write("#define __EPD_IMAGE_DATA_H\n\n")
            f.write(f"#define EPD_WIDTH {EPD_WIDTH}\n")
            f.write(f"#define EPD_HEIGHT {EPD_HEIGHT}\n\n")

            f.write("/* 黑白图层数据 (写入0x24 BW RAM) */\n")
            f.write("const unsigned char bw_ram_data[] = {\n")
            for i in range(0, len(bw_buf), 16):
                line = ", ".join(f"0x{b:02X}" for b in bw_buf[i:i+16])
                f.write(f"    {line},\n")
            f.write("};\n\n")

            f.write("/* 红色图层数据 (写入0x26 RED RAM) */\n")
            f.write("const unsigned char red_ram_data[] = {\n")
            for i in range(0, len(red_buf), 16):
                line = ", ".join(f"0x{b:02X}" for b in red_buf[i:i+16])
                f.write(f"    {line},\n")
            f.write("};\n\n")
            f.write("#endif // __EPD_IMAGE_DATA_H\n")
        print(f"✅ 已生成C语言头文件: {h_path.absolute()}")

    # 保存中间BMP
    if SAVE_INTERMEDIATE_BMP:
        bw_bmp_path = OUTPUT_FOLDER / "black_plane.bmp"
        red_bmp_path = OUTPUT_FOLDER / "red_plane.bmp"
        bw_plane.save(bw_bmp_path)
        red_plane.save(red_bmp_path)
        print(f"✅ 已保存黑白图层: {bw_bmp_path.absolute()}")
        print(f"✅ 已保存红色图层: {red_bmp_path.absolute()}")

    # 生成屏幕预览图
    if SAVE_SCREEN_PREVIEW:
        preview = Image.new("RGB", (EPD_WIDTH, EPD_HEIGHT), (255, 255, 255))
        preview_pixels = preview.load()
        bw_pixels = bw_plane.load()
        red_pixels = red_plane.load()

        for y in range(EPD_HEIGHT):
            for x in range(EPD_WIDTH):
                bw_val = bw_pixels[x, y]
                red_val = red_pixels[x, y]
                if red_val == 1:
                    preview_pixels[x, y] = (255, 0, 0)
                elif bw_val == 0:
                    preview_pixels[x, y] = (0, 0, 0)
                else:
                    preview_pixels[x, y] = (255, 255, 255)
        
        preview_path = OUTPUT_FOLDER / "screen_preview.png"
        preview.save(preview_path, dpi=(300, 300))
        print(f"✅ 已生成屏幕预览图: {preview_path.absolute()}")

# =====================  主函数 =====================
def main():
    # 提前导入ImageFilter，避免运行时报错
    from PIL import ImageFilter
    global ImageFilter

    start_time = time.time()
    print("="*60)
    print(f"SSD1683 全彩图片优化版处理工具")
    print("="*60)

    try:
        # 分辨率校验
        if EPD_WIDTH % 8 != 0:
            raise ValueError(f"SSD1683要求宽度必须是8的整数倍，当前宽度: {EPD_WIDTH}")
        
        # 1. 加载和缩放图片
        print(f"📷 正在加载图片: {INPUT_IMAGE_PATH.absolute()}")
        img = load_and_resize_image(INPUT_IMAGE_PATH)

        # 2. 图片预处理
        preprocessed_img = None
        if ENABLE_PREPROCESS:
            print("🎨 正在执行全彩图预处理...")
            img = preprocess_image(img)
            preprocessed_img = img

        # 3. 三色抖动处理
        if ENABLE_DITHER:
            print("🔶 正在执行三色抖动优化...")
            #img = three_color_dither(img)
            quant_img, label_map = three_color_quantize_dither(img)
            stats = {
                "black": np.sum(label_map == 0),
                "white": np.sum(label_map == 1),
                "red":   np.sum(label_map == 2),
                "total": label_map.size
            }

        # 4. 拆分颜色图层
        print("📦 正在拆分颜色图层...")
        #bw_plane, red_plane, stats = split_color_planes(img)
        bw_plane, red_plane = labelmap_to_planes(label_map)

        # 5. 生成取模数据
        print("🔢 正在生成墨水屏取模数据...")
        bw_buf = image_to_epd_buffer(bw_plane)
        red_buf = image_to_epd_buffer(red_plane)

        # 6. 保存文件
        print("💾 正在保存输出文件...")
        process_time = time.time() - start_time
        save_output_files(bw_buf, red_buf, bw_plane, red_plane, stats, process_time, preprocessed_img)

        # 输出统计
        print("\n" + "="*60)
        print("✅ 全彩图优化处理完成！")
        print(f"⏱️  总耗时: {process_time:.3f}秒")
        print(f"📊 像素统计:")
        print(f"   黑色像素: {stats['black']} ({stats['black']/stats['total']*100:.1f}%)")
        print(f"   红色像素: {stats['red']} ({stats['red']/stats['total']*100:.1f}%)")
        print(f"   白色像素: {stats['white']} ({stats['white']/stats['total']*100:.1f}%)")
        print("="*60)
        print("⚠️  驱动写入要求:")
        print("   bw_ram_data → 写入SSD1683 0x24命令 (BW RAM)")
        print("   red_ram_data → 写入SSD1683 0x26命令 (RED RAM)")
        print("   渐变/照片图建议使用全屏刷新，避免残影")
        print("="*60)

    except Exception as e:
        print(f"❌ 处理失败: {e}")
        exit(1)

if __name__ == "__main__":
    main()