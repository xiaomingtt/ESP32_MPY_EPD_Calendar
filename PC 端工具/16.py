import re
import os

# 配置路径
input_path = r"C:\Users\Administrator\Desktop\16.TXT"
output_path = r"C:\Users\Administrator\Desktop\font16.py"

def convert_file():
    if not os.path.exists(input_path):
        print(f"错误：找不到文件 {input_path}")
        return

    with open(input_path, "r", encoding="gbk") as f: # 取模软件通常生成GBK编码，如报错请改为utf-8
        content = f.read()

    # 1. 提取所有汉字注释 (匹配 /*"汉字",编号*/)
    chars = re.findall(r'/\*"(.*?)",', content)
    
    # 2. 按注释切分内容，提取每个汉字对应的十六进制数据块
    # 逻辑：将文本按注释分割，每一段的前面部分就是对应的0x数据
    data_sections = re.split(r'/\*".*?",\d+\*/', content)

    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write("# MicroPython Font Library (16x16 Bytes Format)\n")
        f_out.write("my_font_data = {\n")
        
        for i, char in enumerate(chars):
            # 在对应的分段中找 0xXX 格式的十六进制数
            hex_values = re.findall(r'0x[0-9a-fA-F]{2}', data_sections[i])
            
            if hex_values:
                # 转换为 bytes 格式的字符串，例如 \x00\xff
                byte_str = "".join([f"\\x{int(h, 16):02x}" for h in hex_values])
                f_out.write(f"    '{char}': b'{byte_str}',\n")
        
        f_out.write("}\n")
    
    print(f"转换成功！结果已保存至: {output_path}")

if __name__ == "__main__":
    convert_file()