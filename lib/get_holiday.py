import urequests
import ujson
import network
import time  


MAX_RETRIES = 5       # 最大重试次数
RETRY_DELAY = 2       # 每次重试间隔（秒）
# ----------------

def save_holidays_to_flash(year):
    """
    获取指定年份的节假日数据并保存到Flash（带重试功能）
    
    Args:
        year (int): 年份，如 2026
    """
    # 1. 检查年份格式
    if not isinstance(year, int) or len(str(year)) != 4:
        print("错误：年份必须是4位整数")
        return

    # 2. 构建API URL
    url = f"http://api.jiejiariapi.com/v1/holidays/{year}"
    filename = f"holidays_{year}.json"

    response = None # 初始化response变量，防止未定义就关闭
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            print(f"正在请求 (尝试 {attempt}/{MAX_RETRIES}): {url}")
            
            # 3. 发送HTTP请求
            response = urequests.get(url, timeout=10) # 建议增加timeout
            
            if response.status_code == 200:
                print("请求成功，正在解析数据...")
                
                # 4. 解析JSON数据
                holiday_data = response.json()
                
                # 5. 保存到Flash文件
                with open(filename, 'w') as f: 
                    ujson.dump(holiday_data, f)
                
                print(f"成功！数据已保存为: {filename}")
                break # 成功则跳出重试循环
            
            else:
                print(f"请求失败，HTTP状态码: {response.status_code}")
                # 只有服务器错误(5xx)才重试，客户端错误(4xx)通常重试无效
                if 500 <= response.status_code < 600 and attempt < MAX_RETRIES:
                    print(f"服务器异常，{RETRY_DELAY * attempt}秒后重试...")
                    time.sleep(RETRY_DELAY * attempt)
                else:
                    break # 客户端错误或不再重试

        except Exception as e:
            print(f"发生网络错误: {e}")
            if attempt < MAX_RETRIES:
                print(f"{RETRY_DELAY * attempt}秒后重试...")
                time.sleep(RETRY_DELAY * attempt)
            else:
                print("已达到最大重试次数，放弃请求。")
                
        finally:
            # 确保每次请求后都关闭连接，释放内存
            if response:
                response.close()
                response = None

if __name__ == "__main__":
    # 这里的年份可以根据需要修改，比如结合你的RTC时钟获取当前年份
    save_holidays_to_flash(2025)