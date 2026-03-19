from machine import SPI, Pin
import time

# === SSD1683 命令集（根据数据手册 Rev 1.0 整理）===
SSD1683_CMD_DRIVER_OUTPUT_CTL      = 0x01  # 驱动输出控制（设置门数）
SSD1683_CMD_BOOSTER_SOFT_START      = 0x06  # 升压软启动
SSD1683_CMD_DEEP_SLEEP              = 0x10  # 深度休眠 (参数 A[1:0])
SSD1683_CMD_DATA_ENTRY_MODE         = 0x11  # 数据写入模式（地址增量方向）
SSD1683_CMD_SW_RESET                = 0x12  # 软件复位
SSD1683_CMD_MASTER_ACTIVATION       = 0x20  # 启动显示刷新
SSD1683_CMD_DISPLAY_UPDATE_CTRL2    = 0x22  # 显示更新时序控制
SSD1683_CMD_WRITE_BW_RAM             = 0x24  # 写入黑白缓冲区
SSD1683_CMD_WRITE_RED_RAM            = 0x26  # 写入红色缓冲区
SSD1683_CMD_WRITE_VCOM               = 0x2C  # 设置VCOM电压
SSD1683_CMD_WRITE_LUT                = 0x32  # 写入波形LUT（227字节）
SSD1683_CMD_BORDER_WAVEFORM          = 0x3C  # 边框波形控制
SSD1683_CMD_SET_RAM_X_START_END      = 0x44  # 设置X方向RAM窗口起止（字节单位）
SSD1683_CMD_SET_RAM_Y_START_END      = 0x45  # 设置Y方向RAM窗口起止（行单位）
SSD1683_CMD_SET_RAM_X_COUNTER        = 0x4E  # 设置X地址计数器
SSD1683_CMD_SET_RAM_Y_COUNTER        = 0x4F  # 设置Y地址计数器

# 以下命令在原驱动中使用，虽未在手册中明确，但实际有效
SSD1683_CMD_POWER_ON                 = 0x04  # 电源开启（原驱动使用）

