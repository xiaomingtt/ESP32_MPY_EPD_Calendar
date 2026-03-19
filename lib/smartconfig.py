# smartconfig.py
import network
import utime
import json
import socket
import gc
from microWebSrv import MicroWebSrv
from machine import Pin

CONFIG_FILE = "wifi_config.json"


class _DNSServer:
    def __init__(self, ip):
        self.ip = ip
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.sock.bind(('', 53))
        self.running = True

    def process(self):
        if not self.running:
            return
        try:
            data, addr = self.sock.recvfrom(1024)
            if data:
                packet = data[:2] + b'\x81\x80'
                packet += data[4:6] + data[4:6] + b'\x00\x00\x00\x00'
                packet += data[12:]
                packet += b'\xc0\x0c'
                packet += b'\x00\x01\x00\x01\x00\x00\x00\x3c\x00\x04'
                packet += bytes(map(int, self.ip.split('.')))
                self.sock.sendto(packet, addr)
        except:
            pass

    def stop(self):
        self.running = False
        self.sock.close()


class _WiFiManager:

    def __init__(self):
        self.sta = network.WLAN(network.STA_IF)
        self.ap = network.WLAN(network.AP_IF)
        self.mws = None
        self.dns = None
        self.status = "idle"
        self.target_ssid = None
        self.target_pwd = None
        
        # 确保 WiFi 处于初始状态
        self.sta.active(False)
        self.ap.active(False)

        self.led = Pin(48, Pin.OUT)
        self.led.value(0)

        self.led_mode = "off"   # off / blink / on
        self._last_toggle = 0
        self._led_state = 0
            
    def _led_update(self):
        now = utime.ticks_ms()

        if self.led_mode == "blink":
            if utime.ticks_diff(now, self._last_toggle) > 250:
                self._last_toggle = now
                self._led_state = 1 - self._led_state
                self.led.value(self._led_state)
        elif self.led_mode == "on":
            self.led.value(1)
        else:
            self.led.value(0)

    def try_auto_connect(self, timeout=8):
        try:
            with open(CONFIG_FILE, "r") as f:
                cfg = json.load(f)
        except:
            return False

        print("尝试连接已保存 WiFi:", cfg["ssid"])

        self.sta.active(True)
        self.sta.connect(cfg["ssid"], cfg["password"])

        for _ in range(timeout):
            if self.sta.isconnected():
                print("已连接:", self.sta.ifconfig())
                return True
            utime.sleep(1)

        print("自动连接失败")
        self.sta.active(False) # 断开并关闭，为配网模式做准备
        return False

    def start_config(self):
        self.ap.active(True)
        self.ap.config(essid="ESP32_Config", authmode=network.AUTH_OPEN)

        ip = self.ap.ifconfig()[0]
        print("AP IP:", ip)

        self.dns = _DNSServer(ip)
        self.led_mode = "blink"
        
        routes = [
            ("/", "GET", self._root),
            ("/config", "POST", self._config),
            ("/status", "GET", self._status),
            ("/generate_204", "GET", self._root),
            ("/hotspot-detect.html", "GET", self._root),
            ("/ncsi.txt", "GET", self._root),
            ("*", "GET", self._root),
        ]

        self.mws = MicroWebSrv(routeHandlers=routes)
        self.mws.Start(threaded=True)

        print("进入配网模式，等待连接...")

        # 用于确保 connect 只被调用一次的标志
        connection_attempted = False

        while True:
            self.dns.process()
            self._led_update()

            # --- 核心修改：连接逻辑移至主循环 ---
            if self.status == "connecting":
                # 1. 确保 STA 接口已激活
                if not self.sta.active():
                    print("主循环：激活 STA 接口")
                    self.sta.active(True)
                    utime.sleep_ms(100)

                # 2. 发起连接（且仅发起一次）
                if not connection_attempted:
                    print(f"主循环：正在连接 {self.target_ssid}...")
                    try:
                        self.sta.connect(self.target_ssid, self.target_pwd)
                        connection_attempted = True
                    except Exception as e:
                        print("连接异常:", e)
                        # 这里可以选择重置状态，或者等待重试
                        pass

                # 3. 检查是否连接成功
                if self.sta.isconnected():
                    print("连接成功:", self.sta.ifconfig())
                    with open(CONFIG_FILE, "w") as f:
                        json.dump({
                            "ssid": self.target_ssid,
                            "password": self.target_pwd
                        }, f)
                    self._enter_normal()
                    return

            utime.sleep_ms(50)

    def _enter_normal(self):
        print("关闭 AP，进入正常模式")
        self.led_mode = "on"
        
        if self.dns:
            self.dns.stop()

        if self.mws:
            self.mws.Stop()

        self.ap.active(False)

    def scan_wifi(self):
        self.sta.active(True)
        # 稍微等待扫描准备
        utime.sleep_ms(200)
        nets = self.sta.scan()
        html = ""
        for n in nets:
            ssid = n[0].decode()
            rssi = n[3]
            if ssid:
                html += f'<option value="{ssid}">{ssid} (信号:{rssi})</option>'
        return html
    
    # =============================
    # 页面处理
    # =============================
    def _root(self, httpClient, httpResponse):
        wifi_list = self.scan_wifi()

        html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <title>ESP32 配网</title>
                <style>
                body{{font-family:sans-serif;margin:20px}}
                input,select{{width:100%;padding:8px;margin:6px 0}}
                button{{padding:10px;width:100%;background:#2196F3;color:white;border:none}}
                </style>
                </head>
                <body>
                <h2>WiFi 配置</h2>
                <form action="/config" method="post">
                <select name="ssid">{wifi_list}</select>
                <input type="text" name="custom_ssid" placeholder="或手动输入SSID">
                <input type="password" name="password" placeholder="WiFi密码" required>
                <button type="submit">连接</button>
                </form>
                </body>
                </html>
                """
        httpResponse.WriteResponseOk(contentType="text/html", content=html)
        gc.collect()

    def _config(self, httpClient, httpResponse):
        """修改后的配置提交处理：只收数据，不碰硬件"""
        form = httpClient.ReadRequestPostedFormData()
        self.target_ssid = form.get("custom_ssid") or form.get("ssid")
        self.target_pwd = form.get("password")

        # 仅仅改变状态标志，具体连接动作由主循环处理
        self.status = "connecting"

        # 返回一个简单的跳转页面
        content = """
        <meta charset="UTF-8">
        <h3>正在尝试连接 WiFi...</h3>
        <p>如果连接成功，热点将自动关闭。</p>
        <script>
            setTimeout(function(){
                window.location.href = '/status';
            }, 3000);
        </script>
        """
        httpResponse.WriteResponseOk(contentType="text/html", content=content)
        gc.collect()

    def _status(self, httpClient, httpResponse):
        if self.sta.isconnected():
            msg = "成功"
        else:
            msg = "连接中"
        httpResponse.WriteResponseOk(contentType="text/plain", content=msg)


def auto_connect():
    mgr = _WiFiManager()

    if mgr.try_auto_connect():
        return

    mgr.start_config()
    
    
if __name__ == '__main__':
    auto_connect()