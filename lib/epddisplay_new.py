from SSD1683_new import GDEY042Z98
import framebuf
import time
import font_all


# ================= 硬件配置 =================
EPD_PIN_CONFIG = {
    "spi_bus": 1,
    "sck": 12,
    "mosi": 11,
    "cs": 10,
    "dc": 9,
    "rst": 8,
    "busy": 7
}

epd = GDEY042Z98(**EPD_PIN_CONFIG)

buf_black = bytearray(epd.BYTES_PER_BUFFER)
buf_red   = bytearray(epd.BYTES_PER_BUFFER)

fb_black = framebuf.FrameBuffer(
    buf_black,
    epd.WIDTH,
    epd.HEIGHT,
    framebuf.MONO_HLSB
)

fb_red = framebuf.FrameBuffer(
    buf_red,
    epd.WIDTH,
    epd.HEIGHT,
    framebuf.MONO_HLSB
)


fb_black.fill(0xFF)   # 白背景
fb_red.fill(0x00)     # 红RAM清空 = 白背景


def draw_mixed_text(text, x, y, size=16, overlap=False, color="black"):
    if size == 16:
        font_dict = font_all.my_font_data_16
    elif size == 24:
        font_dict = font_all.my_font_data_24
    elif size == 32:
        font_dict = font_all.my_font_data_32
    elif size == 12:
        font_dict = font_all.my_font_data_12
    else:
        return

    # 严格匹配framebuf 1位色规则，颜色参数仅用0/1，规范兼容
    if color == "black":
        fb = fb_black
        fg = 0          # 黑白层：0=黑色
    elif color == "red":
        fb = fb_red
        fg = 1          # 红色层：1=红色
    elif color == "white":
        fb = fb_red
        fg = 0          # 红色层：0=白色（红底白字用）
    elif color == "bw_white":
        fb = fb_black
        fg = 1          # 黑白层：1=白色（黑底白字用）
    else:
        return

    cursor_x = x
    overlap_pixel = size // 2 if overlap else 0   # 英文字符重叠缩进

    for i in range(len(text)):
        ch = text[i]
        if ch in font_dict:
            char_data = font_dict[ch]
            char_width = int((len(char_data) / size) * 8)

            epd.draw_char(
                fb,
                cursor_x,
                y,
                char_data,
                char_width,
                size,
                fg
            )

            next_char_overlap = 0
            if overlap and i + 1 < len(text):
                next_ch = text[i+1]
                if ord(ch) < 128 and ord(next_ch) < 128:
                    next_char_overlap = overlap_pixel

            cursor_x += (char_width - next_char_overlap + 1)
        else:
            cursor_x += (size // 2)