class GDEY042Z98:
    """适用于GDEY042Z98（SSD1683驱动，400x300，红黑白三色）的墨水屏驱动"""
    WIDTH = 400
    HEIGHT = 300
    BYTES_PER_BUFFER = WIDTH * HEIGHT // 8  # 15000 字节（全屏）

    def __init__(self, spi_bus=1, sck=12, mosi=11, cs=5, dc=9, rst=8, busy=7):
        """
        初始化硬件接口并执行屏幕初始化序列
        参数:
            spi_bus: SPI总线编号（如2对应ESP32-S3的SPI2）
            sck, mosi: SPI时钟和数据引脚
            cs, dc, rst, busy: 屏幕控制引脚
        """
        # 初始化SPI（极性0，相位0，最高20MHz）
        self.spi = SPI(
            spi_bus,
            baudrate=20_000_000,
            polarity=0,
            phase=0,
            sck=Pin(sck),
            mosi=Pin(mosi)
        )
        self.cs = Pin(cs, Pin.OUT, value=1)
        self.dc = Pin(dc, Pin.OUT, value=0)
        self.rst = Pin(rst, Pin.OUT, value=1)
        self.busy = Pin(busy, Pin.IN)

        self._init_display()

    # ---------- 底层通信 ----------
    def _send_cmd(self, cmd: int):
        """发送单字节命令（D/C# = 0）"""
        self.cs.value(0)
        self.dc.value(0)
        self.spi.write(bytes([cmd]))
        self.cs.value(1)

    def _send_data(self, data):
        """发送数据字节（D/C# = 1），支持int或bytes-like"""
        self.cs.value(0)
        self.dc.value(1)
        if isinstance(data, int):
            self.spi.write(bytes([data]))
        else:
            self.spi.write(data)
        self.cs.value(1)

    def _wait_busy(self):
        """等待BUSY引脚变为低电平（忙状态为高）"""
        while self.busy.value() == 1:
            time.sleep_ms(10)

    # ---------- 初始化序列（兼容原驱动行为） ----------
    def _init_display(self):
        """完整的屏幕初始化流程（与原驱动一致）"""
        # 硬件复位
        self.rst.value(0)
        time.sleep_ms(20)
        self.rst.value(1)
        time.sleep_ms(20)
        self._wait_busy()

        # 软件复位（可选，确保芯片处于已知状态，原驱动未用但保留无害）
        self._send_cmd(SSD1683_CMD_SW_RESET)
        self._wait_busy()

        # 原驱动中的电源开启命令（0x04），虽手册未列但必要
        self._send_cmd(SSD1683_CMD_POWER_ON)
        self._wait_busy()

        # 升压软启动（与原驱动一致）
        self._send_cmd(SSD1683_CMD_BOOSTER_SOFT_START)
        self._send_data(0x17)
        self._send_data(0x17)
        self._send_data(0x17)

        # VCOM电压设置（与原驱动一致）
        self._send_cmd(SSD1683_CMD_WRITE_VCOM)
        self._send_data(0x38)

        # 设置数据写入模式（X方向递增，Y方向递增，AM=0），原驱动虽未显式设置，但POR值可能为此，此处保留
        self._send_cmd(SSD1683_CMD_DATA_ENTRY_MODE)
        self._send_data(0x03)

        # 设置RAM窗口为全屏（确保写入范围正确，原驱动未设但可能默认全屏，此处设置无妨）
        self._send_cmd(SSD1683_CMD_SET_RAM_X_START_END)
        self._send_data(0x00)        # 起始X字节地址
        self._send_data(0x31)        # 结束X字节地址 (49 = 0x31)

        self._send_cmd(SSD1683_CMD_SET_RAM_Y_START_END)
        self._send_data(0x00)        # Y起始低8位
        self._send_data(0x00)        # Y起始高1位
        self._send_data(0x2B)        # Y结束低8位 (299=0x12B，低8位0x2B)
        self._send_data(0x01)        # Y结束高1位

        # 将地址计数器定位到窗口起点 (0,0)
        self._send_cmd(SSD1683_CMD_SET_RAM_X_COUNTER)
        self._send_data(0x00)
        self._send_cmd(SSD1683_CMD_SET_RAM_Y_COUNTER)
        self._send_data(0x00)
        self._send_data(0x00)

        # 写入LUT（严格复制原驱动的67字节，不补0）
        self._send_cmd(SSD1683_CMD_WRITE_LUT)
        lut = [
            0x80,0x60,0x40,0x00,0x00,0x00,0x00,  # LUT0 (BB)
            0x10,0x60,0x20,0x00,0x00,0x00,0x00,  # LUT1 (BW)
            0x80,0x60,0x40,0x00,0x00,0x00,0x00,  # LUT2 (WB)
            0x10,0x60,0x20,0x00,0x00,0x00,0x00,  # LUT3 (WW)
            0x00,0x00,0x00,0x00,0x00,0x00,0x00,  # LUT4 (VCOM)
            0x03,0x03,0x00,0x00,0x02,
            0x09,0x09,0x00,0x00,0x02,
            0x03,0x03,0x00,0x00,0x02,
            0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,
            0x00,0x00,0x00,0x00,0x00,
            0x00,0x00
        ]
        self._send_data(bytes(lut))  # 发送原长度（67字节）
        self._wait_busy()

        # 边框波形设为高阻（原驱动未设，但POR值可能为此，保留）
        self._send_cmd(SSD1683_CMD_BORDER_WAVEFORM)
        self._send_data(0xC0)

    # ---------- 公共操作API ----------
    def _set_ram_window(self, x, y, w, h):
        """
        设置RAM写入窗口（确保字节对齐）
        参数均为像素坐标，但X必须为8的倍数，宽度也建议为8的倍数
        """
        if x % 8 != 0 or w % 8 != 0:
            raise ValueError("X和宽度必须是8的倍数（字节对齐）")
        x_start_byte = x // 8
        x_end_byte = (x + w - 1) // 8

        self._send_cmd(SSD1683_CMD_SET_RAM_X_START_END)
        self._send_data(x_start_byte)
        self._send_data(x_end_byte)

        self._send_cmd(SSD1683_CMD_SET_RAM_Y_START_END)
        self._send_data(y & 0xFF)
        self._send_data((y >> 8) & 0xFF)
        self._send_data((y + h - 1) & 0xFF)
        self._send_data(((y + h - 1) >> 8) & 0xFF)

        self._send_cmd(SSD1683_CMD_SET_RAM_X_COUNTER)
        self._send_data(x_start_byte)
        self._send_cmd(SSD1683_CMD_SET_RAM_Y_COUNTER)
        self._send_data(y & 0xFF)
        self._send_data((y >> 8) & 0xFF)

    def clear_screen(self, black_val=0xFF, red_val=0xFF):
        """
        全屏清屏
        black_val: 黑白像素值（0=黑，1=白，对应字节中每位，0xFF为全白）
        red_val:   红色像素值（0=红，1=白，0xFF为无红）
        """
        # 填充黑白RAM
        self._set_ram_window(0, 0, self.WIDTH, self.HEIGHT)
        self._send_cmd(SSD1683_CMD_WRITE_BW_RAM)
        for _ in range(self.BYTES_PER_BUFFER):
            self._send_data(black_val)

        # 填充红色RAM
        self._set_ram_window(0, 0, self.WIDTH, self.HEIGHT)
        self._send_cmd(SSD1683_CMD_WRITE_RED_RAM)
        for _ in range(self.BYTES_PER_BUFFER):
            self._send_data(red_val)

        self.refresh()

    def write_buffer(self, data, is_red=False):
        """
        写入全屏缓冲区（原有函数，兼容旧代码）
        data: 字节数组，长度必须为15000
        is_red: True写入红色平面，False写入黑白平面
        """
        if len(data) != self.BYTES_PER_BUFFER:
            raise ValueError(f"数据长度必须为{self.BYTES_PER_BUFFER}字节")
        self._set_ram_window(0, 0, self.WIDTH, self.HEIGHT)
        cmd = SSD1683_CMD_WRITE_RED_RAM if is_red else SSD1683_CMD_WRITE_BW_RAM
        self._send_cmd(cmd)
        self._send_data(data)

    def write_partial_buffer(self, data, x, y, w, h, is_red=False):
        """
        写入指定位置的小尺寸缓冲区（控制图片显示位置）
        参数说明：
            data: 小图片的取模字节数组，长度必须 = (w * h) // 8
            x:    图片左上角的X坐标（像素），必须是8的倍数（如0,8,16...）
            y:    图片左上角的Y坐标（像素），无倍数限制（如0,10,20...）
            w:    图片宽度（像素），必须是8的倍数（如80,160,240...）
            h:    图片高度（像素），无倍数限制（如60,120,180...）
            is_red: True=写入红色图层，False=写入黑白图层
        """
        # 1. 参数合法性校验
        if x < 0 or y < 0:
            raise ValueError("X/Y坐标不能为负数")
        if w <= 0 or h <= 0:
            raise ValueError("图片宽/高必须大于0")
        if x + w > self.WIDTH:
            raise ValueError(f"X+宽度超出屏幕范围（屏幕宽度{self.WIDTH}）")
        if y + h > self.HEIGHT:
            raise ValueError(f"Y+高度超出屏幕范围（屏幕高度{self.HEIGHT}）")
        if w % 8 != 0:
            raise ValueError(f"图片宽度必须是8的倍数（当前{w}）")
        expected_len = (w * h) // 8
        if len(data) != expected_len:
            raise ValueError(f"数据长度错误：预期{expected_len}字节，实际{len(data)}字节")

        # 2. 设置RAM窗口（指定显示位置和尺寸）
        self._set_ram_window(x, y, w, h)

        # 3. 写入小尺寸buffer（仅写入图片对应长度，而非全屏）
        cmd = SSD1683_CMD_WRITE_RED_RAM if is_red else SSD1683_CMD_WRITE_BW_RAM
        self._send_cmd(cmd)
        self._send_data(data)

    def refresh(self):
        """执行全屏刷新（必须调用才会更新显示）"""
        self._send_cmd(SSD1683_CMD_MASTER_ACTIVATION)
        self._wait_busy()

    def sleep(self):
        """进入深度休眠模式2（最低功耗，RAM内容不保留）"""
        self._send_cmd(SSD1683_CMD_DEEP_SLEEP)
        self._send_data(0x03)        # 模式2

    def draw_char(self, fb, x, y, char_data, char_width, char_height, color):
        bytes_per_row = (char_width + 7) // 8
        for row in range(char_height):
            for byte_index in range(bytes_per_row):
                byte = char_data[row * bytes_per_row + byte_index]
                for bit in range(8):
                    if (byte >> (7 - bit)) & 0x01:  # 高位在前
                        pixel_x = x + byte_index * 8 + bit
                        pixel_y = y + row
                        # 确保在字符有效区域内
                        if pixel_x < x + char_width and pixel_y < y + char_height:
                            if pixel_x < self.WIDTH and pixel_y < self.HEIGHT:
                                fb.pixel(pixel_x, pixel_y, color)