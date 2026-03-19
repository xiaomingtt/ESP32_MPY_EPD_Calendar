import re
import os

# 配置路径
input_path = r"C:\Users\Administrator\Desktop\24.TXT"
output_path = r"C:\Users\Administrator\Desktop\font24.py"

def convert_24font():
    if not os.path.exists(input_path):
        print(f"错误：找不到文件 {input_path}")
        return

    # 注意：如果读取报错，尝试将 encoding 改为 'utf-8'
    with open(input_path, "r", encoding="gbk") as f:
        content = f.read()

    # 提取汉字和数据块
    chars = re.findall(r'/\*"(.*?)",', content)
    data_sections = re.split(r'/\*".*?",\d+\*/', content)

    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write("# MicroPython Font Library (24x24 Bytes Format)\n")
        f_out.write("my_font_data_24 = {\n")
        
        for i, char in enumerate(chars):
            hex_values = re.findall(r'0x[0-9a-fA-F]{2}', data_sections[i])
            
            if hex_values:
                # 24x24 应该是 72 个字节
                if len(hex_values) != 72:
                    print(f"警告：字符 '{char}' 的数据长度为 {len(hex_values)}，不是预期的 72")
                
                byte_str = "".join([f"\\x{int(h, 16):02x}" for h in hex_values])
                f_out.write(f"    '{char}': b'{byte_str}',\n")
        
        f_out.write("}\n")
    
    print(f"转换成功！24点阵字库已保存至: {output_path}")

if __name__ == "__main__":
    convert_24font()