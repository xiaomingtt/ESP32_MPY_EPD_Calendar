import json
import network
from microWebSrv import MicroWebSrv

# ------------------- 课程表数据管理 -------------------
TIMETABLE_FILE = "timetable.json"

# 默认课程表内容（8行6列）
default_timetable = [
    ["",       "周一", "周二", "周三", "周四", "周五"],
    ["第1节\n8:00-8:45", "", "", "", "", ""],
    ["第2节\n8:55-9:40", "", "", "", "", ""],
    ["第3节\n9:50-10:35", "", "", "", "", ""],
    ["第4节\n10:45-11:30", "", "", "", "", ""],
    ["第5节\n11:40-12:25", "", "", "", "", ""],
    ["第6节\n13:30-14:15", "", "", "", "", ""],
    ["第7节\n14:25-15:10", "", "", "", "", ""],
]

def load_timetable():
    """从 Flash 加载课程表 JSON"""
    try:
        with open(TIMETABLE_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) == 8 and all(len(row) == 6 for row in data):
                return data
    except Exception:
        pass
    return default_timetable

def save_timetable(data):
    """将课程表数据保存为 JSON 文件"""
    with open(TIMETABLE_FILE, "w") as f:
        json.dump(data, f)

# ------------------- Web 服务类 -------------------
class TimetableWebServer:
    def __init__(self):
        self.srv = None
        self._is_running = False

    def _generate_html(self, timetable):
        """生成包含可编辑表格的 HTML 页面"""
        html = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ESP32 课程表编辑</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
        h1 { text-align: center; color: #333; }
        table { border-collapse: collapse; width: 100%; margin-top: 20px; }
        td { border: 1px solid #ccc; padding: 0; height: 50px; }
        input { 
            width: 100%; height: 100%;
            border: none; padding: 5px; 
            box-sizing: border-box; 
            text-align: center;
            font-size: 14px;
            background: #f9f9f9;
        }
        input:focus { outline: 2px solid #4CAF50; background: #fff; }
        .btn-container { text-align: center; margin-top: 30px; }
        button { 
            padding: 12px 30px; 
            font-size: 18px;
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover { background-color: #45a049; }
        .info { text-align: center; color: #666; margin-top: 10px; }
    </style>
</head>
<body>
    <h1>📅 课程表编辑</h1>
    <div class="info">编辑完成后点击保存，墨水屏将在下次刷新时更新</div>
    <table>
'''
        for i in range(8):
            html += "        <tr>\n"
            for j in range(6):
                value = timetable[i][j]
                safe_value = value.replace('"', '&quot;')
                html += f'            <td><input type="text" name="cell_{i}_{j}" value="{safe_value}"></td>\n'
            html += "        </tr>\n"

        html += '''    </table>
    <div class="btn-container">
        <button onclick="submitTimetable()">💾 保存课程表</button>
    </div>

    <script>
        function submitTimetable() {
            var timetable = [];
            for (var i = 0; i < 8; i++) {
                var row = [];
                for (var j = 0; j < 6; j++) {
                    var input = document.getElementsByName("cell_" + i + "_" + j)[0];
                    row.push(input ? input.value : "");
                }
                timetable.push(row);
            }

            fetch('/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(timetable)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'ok') {
                    alert('✅ 保存成功！按ESP32按键刷新屏幕查看');
                } else {
                    alert('❌ 保存失败');
                }
            })
            .catch(err => {
                console.error(err);
                alert('❌ 保存失败，请检查网络');
            });
        }
    </script>
</body>
</html>'''
        return html

    def _handle_root(self, httpClient, httpResponse):
        """GET / ：返回课程表页面"""
        timetable = load_timetable()
        html = self._generate_html(timetable)
        httpResponse.WriteResponseOk(
            headers=None,
            contentType="text/html",
            content=html
        )

    def _handle_save(self, httpClient, httpResponse):
        """POST /save ：接收 JSON 并保存"""
        content = httpClient.ReadRequestContent()
        try:
            new_timetable = json.loads(content)
            save_timetable(new_timetable)
            httpResponse.WriteResponseOk(
                headers=None,
                contentType="application/json",
                content='{"status":"ok"}'
            )
        except Exception:
            httpResponse.WriteResponseBadRequest()

    def start(self):
        """启动Web服务（后台线程）"""
        if self._is_running:
            print("Web服务已在运行中")
            return False

        try:
            # 获取IP地址
            wlan = network.WLAN(network.STA_IF)
            if wlan.isconnected():
                ip = wlan.ifconfig()[0]
                print(f"🌐 课程表Web服务已启动: http://{ip}")
            else:
                print("⚠️ WiFi未连接，Web服务可能无法访问")

            # 定义路由
            routes = [
                ("/", "GET", self._handle_root),
                ("/save", "POST", self._handle_save),
            ]

            # 启动服务（threaded=True 表示后台运行）
            self.srv = MicroWebSrv(routeHandlers=routes)
            self.srv.Start(threaded=True)
            self._is_running = True
            return True
        except Exception as e:
            print(f"❌ Web服务启动失败: {e}")
            return False

    def stop(self):
        """停止Web服务"""
        if not self._is_running:
            return

        try:
            if self.srv:
                self.srv.Stop()
                self.srv = None
            self._is_running = False
            print("🛑 Web服务已停止")
        except Exception as e:
            print(f"❌ Web服务停止失败: {e}")

    def is_running(self):
        """返回服务运行状态"""
        return self._is_running

# ------------------- 全局实例 -------------------
_web_server = TimetableWebServer()

# ------------------- 对外接口 -------------------
def start_web_server():
    """启动课程表Web服务"""
    return _web_server.start()

def stop_web_server():
    """停止课程表Web服务"""
    _web_server.stop()

def is_web_server_running():
    """检查Web服务状态"""
    return _web_server.is_running()