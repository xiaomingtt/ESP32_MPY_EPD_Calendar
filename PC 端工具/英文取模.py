from PIL import Image, ImageFont, ImageDraw
import os

# --- 配置区 ---
# 建议选择电脑自带的等宽字体：Consolas (Windows) 或 Courier New
FONT_PATH = "C:\\Windows\\Fonts\\consola.ttf" 
CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz:.- " # 你需要的常用字符
SIZES = [16, 24, 32]
OUTPUT_FILE = r"C:\Users\Administrator\Desktop\font_ascii.py"

def generate_font_dict():
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("# 自动生成的 ASCII 等宽字库 (16, 24, 32)\n\n")
        
        for size in SIZES:
            f.write(f"font_ascii_{size} = {{\n")
            try:
                # 加载字体
                font = ImageFont.truetype(FONT_PATH, size)
            except:
                print(f"找不到字体文件: {FONT_PATH}")
                return

            for char in CHARS:
                # 创建黑白位图 (1位深度)
                # 等宽字体我们强制宽度和高度一致
                img = Image.new("1", (size, size), 0)
                draw = ImageDraw.Draw(img)
                
                # 计算居中偏移（可选，此处直接靠左上绘制）
                draw.text((0, 0), char, font=font, fill=1)
                
                # 获取像素数据并转为字节
                byte_data = []
                for y in range(size):
                    for x in range(0, size, 8):
                        byte = 0
                        for bit in range(8):
                            if x + bit < size:
                                if img.getpixel((x + bit, y)):
                                    byte |= (1 << (7 - bit)) # 高位在前
                        byte_data.append(byte)
                
                # 转为 b'\x00' 格式
                byte_str = "".join([f"\\x{b:02x}" for b in byte_data])
                # 转义特殊字符以便在字典中显示
                char_key = char if char != "'" else "\\'"
                f.write(f"    '{char_key}': b'{byte_str}',\n")
            
            f.write("}\n\n")
            print(f"已完成 {size}x{size} 字符集生成")

    print(f"\n大功告成！文件已保存至: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_font_dict()