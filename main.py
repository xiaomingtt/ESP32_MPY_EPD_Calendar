from machine import Pin, deepsleep
import time
import gc
import sys, os
import random 
from lib.smartconfig import auto_connect
from lib.ntp_sync import set_rtc_utc, get_localtime
from lib.dispatcher import Dispatcher
from lib.qweather import QWeather
from lib.timetable_new import timetable_show
from lib.calendar_lib_new import show_calendar
from lib.get_holiday import save_holidays_to_flash
from lib.multi_button import MultiButton, Event
from lib.timetable_web import start_web_server, stop_web_server, is_web_server_running

gc.enable()

now_state = "calendar" 
current_year = 0
current_month = 0
current_img_index = 1

def _count_images():
    cnt = 0
    try:
        for f in os.listdir("images"):
            if f.startswith("epd_image") and f.endswith(".py"):
                cnt += 1
        print(f"✅ 发现图片库: 共 {cnt} 张")
    except Exception as e:
        print(f"⚠️ 扫描图片目录失败: {e}")
        cnt = 0
    return cnt

total_images = _count_images()

def show_image(i):
    from lib.epddisplay_new import epd
    
    module_name = f"images.epd_image{i:02d}"
    try:
        mod = __import__(module_name, None, None, ['bw_ram_data', 'red_ram_data'])
        bw_data = mod.bw_ram_data
        red_data = mod.red_ram_data
    except (ImportError, AttributeError) as e:
        print(f"❌ 图片加载失败: {module_name}, 错误: {e}")
        return False

    print(f"🖼  显示图片: {module_name}")
    

    #epd.clear_screen(0xFF, 0x00)
    epd.write_buffer(bw_data, is_red=False)
    epd.write_buffer(red_data, is_red=True)
    epd.refresh()

    if module_name in sys.modules:
        del sys.modules[module_name]
    del mod, bw_data, red_data
    gc.collect()
    return True


def show_memory():
    free = gc.mem_free()
    alloc = gc.mem_alloc()
    print(f"空闲内存: {free} B | 已分配内存: {alloc} B")
    
show_memory()


auto_connect()
set_rtc_utc()

def update_current_time():
    global current_year, current_month
    nowdate = get_localtime(8)
    current_year = nowdate[0]
    current_month = nowdate[1]
    print("当前时间:", current_year, current_month)

update_current_time()


KEY = "和风天气API"
LOC = "2.059756,3.212771" 
weather_api = QWeather(KEY, LOC)

def get_Weather():
    print("执行天气更新:", get_localtime(8))
    try:
        weather_api.get_daily(save_to="weather_3day.json")
        weather_api.get_moon(save_to="moon_phase.json")
        weather_api.get_hourly(save_to="weather_hour.json")
        weather_api.get_now(save_to="weather_now.json")
    except Exception as e:
        print("天气获取失败:", e)

get_Weather()


tasks = Dispatcher()
tasks.add_work(get_Weather, 60 * 60 * 1000)


def on_single_click_1(btn):
    global current_year, current_month, now_state, current_img_index
    print("✅ 单击1")
    
    if now_state == "calendar":
        new_month = current_month + 1
        new_year = current_year
        if new_month > 12:
            new_month = 1
            new_year += 1
        current_year, current_month = new_year, new_month
        show_calendar(year=current_year, month=current_month)
        
    elif now_state == "album":
        current_img_index += 1
        if current_img_index > total_images:
            current_img_index = 1  
        show_image(current_img_index)

def on_double_click_1(btn):
    global now_state, current_img_index
    print("✅ 双击1 - 进入相册")
    now_state = "album"
    if is_web_server_running():
        stop_web_server()
    current_img_index = random.randint(1, total_images)
    show_image(current_img_index)

def on_single_click_2(btn):
    global current_year, current_month, now_state, current_img_index
    print("✅ 单击2")
    
    if now_state == "calendar":
        new_month = current_month - 1
        new_year = current_year
        if new_month < 1:
            new_month = 12
            new_year -= 1
        current_year, current_month = new_year, new_month
        show_calendar(year=current_year, month=current_month)
        
    elif now_state == "album":
        current_img_index -= 1
        if current_img_index < 1:
            current_img_index = total_images  
        show_image(current_img_index)

def on_long_press_start_1(btn):
    global now_state
    now_state = "timetable"
    print("✅ 长按1 - 课程表")
    timetable_show()
    start_web_server()
    
def on_long_press_start_2(btn):
    global now_state
    print("✅ 长按2 - 返回日历")
    now_state = "calendar"
    if is_web_server_running():
        stop_web_server()
    update_current_time()
    show_calendar(year=current_year, month=current_month)


btn1 = MultiButton(pin=1, active_level=0)
btn2 = MultiButton(pin=2, active_level=0)
btn3 = MultiButton(pin=3, active_level=0)
btn4 = MultiButton(pin=4, active_level=0)

btn1.attach(Event.SINGLE_CLICK, on_single_click_1)
btn1.attach(Event.DOUBLE_CLICK, on_double_click_1)
btn1.attach(Event.LONG_PRESS_START, on_long_press_start_1)

btn2.attach(Event.SINGLE_CLICK, on_single_click_2)
btn2.attach(Event.DOUBLE_CLICK, lambda btn: print("✅ 双击2事件"))
btn2.attach(Event.LONG_PRESS_START, on_long_press_start_2)

btn3.attach(Event.SINGLE_CLICK, lambda btn: print("✅ 单击3事件"))
btn3.attach(Event.DOUBLE_CLICK, lambda btn: print("✅ 双击3事件"))
btn3.attach(Event.LONG_PRESS_START, lambda btn: print("✅ 长按3事件"))

btn4.attach(Event.SINGLE_CLICK, lambda btn: print("✅ 单击4事件"))
btn4.attach(Event.DOUBLE_CLICK, lambda btn: print("✅ 双击4事件"))
btn4.attach(Event.LONG_PRESS_START, lambda btn: print("✅ 长按4事件"))

btn1.start()
btn2.start()
btn3.start()
btn4.start()


def re_show():
    global now_state 
    print("刷新屏幕:", get_localtime(8))
    now_state = "calendar"
    show_calendar(year=current_year, month=current_month)
    
re_show()

save_holidays_to_flash(current_year)
tasks.add_work(re_show, 2 * 60 * 60 * 1000) 

gc.collect()
show_memory()

try:
    while True:
        MultiButton.tick_all()
        time.sleep_ms(5)
except KeyboardInterrupt:
    print("程序终止")
    tasks.deinit()
