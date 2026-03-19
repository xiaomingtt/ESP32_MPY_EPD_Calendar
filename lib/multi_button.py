import time

# ------------------------------ 事件类型常量 ------------------------------
class Event:
    PRESS_DOWN = 0       # 按键按下（每次按下触发）
    PRESS_UP = 1         # 按键松开（每次松开触发）
    SINGLE_CLICK = 2     # 单击事件
    DOUBLE_CLICK = 3     # 双击事件
    LONG_PRESS_START = 4 # 长按开始（仅触发一次）
    LONG_PRESS_HOLD = 5  # 长按保持（周期性触发）
    PRESS_REPEAT = 6     # 重复按下（按下后周期性触发）

# ------------------------------ 状态机状态常量 ------------------------------
class State:
    IDLE = 0             # 空闲状态
    PRESS_DOWN = 1       # 按下状态
    PRESS_UP = 2         # 松开状态
    SINGLE_CLICK = 3     # 单击确认
    DOUBLE_CLICK = 4     # 双击确认
    LONG_PRESS_START = 5 # 长按开始
    LONG_PRESS_HOLD = 6  # 长按保持

# ------------------------------ MultiButton 核心类 ------------------------------
class MultiButton:
    # 全局配置参数（可通过类变量统一修改）
    DEBOUNCE_TICKS = 5      # 消抖次数（建议每5ms调用一次tick，总消抖25ms）
    SHORT_TICKS = 200        # 短按最大时长（ms）
    LONG_TICKS = 1000        # 长按触发时长（ms）
    DOUBLE_TICKS = 300        # 双击间隔时长（ms）
    LONG_HOLD_INTERVAL = 500  # 长按保持触发间隔（ms）
    REPEAT_INTERVAL = 200     # 重复按下触发间隔（ms）

    # 所有注册的按键列表（类变量）
    _buttons = []

    def __init__(self, pin, active_level=0, pin_read_func=None):
        """
        初始化按键对象
        :param pin: 按键引脚（int类型引脚号 或 machine.Pin对象）
        :param active_level: 有效电平（0=低电平有效，1=高电平有效）
        :param pin_read_func: 自定义引脚读取函数（可选，默认用pin.value()）
        """
        # 自动初始化引脚（如果传入的是引脚号）
        if isinstance(pin, int):
            from machine import Pin
            # 默认配置为输入上拉（可根据实际电路修改）
            self._pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        else:
            self._pin = pin

        self._active_level = active_level
        self._pin_read_func = pin_read_func or self._default_pin_read

        # 按键状态变量
        self._state = State.IDLE
        self._debounce_cnt = 0
        self._last_level = self._pin_read_func()  # 初始电平
        self._press_time = 0       # 按下时间戳
        self._release_time = 0     # 松开时间戳
        self._last_hold_time = 0   # 上次长按保持触发时间
        self._last_repeat_time = 0 # 上次重复触发时间
        self._event_callbacks = {} # 事件回调字典

    def _default_pin_read(self):
        """默认引脚读取函数（读取GPIO电平）"""
        return self._pin.value()

    def attach(self, event, callback):
        """
        注册事件回调函数
        :param event: 事件类型（Event.*）
        :param callback: 回调函数（参数为当前按键对象）
        """
        self._event_callbacks[event] = callback

    def _trigger_callback(self, event):
        """内部方法：触发指定事件的回调"""
        if event in self._event_callbacks:
            self._event_callbacks[event](self)

    def start(self):
        """启动按键（加入全局按键列表）"""
        if self not in self._buttons:
            self._buttons.append(self)

    def stop(self):
        """停止按键（从全局按键列表移除）"""
        if self in self._buttons:
            self._buttons.remove(self)

    def _tick(self):
        """内部方法：单个按键的状态机处理（核心逻辑）"""
        current_level = self._pin_read_func()
        current_time = time.ticks_ms()

        # ------------------------------ 1. 消抖处理 ------------------------------
        if current_level == self._last_level:
            self._debounce_cnt += 1
        else:
            self._debounce_cnt = 0
            self._last_level = current_level

        # 消抖未完成，直接返回
        if self._debounce_cnt < self.DEBOUNCE_TICKS:
            return

        # 消抖完成，确认按键是否按下
        is_pressed = (current_level == self._active_level)

        # ------------------------------ 2. 状态机流转 ------------------------------
        if self._state == State.IDLE:
            if is_pressed:
                # 按键按下：切换状态+记录时间+触发回调
                self._state = State.PRESS_DOWN
                self._press_time = current_time
                self._last_repeat_time = current_time
                self._trigger_callback(Event.PRESS_DOWN)

        elif self._state == State.PRESS_DOWN:
            if not is_pressed:
                # 按键松开：切换状态+记录时间+触发回调
                self._state = State.PRESS_UP
                self._release_time = current_time
                self._trigger_callback(Event.PRESS_UP)
            else:
                # 仍在按下：检查长按/重复触发
                if time.ticks_diff(current_time, self._press_time) >= self.LONG_TICKS:
                    # 触发长按开始
                    self._state = State.LONG_PRESS_START
                    self._trigger_callback(Event.LONG_PRESS_START)
                    self._last_hold_time = current_time
                else:
                    # 触发重复按下
                    if time.ticks_diff(current_time, self._last_repeat_time) >= self.REPEAT_INTERVAL:
                        self._trigger_callback(Event.PRESS_REPEAT)
                        self._last_repeat_time = current_time

        elif self._state == State.PRESS_UP:
            # 松开后：判断是单击还是等待双击
            if time.ticks_diff(current_time, self._release_time) >= self.DOUBLE_TICKS:
                # 双击超时：触发单击
                self._trigger_callback(Event.SINGLE_CLICK)
                self._state = State.IDLE
            else:
                # 等待双击：检查是否再次按下
                if is_pressed:
                    self._state = State.DOUBLE_CLICK
                    self._press_time = current_time
                    self._trigger_callback(Event.PRESS_DOWN)

        elif self._state == State.DOUBLE_CLICK:
            if not is_pressed:
                # 双击松开：触发双击事件
                self._release_time = current_time
                self._trigger_callback(Event.PRESS_UP)
                self._trigger_callback(Event.DOUBLE_CLICK)
                self._state = State.IDLE

        elif self._state == State.LONG_PRESS_START:
            if not is_pressed:
                # 长按松开：回到空闲
                self._release_time = current_time
                self._trigger_callback(Event.PRESS_UP)
                self._state = State.IDLE
            else:
                # 长按保持：周期性触发
                if time.ticks_diff(current_time, self._last_hold_time) >= self.LONG_HOLD_INTERVAL:
                    self._trigger_callback(Event.LONG_PRESS_HOLD)
                    self._last_hold_time = current_time

    @classmethod
    def tick_all(cls):
        """
        全局按键处理函数（必须周期性调用，建议每5ms一次）
        """
        for btn in cls._buttons:
            btn._tick()