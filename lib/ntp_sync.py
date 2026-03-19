# ntp_sync.py
from time import gmtime
import socket
import struct
import machine

# 可自行增删服务器
_DEFAULT_HOSTS = [
    "ntp7.aliyun.com",
    "ntp.ntsc.ac.cn",
    "cn.ntp.org.cn",
    "cn.pool.ntp.org",
    "ntp3.tencent.com",
    "time.windows.com",
]

# NTP 回绕判断阈值（2036 问题）
_MIN_NTP_TIMESTAMP = 3913056000


def _get_epoch_delta():
    """
    自动判断 MicroPython 使用的 epoch
    ESP32 通常是 2000-01-01
    """
    epoch_year = gmtime(0)[0]

    if epoch_year == 2000:
        return 3155673600
    elif epoch_year == 1970:
        return 2208988800
    else:
        raise Exception("Unsupported epoch: {}".format(epoch_year))


def _query_host(host, timeout):
    """
    向单个 NTP 服务器发起查询
    返回 UTC 时间戳（秒）
    """
    addr = socket.getaddrinfo(host, 123)[0][-1]

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.settimeout(timeout)

        # 构造 NTP 请求包
        packet = bytearray(48)
        packet[0] = 0x1B

        s.sendto(packet, addr)
        msg = s.recv(48)

        val = struct.unpack("!I", msg[40:44])[0]

        # 2036 回绕修正
        if val < _MIN_NTP_TIMESTAMP:
            val += 0x100000000

        delta = _get_epoch_delta()
        return val - delta

    finally:
        s.close()


def get_utc_timestamp(hosts=None, timeout=2):
    """
    获取 UTC 时间戳（秒）
    不写 RTC
    """
    if hosts is None:
        hosts = _DEFAULT_HOSTS

    last_error = None

    for host in hosts:
        try:
            ts = _query_host(host, timeout)
            print("NTP同步成功:", host)
            return ts
        except Exception as e:
            print("NTP失败:", host, e)
            last_error = e

    raise Exception("所有NTP服务器不可用: {}".format(last_error))


def set_rtc_utc(hosts=None, timeout=2):
    """
    同步 RTC（存 UTC）
    """
    ts = get_utc_timestamp(hosts, timeout)

    tm = gmtime(ts)

    machine.RTC().datetime(
        (tm[0], tm[1], tm[2], tm[6] + 1,
         tm[3], tm[4], tm[5], 0)
    )

    return True


def get_localtime(tz=8):
    """
    获取本地时间（不修改 RTC）
    """
    import time
    ts = time.time() + tz * 3600
    return time.localtime(ts)
    
'''

def get_localtime(tz=8):
    #替换上面的函数，伪造当前日期
    year = 2026
    month = 3
    day = 20
    hour = 10
    minute = 10
    second = 10


    if month < 3:
        month += 12
        year -= 1
    century = year // 100
    year_of_century = year % 100
    # 蔡勒公式简化版
    weekday = (year_of_century + year_of_century//4 + century//4 - 2*century + 
               26*(month+1)//10 + day - 1) % 7
    # 调整为0=周一，6=周日
    weekday = (weekday + 6) % 7
    
    # 计算一年中的第几天
    month_days = [31, 28, 31, 30, 31, 30,
                  31, 31, 30, 31, 30, 31]
    yearday = sum(month_days[:month-1]) + day
    
    # 返回与 time.localtime() 完全相同的8元组
    return (year, month, day, hour, minute, second, weekday, yearday)
    
    
'''