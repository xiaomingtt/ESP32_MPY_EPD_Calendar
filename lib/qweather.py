import socket
import ssl
import deflate
import json
import time  

class QWeather:
    def __init__(self, api_key, location):
        self.host = "kd3md9kf37.re.qweatherapi.com"
        self.key = api_key
        self.location = location

    def _save_json(self, data, filename):
        """内部方法：将数据保存为JSON文件（默认覆盖已存在文件）"""
        try:
            # 'w' 模式会直接覆盖已存在的文件
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            #print(f"✅ 数据已覆盖保存至: {filename}")
        except Exception as e:
            print(f"❌ 保存文件失败: {e}")

    def _fetch(self, endpoint, prefix="/v7/weather", extra_params=None):
        """内部通用请求方法，含重试逻辑
        Args:
            endpoint (str): 接口端点 (如 'now', 'moon')
            prefix (str): API路径前缀 (默认 '/v7/weather', 天文类用 '/v7/astronomy')
            extra_params (dict): 额外的URL参数字典 (如 {'date': '20260312'})
        """
        # 1. 构建基础路径
        path = f"{prefix}/{endpoint}?location={self.location}&key={self.key}"
        
        # 2. 拼接额外参数 (如 date)
        if extra_params:
            for k, v in extra_params.items():
                path += f"&{k}={v}"

        max_retries = 5  # 定义最大重试次数

        for attempt in range(1, max_retries + 1):
            print(f"🔄 正在请求 {endpoint} (尝试 {attempt}/{max_retries})...")
            
            # --- 1. 解析地址 ---
            try:
                ai = socket.getaddrinfo(self.host, 443)
                addr = ai[0][-1]
            except Exception as e:
                print(f"❌ DNS解析失败: {e}")
                if attempt == max_retries: return None
                time.sleep(1)
                continue

            s = socket.socket()
            s.settimeout(10)
            
            try:
                # --- 2. 建立 SSL 连接 ---
                s.connect(addr)
                ss = ssl.wrap_socket(s, server_hostname=self.host)
                
                # --- 3. 发送 HTTP GET 请求 ---
                request = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {self.host}\r\n"
                    f"Accept-Encoding: gzip\r\n"
                    f"User-Agent: MicroPython_ESP32S3\r\n"
                    f"Connection: close\r\n\r\n"
                )
                ss.write(request.encode())
                
                # --- 4. 跳过 HTTP 响应头 ---
                while True:
                    line = ss.readline()
                    if not line or line == b"\r\n":
                        break
                
                # --- 5. 解压并解析 JSON ---
                with deflate.DeflateIO(ss, deflate.GZIP) as g:
                    data = json.load(g)
                
                print(f"✅ 请求 {endpoint} 成功！")
                return data  # 成功则直接返回，不进行后续重试

            except Exception as e:
                print(f"❌ 请求失败: {e}")
                if attempt == max_retries:
                    print(f"❌ 已达最大重试次数，放弃请求。")
                    return None
                print("💤 1秒后重试...")
                time.sleep(1) # 重试前等待
                
            finally:
                # 确保 socket 关闭
                try:
                    s.close()
                except:
                    pass

    def get_now(self, save_to=None):
        """获取实时天气"""
        data = self._fetch("now")
        if data and save_to:
            self._save_json(data, save_to)
        return data

    def get_hourly(self, save_to=None):
        """获取 24 小时逐小时预报"""
        data = self._fetch("24h")
        if data and save_to:
            self._save_json(data, save_to)
        return data

    def get_daily(self, save_to=None):
        """获取 3 天逐日预报"""
        data = self._fetch("3d")
        if data and save_to:
            self._save_json(data, save_to)
        return data

    def get_moon(self, date=None, save_to=None):
        """获取月相数据 (新增功能)
        Args:
            date (str): 日期，格式 YYYYMMDD，留空则自动获取今日
            save_to (str): 保存的文件名，如 'moon_phase.json'
        """
        # 如果未指定日期，自动生成今日日期 (需确保设备已通过NTP同步时间)
        if not date:
            try:
                t = time.localtime()
                date = f"{t[0]}{t[1]:02d}{t[2]:02d}"
                print(f"📅 自动使用今日日期: {date}")
            except:
                print("⚠️ 无法自动获取日期，请手动传入 date 参数 (格式: YYYYMMDD)")
                return None

        # 调用通用请求方法
        # 注意：月相接口的 prefix 是 /v7/astronomy 而不是 /v7/weather
        data = self._fetch(
            endpoint="moon", 
            prefix="/v7/astronomy", 
            extra_params={"date": date}
        )
        
        if data and save_to:
            self._save_json(data, save_to)
            
        return data


if __name__ == "__main__":
    # 初始化配置
    KEY = "******************************"
    # 支持经纬度字符串或城市ID字符串
    LOC = "0.059756,0.212771" 
    # 实例化对象
    weather = QWeather(KEY, LOC)
    
    moon_data = weather.get_moon(save_to="moon_phase.json") 
    now_data = weather.get_now(save_to="weather_now.json")
    

