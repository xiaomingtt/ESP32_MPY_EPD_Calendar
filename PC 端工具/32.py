import re
import os

# 配置路径 (你可以根据需要修改这里)
input_path = r"C:\Users\Administrator\Desktop\32.TXT"
output_path = r"C:\Users\Administrator\Desktop\font32.py"

def convert_font_universal():
    if not os.path.exists(input_path):
        print(f"错误：找不到文件 {input_path}")
        return

    # 尝试以 GBK 编码读取（取模软件常用）
    try:
        with open(input_path, "r", encoding="gbk") as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(input_path, "r", encoding="utf-8") as f:
            content = f.read()

    # 1. 匹配所有汉字
    chars = re.findall(r'/\*"(.*?)",', content)
    # 2. 按注释标签切割全文，获取数据块
    data_sections = re.split(r'/\*".*?",\d+\*/', content)

    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write("# MicroPython Font Library (Universal Bytes Format)\n")
        f_out.write("my_font_data_32 = {\n")
        
        for i, char in enumerate(chars):
            # 提取该字符对应的所有 0xXX 数据
            hex_values = re.findall(r'0x[0-9a-fA-F]{2}', data_sections[i])
            
            if hex_values:
                # 转换为 bytes 格式的十六进制字符串
                byte_str = "".join([f"\\x{int(h, 16):02x}" for h in hex_values])
                f_out.write(f"    '{char}': b'{byte_str}',  # {len(hex_values)} bytes\n")
        
        f_out.write("}\n")
    
    print(f"转换成功！共处理 {len(chars)} 个汉字。")
    print(f"结果已保存至: {output_path}")

if __name__ == "__main__":
    convert_font_universal()