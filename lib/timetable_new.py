import json
from ntp_sync import get_localtime


from lib.epddisplay_new import epd, buf_black, buf_red, fb_black, fb_red, draw_mixed_text
from lib.weather_icons import image_data

class _Timetable:
    """内部私有类，对外不暴露"""
    def __init__(self):
        # 1. 时间同步
        self.datetime_now = get_localtime(8)
        self.weekday_today = self.datetime_now[6]  # 0=周一, 4=周五, 5/6=周末

        # 2. 加载课程表
        self.timetable_data = self._load_timetable()

        # 3. 布局参数
        self.START_X = 5
        self.START_Y = 50
        self.COL_WIDTHS = [90, 60, 60, 60, 60, 60]
        self.CELL_HEIGHT = 30
        self.TABLE_WIDTH = sum(self.COL_WIDTHS)
        self.TABLE_HEIGHT = 8 * self.CELL_HEIGHT

    def _load_timetable(self):
        """加载课程表json，失败返回默认结构"""
        try:
            with open("timetable.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return [
                ["", "周一", "周二", "周三", "周四", "周五"],
                ["第1节\n8:00-8:45", "", "", "", "", ""],
                ["第2节\n8:55-9:40", "", "", "", "", ""],
                ["第3节\n9:50-10:35", "", "", "", "", ""],
                ["第4节\n10:45-11:30", "", "", "", "", ""],
                ["第5节\n11:40-12:25", "", "", "", "", ""],
                ["第6节\n13:30-14:15", "", "", "", "", ""],
                ["第7节\n14:25-15:10", "", "", "", "", ""],
            ]

    def _estimate_text_width(self, text, font_size):
        """估算文本宽度，和原代码逻辑完全一致"""
        width = 0
        for ch in text:
            if '\u4e00' <= ch <= '\u9fff':
                width += font_size
            else:
                width += font_size // 2
        return width

    def _get_col_x(self, col_idx):
        """计算列的X坐标"""
        x = self.START_X
        for i in range(col_idx):
            x += self.COL_WIDTHS[i]
        return x

    def _draw_centered_text(self, text, cell_x, cell_y, cell_w, cell_h, font_size, color):
        """居中绘制文本，和原代码一致"""
        if not text:
            return
        text_w = self._estimate_text_width(text, font_size)
        x = cell_x + (cell_w - text_w) // 2
        y = cell_y + (cell_h - font_size) // 2
        x = max(cell_x, min(x, cell_x + cell_w - text_w))
        y = max(cell_y, min(y, cell_y + cell_h - font_size))
        draw_mixed_text(text, x, y, size=font_size, overlap=True, color=color)

    def _draw_first_cell(self, text, cell_x, cell_y, cell_w, cell_h, color):
        """绘制第一列的节次单元格，仅修复切割逻辑"""
        if not text:
            return
        
        if '\n' in text:
            part1, part2 = text.split('\n', 1)
        else:
            if "节" in text:
                idx = text.index("节") + 1
                part1 = text[:idx]
                part2 = text[idx:]
            else:
                part1 = text[:4]
                part2 = text[4:]  

        top_h = cell_h // 2
        bottom_h = cell_h - top_h

        # 上半部分节次文字
        if part1:
            text_w = self._estimate_text_width(part1, 16)
            x = cell_x + (cell_w - text_w) // 2
            y = cell_y + (top_h - 16) // 2 + 4
            x = max(cell_x, min(x, cell_x + cell_w - text_w))
            y = max(cell_y, min(y, cell_y + top_h - 16))
            draw_mixed_text(part1, x, y+2, size=16, overlap=True, color=color)

        # 下半部分时间小字
        if part2:
            x = cell_x + 2
            y = cell_y + top_h + (bottom_h - 8) // 2 + 2
            if y > cell_y + cell_h - 8:
                y = cell_y + cell_h - 8
            if color == "red":
                fb_red.text(part2, x, y, 0x00)
            else:
                fb_black.text(part2, x, y, 0x00)

    def _draw_top_date(self):
        """绘制顶部年月日"""
        year = str(self.datetime_now[0])
        month = self.datetime_now[1]
        day = self.datetime_now[2]
        month_str = f"{month:02d}"
        day_str = f"{day:02d}"
        draw_mixed_text(year, 5, 9, size=32, overlap=True, color="black")
        draw_mixed_text("年", 76, 17, size=16, overlap=True, color="black")
        draw_mixed_text(month_str, 94, 9, size=32, overlap=True, color="black")
        draw_mixed_text("月", 130, 17, size=16, overlap=True, color="black")
        draw_mixed_text(day_str, 146, 9, size=32, overlap=True, color="black")
        draw_mixed_text("日", 179, 17, size=16, overlap=True, color="black")

    def _draw_table_frame(self):
        """绘制表格横线竖线"""
        # 横线
        for i in range(9):
            y = self.START_Y + i * self.CELL_HEIGHT
            fb_black.hline(self.START_X, y, self.TABLE_WIDTH, 0)
        # 竖线
        for i in range(7):
            x = self._get_col_x(i)
            fb_black.vline(x, self.START_Y, self.TABLE_HEIGHT, 0)

    def _fill_table_content(self):
        """填充课程表所有单元格内容"""
        for row in range(8):
            for col in range(6):
                text = self.timetable_data[row][col]
                if not text:
                    continue

                cell_x = self._get_col_x(col)
                cell_y = self.START_Y + row * self.CELL_HEIGHT
                cell_w = self.COL_WIDTHS[col]

                # 当天表头单元格：红底白字
                if row == 0 and col == self.weekday_today + 1 and 1 <= col <= 5:
                    fb_red.fill_rect(cell_x, cell_y, cell_w, self.CELL_HEIGHT, 0xFF)
                    self._draw_centered_text(text, cell_x, cell_y, cell_w, self.CELL_HEIGHT, 24, "white")
                else:
                    # 普通单元格：当天列红字，其他黑字
                    text_color = "red" if (col == self.weekday_today + 1 and 1 <= col <= 5) else "black"
                    if col == 0:
                        self._draw_first_cell(text, cell_x, cell_y, cell_w, self.CELL_HEIGHT, text_color)
                    else:
                        self._draw_centered_text(text, cell_x, cell_y, cell_w, self.CELL_HEIGHT, 24, text_color)

    def _draw_weather_text(self):
        """仅绘制天气文字，返回是否绘制成功（用于判断是否二次写入缓冲区）"""
        text_drawn = False
        try:
            with open("weather_now.json", 'r') as f:
                content = f.read()
            data = json.loads(content)
            
            if data.get("code") == "200":
                now = data.get("now", {})
                temp = now.get("temp")
                text = now.get("text")
                windDir = now.get("windDir")
                windScale = now.get("windScale")
                
                # 绘制天气文字
                draw_mixed_text(text + " " + temp + "℃", 250, 9, size=16, overlap=True, color="black")
                draw_mixed_text(windDir + " " + windScale + "级", 250, 30, size=16, overlap=True, color="black")
                text_drawn = True
                print(f"🌡 天气文字绘制成功: 温度={temp}, 天气={text}")
        except Exception as e:
            print(f"❌ 天气文字绘制异常: {e}")
        return text_drawn

    def _draw_weather_icon(self):
        """仅绘制天气图标（局部写入），必须在二次缓冲区写入之后执行"""
        try:
            with open("weather_now.json", 'r') as f:
                content = f.read()
            data = json.loads(content)
            
            if data.get("code") == "200":
                now = data.get("now", {})
                icon = now.get("icon")
                if icon in image_data:
                    img = image_data[icon]
                    # X是8的倍数
                    epd.write_partial_buffer(
                        data=img,
                        x=208,
                        y=9,
                        w=32,
                        h=32,
                        is_red=False
                    )
                    print("✅ 天气图标已写入")
                else:
                    print(f"❌ 图标库无对应图标: {icon}")
        except Exception as e:
            print(f"❌ 天气图标绘制异常: {e}")

    def _draw_moon_icon(self):
        """绘制月相图标（局部写入），和原代码逻辑一致"""
        try:
            with open("moon_phase.json", 'r', encoding="utf-8") as f:
                content = f.read()
            data = json.loads(content)
            
            if data.get("code") == "200":
                moon = data.get("moonPhase", [])
                if moon:
                    moonPhase = moon[0]
                    icon = moonPhase.get("icon")
                    if icon in image_data:
                        img = image_data[icon]
                        epd.write_partial_buffer(
                            data=img,
                            x=360,
                            y=9,
                            w=32,
                            h=32,
                            is_red=False
                        )
                        print("✅ 月相图标已写入")
                    else:
                        print(f"❌ 图标库无对应月相图标: {icon}")
        except Exception as e:
            print(f"❌ 月相图标绘制异常: {e}")

    def _clear_framebuffer(self):
        """
        清空内存中的 FrameBuffer
        """
        # 0xFF 代表白色背景（清空黑色缓冲区）
        fb_black.fill(0xFF)
        # 0x00 代表无红色（清空红色缓冲区）
        fb_red.fill(0x00)
        print("🧹 内存 FrameBuffer 已清空")

    def run(self):
        self._clear_framebuffer()

        # 1. 绘制课程表完整内容
        self._draw_top_date()
        self._draw_table_frame()
        self._fill_table_content()

        # 2. 第一次全量写入缓冲区（课程表内容）
        epd.write_buffer(buf_black, is_red=False)
        epd.write_buffer(buf_red, is_red=True)

        # 3. 绘制天气文字
        weather_text_ok = self._draw_weather_text()

        # 4. 第二次全量写入缓冲区（把天气文字提交到硬件）
        if weather_text_ok:
            epd.write_buffer(buf_black, is_red=False)
            epd.write_buffer(buf_red, is_red=True)

        # 5. 绘制天气图标（局部写入）
        self._draw_weather_icon()

        # 6. 绘制月相图标（局部写入）
        self._draw_moon_icon()

        # 7. 最终刷新屏幕
        epd.refresh()
        print("✅ 课程表屏幕刷新完成")

# ==========================================
# 对外唯一暴露的接口
# ==========================================
def timetable_show():
    """一句话显示完整课程表（含日期、课程、天气、月相）"""
    timetable = _Timetable()
    timetable.run()
    
if __name__ == "__main__":
    timetable_show()