from PIL import Image
import time
from pathlib import Path

# ==============================================  核心配置区 ==============================================
# 文件夹路径（将需要批量转换的图片放入此文件夹）
INPUT_FOLDER = Path(r"C:\Users\Administrator\Desktop\新建文件夹")
# 输出文件路径（所有图片数据将存入此文件）
OUTPUT_FILE = Path(r"C:\Users\Administrator\Desktop\image_data.py")

# 黑色判断阈值 (0-255)，低于此值判定为黑色
BLACK_LUMINANCE_THRESHOLD = 60
# 是否反转黑白 (True/False)
INVERT_BLACK_WHITE = False
# =======================================================================================================

def calculate_luminance(r: int, g: int, b: int) -> float:
    """计算人眼感知亮度"""
    return 0.299 * r + 0.587 * g + 0.114 * b

def preprocess_image(input_path: Path) -> Image.Image:
    """图片预处理：处理透明通道、转为RGB"""
    if not input_path.exists():
        raise FileNotFoundError(f"图片不存在: {input_path}")
    
    try:
        img = Image.open(input_path)
    except Exception as e:
        raise RuntimeError(f"图片打开失败: {e}")

    # 处理透明通道（透明区域转为白色）
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        alpha = img.convert("RGBA").split()[-1]
        bg = Image.new("RGBA", img.size, (255, 255, 255, 255))
        bg.paste(img, mask=alpha)
        img = bg.convert("RGB")
    else:
        img = img.convert("RGB")

    return img

def process_black_plane(img: Image.Image) -> Image.Image:
    """将图片转换为纯黑白图层（1位像素）"""
    img_width, img_height = img.size
    
    # 初始化图层：1=白色，0=黑色
    black_plane = Image.new("1", (img_width, img_height), 1)
    img_pixels = img.load()
    bw_pixels = black_plane.load()

    for y in range(img_height):
        for x in range(img_width):
            r, g, b = img_pixels[x, y]
            lum = calculate_luminance(r, g, b)
            
            # 根据亮度判断是否为黑色
            if lum < BLACK_LUMINANCE_THRESHOLD:
                bw_pixels[x, y] = 0  # 黑色
            else:
                bw_pixels[x, y] = 1  # 白色

    # 黑白反转处理
    if INVERT_BLACK_WHITE:
        inverted_bw = Image.new("1", (img_width, img_height), 0)
        inv_bw_pixels = inverted_bw.load()
        for y in range(img_height):
            for x in range(img_width):
                inv_bw_pixels[x, y] = 1 if bw_pixels[x, y] == 0 else 0
        black_plane = inverted_bw

    return black_plane

def image_to_buffer(img: Image.Image) -> bytearray:
    """
    将图片转换为 SSD1683 兼容的字节数组 (MONO_HLSB, 高位在前)
    0 = 黑色，1 = 白色
    """
    img_width, img_height = img.size
    pixels = img.load()
    buffer_size = (img_width * img_height) // 8
    buffer = bytearray(buffer_size)

    for y in range(img_height):
        for x in range(img_width):
            index = x + y * img_width
            byte_index = index >> 3
            bit_index = 7 - (index & 0x07)

            if pixels[x, y] == 0:
                buffer[byte_index] &= ~(1 << bit_index) # 黑色置0
            else:
                buffer[byte_index] |= (1 << bit_index)    # 白色置1

    return buffer

def save_data_dict(data_dict: dict, output_path: Path):
    """
    将所有图片数据以字典格式保存到一个 Python 文件中
    格式：{ "文件名": bytearray([...]), "文件名2": bytearray([...]) }
    """
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# SSD1683 墨水屏图片数据字典\n")
        f.write(f"# 生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"# 黑白阈值: {BLACK_LUMINANCE_THRESHOLD}\n\n")
        f.write("image_data = {\n")
        
        for img_name, buffer in data_dict.items():
            f.write(f'    "{img_name}": bytearray([\n')
            # 每16个字节换一行，方便阅读
            for i in range(0, len(buffer), 16):
                chunk = buffer[i:i+16]
                hex_str = ", ".join(f"0x{b:02X}" for b in chunk)
                f.write(f"        {hex_str},\n")
            f.write("    ]),\n")
        
        f.write("}\n")
    print(f"✅ 所有数据已保存至: {output_path.absolute()}")

def main():
    start_time = time.time()
    print("="*60)
    print(f"SSD1683 黑白图片批量取模工具")
    print("="*60)

    # 1. 检查输入文件夹
    if not INPUT_FOLDER.exists() or not INPUT_FOLDER.is_dir():
        print(f"❌ 错误：文件夹不存在 -> {INPUT_FOLDER.absolute()}")
        return

    # 2. 获取所有图片文件
    supported_exts = (".png", ".jpg", ".jpeg", ".bmp")
    image_files = [f for f in INPUT_FOLDER.iterdir() if f.is_file() and f.suffix.lower() in supported_exts]

    if not image_files:
        print(f"❌ 错误：在文件夹中未找到图片 (支持格式: {', '.join(supported_exts)})")
        return

    print(f"📂 发现 {len(image_files)} 张图片，开始处理...\n")

    all_data = {}
    success_count = 0

    # 3. 批量处理
    for img_path in image_files:
        try:
            print(f"[{success_count + 1}/{len(image_files)}] 正在处理: {img_path.name}")
            
            # 预处理
            img = preprocess_image(img_path)
            w, h = img.size

            # 校验宽度（SSD1683要求宽度为8的倍数）
            if w % 8 != 0:
                print(f"   ⚠️  跳过：宽度 {w} 不是8的倍数")
                continue

            # 转黑白图层
            bw_img = process_black_plane(img)
            
            # 取模
            buffer = image_to_buffer(bw_img)
            
            # 存入字典 (Key为不含后缀的文件名)
            file_key = img_path.stem
            all_data[file_key] = buffer
            
            print(f"   ✅ 完成 -> Key: {file_key}, 尺寸: {w}x{h}, 大小: {len(buffer)}字节")
            success_count += 1

        except Exception as e:
            print(f"   ❌ 失败: {e}")
            continue

    # 4. 保存最终文件
    if all_data:
        print(f"\n💾 正在生成总文件...")
        save_data_dict(all_data, OUTPUT_FILE)
        
        print("\n" + "="*60)
        print(f"🎉 全部完成！")
        print(f"⏱️  总耗时: {time.time() - start_time:.2f}秒")
        print(f"📊 成功转换: {success_count}/{len(image_files)} 张")
        print(f"📖 使用方法: 在ESP32代码中 import image_data, 然后通过 image_data['文件名'] 调用")
        print("="*60)
    else:
        print("\n❌ 没有图片被成功转换。")

if __name__ == "__main__":
    main()