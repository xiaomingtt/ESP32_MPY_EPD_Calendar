import re
import os

# 配置路径
input_path = r"C:\Users\Administrator\Desktop\12.TXT"  # 修改为12像素字模文件
output_path = r"C:\Users\Administrator\Desktop\font12.py"

def convert_file():
    if not os.path.exists(input_path):
        print(f"错误：找不到文件 {input_path}")
        return

    with open(input_path, "r", encoding="gbk") as f:  # 取模软件通常生成GBK编码，如报错请改为utf-8
        content = f.read()

    # 1. 提取所有汉字注释 (匹配 /*"汉字",编号*/)
    chars = re.findall(r'/\*"(.*?)",', content)
    
    # 2. 按注释切分内容，提取每个汉字对应的十六进制数据块
    data_sections = re.split(r'/\*".*?",\d+\*/', content)

    with open(output_path, "w", encoding="utf-8") as f_out:
        f_out.write("# MicroPython Font Library (12x12 Bytes Format)\n")
        f_out.write("# Each character uses 18 bytes (12 rows * 12 bits = 144 bits = 18 bytes)\n")
        f_out.write("my_font_data = {\n")
        
        for i, char in enumerate(chars):
            # 在对应的分段中找 0xXX 格式的十六进制数
            hex_values = re.findall(r'0x[0-9a-fA-F]{2}', data_sections[i])
            
            # 12x12汉字需要18字节 (12行 × 2字节/行 = 24字节？)
            # 注意：12像素点通常采用【每行2字节(16位)】存储，实际使用12位，高4位为0
            # 因此总字节数为 12行 × 2字节 = 24字节
            if hex_values:
                # 转换为 bytes 格式的字符串
                # 直接按实际提取的字节数转换（应为24字节）
                byte_str = "".join([f"\\x{int(h, 16):02x}" for h in hex_values])
                
                # 校验数据块大小（可选，用于调试）
                if len(hex_values) != 24:
                    print(f"警告：汉字'{char}'的数据长度异常（{len(hex_values)}字节），应为24字节")
                
                f_out.write(f"    '{char}': b'{byte_str}',\n")
        
        f_out.write("}\n")
    
    print(f"转换成功！结果已保存至: {output_path}")
    print(f"共转换 {len(chars)} 个汉字")

if __name__ == "__main__":
    convert_file()