import json
import sys

try:
    from lib.epddisplay_new import epd, buf_black, buf_red, fb_black, fb_red, draw_mixed_text
    from ntp_sync import get_localtime
    from lib.weather_icons import image_data
    from lib.jieri import YANGLI_JIERI, NONGLI_JIERI
except ImportError as e:
    print(f"⚠️ 依赖导入失败: {e}")
    print("请确保文件结构正确，或手动调整 sys.path")
    raise

# ======================== 农历数据 ========================
TIAN_GAN = "甲乙丙丁戊己庚辛壬癸"
DI_ZHI = "子丑寅卯辰巳午未申酉戌亥"
ZODIAC = "鼠牛虎兔龙蛇马羊猴鸡狗猪"
SOLAR_TERMS = ["小寒","大寒","立春","雨水","惊蛰","春分","清明","谷雨","立夏","小满","芒种","夏至","小暑","大暑","立秋","处暑","白露","秋分","寒露","霜降","立冬","小雪","大雪","冬至"]
LUNAR_MONTHS = ["正","二","三","四","五","六","七","八","九","十","冬","腊"]
LUNAR_DATES = ["初一","初二","初三","初四","初五","初六","初七","初八","初九","初十","十一","十二","十三","十四","十五","十六","十七","十八","十九","二十","廿一","廿二","廿三","廿四","廿五","廿六","廿七","廿八","廿九","三十"]
CN_NUMBERS = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九"]

LUNAR_INFO = (
    0x04bd8, 0x04ae0, 0x0a570, 0x054d5, 0x0d260, 0x0d950, 0x16554, 0x056a0, 0x09ad0, 0x055d2,
    0x04ae0, 0x0a5b6, 0x0a4d0, 0x0d250, 0x1d255, 0x0b540, 0x0d6a0, 0x0ada2, 0x095b0, 0x14977,
    0x04970, 0x0a4b0, 0x0b4b5, 0x06a50, 0x06d40, 0x1ab54, 0x02b60, 0x09570, 0x052f2, 0x04970,
    0x06566, 0x0d4a0, 0x0ea50, 0x06e95, 0x05ad0, 0x02b60, 0x186e3, 0x092e0, 0x1c8d7, 0x0c950,
    0x0d4a0, 0x1d8a6, 0x0b550, 0x056a0, 0x1a5b4, 0x025d0, 0x092d0, 0x0d2b2, 0x0a950, 0x0b557,
    0x06ca0, 0x0b550, 0x15355, 0x04da0, 0x0a5b0, 0x14573, 0x052b0, 0x0a9a8, 0x0e950, 0x06aa0,
    0x0aea6, 0x0ab50, 0x04b60, 0x0aae4, 0x0a570, 0x05260, 0x0f263, 0x0d950, 0x05b57, 0x056a0,
    0x096d0, 0x04dd5, 0x04ad0, 0x0a4d0, 0x0d4d4, 0x0d250, 0x0d558, 0x0b540, 0x0b6a0, 0x195a6,
    0x095b0, 0x049b0, 0x0a974, 0x0a4b0, 0x0b27a, 0x06a50, 0x06d40, 0x0af46, 0x0ab60, 0x09570,
    0x04af5, 0x04970, 0x064b0, 0x074a3, 0x0ea50, 0x06b58, 0x055c0, 0x0ab60, 0x096d5, 0x092e0,
    0x0c960, 0x0d954, 0x0d4a0, 0x0da50, 0x07552, 0x056a0, 0x0abb7, 0x025d0, 0x092d0, 0x0cab5,
    0x0a950, 0x0b4a0, 0x0baa4, 0x0ad50, 0x055d9, 0x04ba0, 0x0a5b0, 0x15176, 0x052b0, 0x0a930,
    0x07954, 0x06aa0, 0x0ad50, 0x05b52, 0x04b60, 0x0a6e6, 0x0a4e0, 0x0d260, 0x0ea65, 0x0d530,
    0x05aa0, 0x076a3, 0x096d0, 0x04afb, 0x04ad0, 0x0a4d0, 0x1d0b6, 0x0d250, 0x0d520, 0x0dd45,
    0x0b5a0, 0x056d0, 0x055b2, 0x049b0, 0x0a577, 0x0a4b0, 0x0aa50, 0x1b255, 0x06d20, 0x0ada0,
    0x14b63, 0x09370, 0x049f8, 0x04970, 0x064b0, 0x168a6, 0x0ea50, 0x06b20, 0x1a6c4, 0x0aae0,
    0x0a2e0, 0x0d2e3, 0x0c960, 0x0d557, 0x0d4a0, 0x0da50, 0x05d55, 0x056a0, 0x0a6d0, 0x055d4,
    0x052d0, 0x0a9b8, 0x0a950, 0x0b4a0, 0x0b6a6, 0x0ad50, 0x055a0, 0x0aba4, 0x0a5b0, 0x052b0,
    0x0b273, 0x06930, 0x07337, 0x06aa0, 0x0ad50, 0x14b55, 0x04b60, 0x0a570, 0x054e4, 0x0d160,
    0x0e968, 0x0d520, 0x0daa0, 0x16aa6, 0x056d0, 0x04ae0, 0x0a9d4, 0x0a2d0, 0x0d150, 0x0f252,
)

# 节气数据
ST_DATA = {
    1900: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    1901: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1902: b'\x66\x54\x66\x66\x67\x77\x89\x89\x89\x99\x88\x88',
    1903: b'\x66\x55\x77\x66\x77\x77\x89\x99\x99\x99\x88\x88',
    1904: b'\x76\x55\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1905: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1906: b'\x66\x54\x66\x66\x67\x67\x89\x89\x89\x99\x88\x88',
    1907: b'\x66\x55\x77\x66\x77\x77\x89\x99\x99\x99\x88\x88',
    1908: b'\x76\x55\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1909: b'\x65\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1910: b'\x66\x54\x66\x66\x67\x67\x89\x89\x89\x99\x88\x88',
    1911: b'\x66\x55\x77\x66\x77\x77\x89\x99\x99\x99\x88\x88',
    1912: b'\x76\x55\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1913: b'\x65\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1914: b'\x66\x44\x66\x56\x67\x67\x89\x89\x89\x99\x88\x88',
    1915: b'\x66\x55\x67\x66\x67\x77\x89\x89\x99\x99\x88\x88',
    1916: b'\x66\x55\x66\x55\x66\x67\x78\x88\x88\x89\x87\x77',
    1917: b'\x65\x44\x66\x55\x66\x67\x88\x89\x88\x99\x88\x77',
    1918: b'\x66\x44\x66\x56\x67\x67\x89\x89\x89\x99\x88\x87',
    1919: b'\x66\x55\x67\x66\x67\x77\x89\x89\x99\x99\x88\x88',
    1920: b'\x66\x55\x66\x55\x66\x67\x78\x88\x88\x89\x87\x77',
    1921: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1922: b'\x66\x44\x66\x56\x67\x67\x89\x89\x89\x99\x88\x87',
    1923: b'\x66\x54\x66\x66\x67\x77\x89\x89\x99\x99\x88\x88',
    1924: b'\x66\x55\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1925: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1926: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1927: b'\x66\x54\x66\x66\x67\x77\x89\x89\x89\x99\x88\x88',
    1928: b'\x66\x55\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1929: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1930: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1931: b'\x66\x54\x66\x66\x67\x77\x89\x89\x89\x99\x88\x88',
    1932: b'\x66\x55\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1933: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1934: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1935: b'\x66\x54\x66\x66\x67\x67\x89\x89\x89\x99\x88\x88',
    1936: b'\x66\x55\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1937: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1938: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1939: b'\x66\x54\x66\x66\x67\x67\x89\x89\x89\x99\x88\x88',
    1940: b'\x66\x55\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1941: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1942: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1943: b'\x66\x54\x66\x66\x67\x67\x89\x89\x89\x99\x88\x88',
    1944: b'\x66\x55\x66\x55\x56\x66\x78\x88\x88\x88\x77\x77',
    1945: b'\x55\x44\x66\x55\x66\x67\x78\x88\x88\x89\x87\x77',
    1946: b'\x65\x44\x66\x55\x66\x67\x88\x89\x88\x99\x88\x87',
    1947: b'\x66\x44\x66\x56\x67\x67\x89\x89\x89\x99\x88\x88',
    1948: b'\x66\x55\x56\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    1949: b'\x55\x44\x66\x55\x66\x67\x78\x88\x88\x89\x87\x77',
    1950: b'\x65\x44\x66\x55\x66\x67\x88\x89\x88\x99\x88\x77',
    1951: b'\x66\x44\x66\x56\x67\x67\x89\x89\x89\x99\x88\x88',
    1952: b'\x66\x55\x56\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    1953: b'\x55\x44\x66\x55\x66\x67\x78\x88\x88\x89\x87\x77',
    1954: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1955: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1956: b'\x66\x55\x55\x55\x56\x66\x78\x78\x78\x88\x77\x77',
    1957: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1958: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1959: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1960: b'\x66\x54\x55\x55\x56\x66\x78\x78\x78\x88\x77\x77',
    1961: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1962: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1963: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1964: b'\x66\x54\x55\x55\x56\x66\x78\x78\x78\x88\x77\x77',
    1965: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1966: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1967: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1968: b'\x66\x54\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    1969: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1970: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1971: b'\x66\x44\x66\x56\x67\x67\x88\x89\x89\x99\x88\x87',
    1972: b'\x66\x54\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    1973: b'\x55\x44\x66\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    1974: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1975: b'\x66\x44\x66\x56\x66\x67\x88\x89\x88\x99\x88\x87',
    1976: b'\x66\x54\x55\x45\x56\x56\x78\x78\x78\x88\x77\x77',
    1977: b'\x55\x44\x66\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    1978: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x89\x88\x77',
    1979: b'\x66\x44\x66\x56\x66\x67\x88\x89\x88\x99\x88\x87',
    1980: b'\x66\x54\x55\x45\x56\x56\x78\x78\x78\x88\x77\x77',
    1981: b'\x55\x44\x66\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    1982: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x89\x87\x77',
    1983: b'\x65\x44\x66\x55\x66\x67\x88\x89\x88\x99\x88\x87',
    1984: b'\x66\x44\x55\x45\x56\x56\x77\x78\x78\x88\x77\x77',
    1985: b'\x55\x44\x56\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    1986: b'\x55\x44\x66\x55\x66\x67\x78\x88\x88\x89\x87\x77',
    1987: b'\x65\x44\x66\x55\x66\x67\x78\x89\x88\x99\x88\x77',
    1988: b'\x66\x44\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    1989: b'\x55\x43\x55\x55\x56\x66\x78\x78\x78\x88\x77\x77',
    1990: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x89\x87\x77',
    1991: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1992: b'\x66\x44\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    1993: b'\x55\x43\x55\x55\x56\x66\x78\x78\x78\x88\x77\x77',
    1994: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1995: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    1996: b'\x66\x44\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    1997: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    1998: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    1999: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    2000: b'\x66\x44\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2001: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2002: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    2003: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x99\x88\x77',
    2004: b'\x66\x44\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2005: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2006: b'\x55\x44\x66\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    2007: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x89\x88\x77',
    2008: b'\x66\x44\x55\x45\x55\x56\x77\x78\x77\x88\x77\x76',
    2009: b'\x55\x43\x55\x45\x56\x56\x78\x78\x78\x88\x77\x77',
    2010: b'\x55\x44\x66\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    2011: b'\x65\x44\x66\x55\x66\x67\x78\x88\x88\x89\x87\x77',
    2012: b'\x65\x44\x55\x44\x55\x56\x77\x78\x77\x88\x77\x76',
    2013: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x77',
    2014: b'\x55\x44\x56\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    2015: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x89\x87\x77',
    2016: b'\x65\x44\x55\x44\x55\x56\x67\x77\x77\x88\x77\x76',
    2017: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2018: b'\x55\x43\x55\x55\x56\x66\x78\x78\x78\x88\x77\x77',
    2019: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x89\x87\x77',
    2020: b'\x65\x44\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2021: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2022: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2023: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    2024: b'\x65\x44\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2025: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2026: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2027: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    2028: b'\x65\x44\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2029: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2030: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2031: b'\x55\x44\x66\x55\x66\x66\x78\x88\x88\x88\x77\x77',
    2032: b'\x65\x44\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2033: b'\x55\x33\x55\x45\x55\x56\x77\x78\x77\x88\x77\x76',
    2034: b'\x55\x43\x55\x45\x56\x56\x78\x78\x78\x88\x77\x77',
    2035: b'\x55\x44\x66\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    2036: b'\x65\x44\x55\x44\x55\x55\x67\x77\x77\x78\x77\x66',
    2037: b'\x55\x33\x55\x44\x55\x56\x77\x78\x77\x88\x77\x76',
    2038: b'\x55\x43\x55\x45\x56\x56\x77\x78\x78\x88\x77\x77',
    2039: b'\x55\x44\x66\x55\x56\x66\x78\x78\x88\x88\x77\x77',
    2040: b'\x65\x44\x55\x44\x55\x55\x67\x77\x77\x78\x76\x66',
    2041: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x76',
    2042: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x77',
    2043: b'\x55\x44\x55\x55\x56\x66\x78\x78\x78\x88\x77\x77',
    2044: b'\x55\x44\x55\x44\x55\x55\x67\x77\x77\x78\x76\x66',
    2045: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x76',
    2046: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x77',
    2047: b'\x55\x44\x55\x55\x56\x66\x78\x78\x78\x88\x77\x77',
    2048: b'\x55\x44\x55\x44\x55\x55\x67\x77\x77\x78\x76\x66',
    2049: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x76',
    2050: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x77',
    2051: b'\x55\x44\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2052: b'\x55\x44\x55\x44\x55\x55\x67\x77\x77\x78\x76\x66',
    2053: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2054: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2055: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2056: b'\x55\x44\x55\x44\x55\x55\x67\x77\x77\x77\x66\x66',
    2057: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2058: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2059: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2060: b'\x55\x44\x55\x44\x45\x55\x67\x67\x77\x77\x66\x66',
    2061: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2062: b'\x55\x33\x55\x45\x55\x56\x77\x78\x77\x88\x77\x76',
    2063: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2064: b'\x55\x44\x55\x44\x45\x55\x67\x67\x77\x77\x66\x66',
    2065: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x78\x77\x66',
    2066: b'\x55\x33\x55\x44\x55\x56\x67\x78\x77\x88\x77\x76',
    2067: b'\x55\x43\x55\x45\x56\x56\x77\x78\x78\x88\x77\x77',
    2068: b'\x55\x44\x55\x44\x45\x55\x67\x67\x77\x77\x66\x66',
    2069: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x78\x77\x66',
    2070: b'\x55\x33\x55\x44\x55\x56\x67\x78\x77\x88\x77\x76',
    2071: b'\x55\x43\x55\x45\x56\x56\x77\x78\x78\x88\x77\x77',
    2072: b'\x55\x44\x55\x44\x45\x55\x67\x67\x77\x77\x66\x66',
    2073: b'\x54\x33\x55\x44\x55\x55\x67\x77\x77\x78\x76\x66',
    2074: b'\x55\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x76',
    2075: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x77',
    2076: b'\x55\x44\x44\x44\x45\x55\x67\x67\x67\x77\x66\x66',
    2077: b'\x44\x33\x55\x44\x55\x55\x67\x77\x77\x78\x76\x66',
    2078: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x76',
    2079: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x77',
    2080: b'\x55\x44\x44\x44\x45\x45\x67\x67\x67\x77\x66\x66',
    2081: b'\x44\x33\x55\x44\x55\x55\x67\x77\x77\x78\x76\x66',
    2082: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2083: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2084: b'\x55\x44\x44\x44\x45\x45\x67\x67\x67\x77\x66\x66',
    2085: b'\x44\x33\x55\x44\x55\x55\x67\x77\x77\x78\x76\x66',
    2086: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2087: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2088: b'\x55\x44\x44\x44\x45\x45\x67\x67\x67\x77\x66\x66',
    2089: b'\x44\x33\x55\x44\x55\x55\x67\x77\x77\x77\x66\x66',
    2090: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2091: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2092: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2093: b'\x44\x33\x55\x44\x55\x55\x67\x67\x77\x77\x66\x66',
    2094: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2095: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2096: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
    2097: b'\x44\x33\x55\x44\x55\x55\x67\x67\x77\x77\x66\x66',
    2098: b'\x54\x33\x55\x44\x55\x56\x67\x77\x77\x88\x77\x66',
    2099: b'\x55\x33\x55\x45\x56\x56\x77\x78\x78\x88\x77\x76',
    2100: b'\x55\x43\x55\x55\x56\x56\x78\x78\x78\x88\x77\x77',
}

class SSD1683_Calendar:
    """
    SSD1683 电子墨水屏日历库
    支持显示指定年月或当前月的日历，包含农历、节气、天气、月相、三伏和数九
    """
    
    # 屏幕布局常量
    SCREEN_W = 400
    SCREEN_H = 300
    TOP_H = 50
    WEEK_H = 20
    DATE_ROWS = 5
    CELL_W = SCREEN_W // 7
    DATE_ROW_H = (SCREEN_H - TOP_H - WEEK_H) // DATE_ROWS



    def __init__(self):
        """简化初始化：自动使用全局导入的依赖"""
        self.epd = epd
        self.buf_black = buf_black
        self.buf_red = buf_red
        self.fb_black = fb_black
        self.fb_red = fb_red
        self.draw_mixed_text = draw_mixed_text
        self.image_data = image_data
        self.get_localtime = get_localtime
        self.holidays = {}
        self.YANGLI_JIERI = YANGLI_JIERI
        self.NONGLI_JIERI = NONGLI_JIERI

    # ======================== 内部工具函数 ========================
    @staticmethod
    def _get_abs_days(y, m, d):
        if m < 3:
            y -= 1
            m += 12
        return 365*y + y//4 - y//100 + y//400 + (153*m - 457)//5 + d - 306

    @staticmethod
    def _abs_days_to_date(abs_days):
        low, high = 1900, 2100
        y = 1900
        while low <= high:
            mid = (low + high) // 2
            mid_abs = SSD1683_Calendar._get_abs_days(mid, 1, 1)
            if mid_abs <= abs_days:
                y = mid
                low = mid + 1
            else:
                high = mid - 1
        
        y_abs = SSD1683_Calendar._get_abs_days(y, 1, 1)
        day_of_year = abs_days - y_abs + 1
        
        m = 1
        while m <= 12:
            dim = SSD1683_Calendar._get_days_in_month(y, m)
            if day_of_year <= dim:
                break
            day_of_year -= dim
            m += 1
        return (y, m, day_of_year)

    @staticmethod
    def _get_days_in_month(y, m):
        if m in (4, 6, 9, 11): return 30
        if m == 2: return 29 if (y%4==0 and y%100!=0) or (y%400==0) else 28
        return 31

    @staticmethod
    def _get_weekday_of_first_day(y, m):
        abs_day = SSD1683_Calendar._get_abs_days(y, m, 1)
        return (abs_day - SSD1683_Calendar._get_abs_days(1970, 1, 1) + 3) % 7

    @staticmethod
    def _estimate_text_width(s, size):
        w = 0
        for c in s:
            if '\u4e00' <= c <= '\u9fff':
                w += size
            else:
                w += size//2
        return w

    def _get_lunar_date(self, gy, gm, gd):
        base = self._get_abs_days(1900, 1, 31)
        now = self._get_abs_days(gy, gm, gd)
        offset = now - base
        ly = 1900
        
        while offset >= 365:
            info = LUNAR_INFO[ly-1900]
            ylen = 348
            for i in range(15, 3, -1):
                ylen += 1 if (info >> i) & 1 else 0
            leap = info & 0xf
            if leap:
                ylen += 30 if (info >> 16) & 1 else 29
            if offset < ylen:
                break
            offset -= ylen
            ly += 1

        info = LUNAR_INFO[ly-1900]
        leap = info & 0xf
        lm = 1
        is_leap = False
        
        for m in range(1, 13):
            mlen = 30 if (info >> (16 - m)) & 1 else 29
            if offset < mlen:
                break
            offset -= mlen
            
            if m == leap:
                mlen2 = 30 if (info >> 16) & 1 else 29
                if offset < mlen2:
                    is_leap = True
                    break
                offset -= mlen2
            lm += 1
            
        ld = offset + 1
        
        return {
            "l_year": ly,
            "l_month": lm,
            "l_day": ld,
            "is_leap": is_leap
        }

    def _get_term_precise(self, y, m, d):
        if y not in ST_DATA:
            return ""
        b = ST_DATA[y][m-1]
        d1 = b >> 4
        d2 = (b & 0x0f) + 15
        if d == d1:
            return SOLAR_TERMS[(m-1)*2]
        if d == d2:
            return SOLAR_TERMS[(m-1)*2+1]
        return ""
    
    def _get_solar_term_date(self, year, term_name):
        try:
            term_index = SOLAR_TERMS.index(term_name)
            month = (term_index // 2) + 1
            for day in range(1, 32):
                if self._get_term_precise(year, month, day) == term_name:
                    return (year, month, day)
        except ValueError:
            pass
        return None

    def _get_gan_zhi_zodiac(self, lunar_year):
        gan_index = (lunar_year - 4) % 10
        zhi_index = (lunar_year - 4) % 12
        gan = TIAN_GAN[gan_index]
        zhi = DI_ZHI[zhi_index]
        zodiac = ZODIAC[zhi_index]
        return f"{gan}{zhi}{zodiac}年"

    # ======================== 数九与三伏计算 ========================
    
    def _find_geng_day(self, start_abs, nth):
        count = 0
        current_abs = start_abs
        base_abs = self._get_abs_days(1900, 1, 31)
        while True:
            offset = current_abs - base_abs
            if (offset + 40) % 10 == 6:
                count += 1
                if count == nth:
                    return current_abs
            current_abs += 1

    def _get_shu_jiu(self, y, m, d):
        winter_year = y if m >= 12 else y - 1
        winter = self._get_solar_term_date(winter_year, "冬至")
        if not winter: return None
        
        w_abs = self._get_abs_days(*winter)
        t_abs = self._get_abs_days(y, m, d)
        delta = t_abs - w_abs
        
        if 0 <= delta < 81 and delta % 9 == 0:
            n = delta // 9 + 1
            return f"{CN_NUMBERS[n]}九"
        return None

    def _get_san_fu(self, y, m, d):
        if m < 6 or m > 8:
            return None
            
        xiazhi = self._get_solar_term_date(y, "夏至")
        liqiu = self._get_solar_term_date(y, "立秋")
        
        if not xiazhi or not liqiu:
            return None
            
        abs_xiazhi = self._get_abs_days(*xiazhi)
        abs_liqiu = self._get_abs_days(*liqiu)
        
        abs_chufu = self._find_geng_day(abs_xiazhi, 3)
        abs_zhongfu = self._find_geng_day(abs_xiazhi, 4)
        abs_mofu = self._find_geng_day(abs_liqiu, 1)
        
        abs_target = self._get_abs_days(y, m, d)
        
        if abs_target == abs_chufu: return "入伏"
        if abs_target == abs_zhongfu: return "中伏"
        if abs_target == abs_mofu: return "末伏"
        
        return None

    # ======================== 节假日加载函数 ========================
    def _load_holidays(self, year):
        filename = f"holidays_{year}.json"
        self.holidays = {}
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                self.holidays = json.load(f)
            print(f"✅ 已加载节假日数据: {filename}")
        except OSError:
            print(f"ℹ️ 未找到节假日文件: {filename}，将使用默认周末规则")
        except Exception as e:
            print(f"⚠️ 解析节假日文件出错: {e}")

    # ======================== 绘制逻辑 ========================
    def _clear(self):
        self.fb_black.fill(0xFF)
        self.fb_red.fill(0x00)

    def _draw_header(self, year, month, real_dt):
        #self.fb_black.hline(0, 50, 400, 0)
        
        month_str = f"{month:02d}"
        self.draw_mixed_text(str(year), 5, 9, size=32, overlap=True, color="black")
        self.draw_mixed_text("年", 76, 21, size=12, overlap=True, color="black")
        self.draw_mixed_text(month_str, 91, 9, size=32, overlap=True, color="black")
        self.draw_mixed_text("月", 126, 21, size=12, overlap=True, color="black")

        info_start_x = 142
        font_size = 12
        is_current_month = (real_dt[0] == year and real_dt[1] == month)
        
        if is_current_month:
            lunar_info_today = self._get_lunar_date(real_dt[0], real_dt[1], real_dt[2])
            gan_zhi_str = self._get_gan_zhi_zodiac(lunar_info_today["l_year"])
            self.draw_mixed_text(gan_zhi_str, info_start_x, 8, size=font_size, overlap=True, color="black")
            
            lunar_date_str = f"{LUNAR_MONTHS[lunar_info_today['l_month']-1]}月{LUNAR_DATES[lunar_info_today['l_day']-1]}"
            self.draw_mixed_text(lunar_date_str, info_start_x, 28, size=font_size, overlap=True, color="black")
        else:
            lunar_info_first_day = self._get_lunar_date(year, month, 1)
            gan_zhi_str = self._get_gan_zhi_zodiac(lunar_info_first_day["l_year"])
            self.draw_mixed_text(gan_zhi_str, info_start_x, 19, size=font_size, overlap=True, color="black")

    def _draw_weekdays(self):
        # 星期顺序：日一二三四五六
        WEEK_NAMES = ["日","一","二","三","四","五","六"]
        WEEK_START_Y = self.TOP_H
        WEEK_FONT_SIZE = 16
        for i in range(7):
            cell_x = i * self.CELL_W
            cell_y = WEEK_START_Y
            cell_w = self.CELL_W
            cell_h = self.WEEK_H
            if i == 6:
                cell_w = self.SCREEN_W - cell_x

            # 样式：周六/周日红底白字，周一到周五黑底白字
            if i == 0 or i == 6:
                # 周末：红底白字
                self.fb_red.fill_rect(cell_x, cell_y, cell_w, cell_h, 0xFF)
                text_color = "white"
            else:
                # 工作日：黑底白字
                self.fb_black.fill_rect(cell_x, cell_y, cell_w, cell_h, 0x00)
                text_color = "bw_white"

            # 居中绘制文字，确保垂直+水平居中
            txt = WEEK_NAMES[i]
            txt_width = self._estimate_text_width(txt, WEEK_FONT_SIZE)
            tx = cell_x + (cell_w - txt_width) // 2
            ty = cell_y + (cell_h - WEEK_FONT_SIZE) // 2
            self.draw_mixed_text(txt, tx, ty, size=WEEK_FONT_SIZE, overlap=True, color=text_color)
        # 星期行底部横线
        #self.fb_black.hline(0, WEEK_START_Y + self.WEEK_H, 400, 0)

    def _draw_dates(self, year, month, today, days_total, first_day_week):
        DATE_START_Y = self.TOP_H + self.WEEK_H
        SOLAR_FONT_SIZE = 24
        LUNAR_FONT_SIZE = 12
        
        # 间距参数定义
        CHAR_GAP = -1
        WORD_GAP = 0

        # 适配周日为首列的日期排布
        first_col = (first_day_week + 1) % 7
        grid = [[None]*7 for _ in range(5)]
        day = 1
        for row in range(5):
            for col in range(7):
                if row == 0 and col < first_col:
                    continue
                if day > days_total:
                    break
                grid[row][col] = day
                day += 1
            if day > days_total:
                break

        day_overflow = day
        if day_overflow <= days_total:
            for col in range(7):
                if grid[0][col] is None and day_overflow <= days_total:
                    grid[0][col] = day_overflow
                    day_overflow += 1

        for row in range(5):
            for col in range(7):
                d = grid[row][col]
                if d is None:
                    continue
                
                cell_x = col * self.CELL_W
                cell_y = DATE_START_Y + row * self.DATE_ROW_H
                
                lunar = self._get_lunar_date(year, month, d)
                is_today = (d == today)
                
                # 当日：先填充完整红底
                if is_today:
                    self.fb_red.fill_rect(cell_x, cell_y, self.CELL_W, self.DATE_ROW_H, 0xFF)

                # 非当日日期颜色判断
                date_key = f"{year}-{month:02d}-{d:02d}"
                text_color = "black"
                
                if date_key in self.holidays:
                    if self.holidays[date_key].get("isOffDay"):
                        text_color = "red"
                    else:
                        text_color = "black"
                else:
                    # 周日(col0)、周六(col6)为红色
                    if col == 0 or col == 6:
                        text_color = "red"
                
                # 当日统一使用白字
                draw_color = "white" if is_today else text_color

                # 绘制公历日期
                solar_txt = str(d)
                solar_width = self._estimate_text_width(solar_txt, SOLAR_FONT_SIZE)
                solar_tx = cell_x + (self.CELL_W - solar_width) // 2
                solar_ty = cell_y + 2
                self.draw_mixed_text(solar_txt, solar_tx, solar_ty, size=SOLAR_FONT_SIZE, overlap=True, color=draw_color)

                # 标签收集
                special_tags = []
                term = self._get_term_precise(year, month, d)
                if term: special_tags.append(term)
                
                yangli_key = f"{month}{d:02d}"
                if yangli_key in self.YANGLI_JIERI: special_tags.append(self.YANGLI_JIERI[yangli_key])
                
                nongli_key = f"{lunar['l_month']}{lunar['l_day']:02d}"
                if nongli_key in self.NONGLI_JIERI: special_tags.append(self.NONGLI_JIERI[nongli_key])
                
                # 除夕判断
                today_abs = self._get_abs_days(year, month, d)
                tomorrow_abs = today_abs + 1
                (y_tom, m_tom, d_tom) = self._abs_days_to_date(tomorrow_abs)
                lunar_tomorrow = self._get_lunar_date(y_tom, m_tom, d_tom)
                if lunar_tomorrow["l_month"] == 1 and lunar_tomorrow["l_day"] == 1:
                    special_tags.append("除夕")
                
                shu_jiu = self._get_shu_jiu(year, month, d)
                if shu_jiu: special_tags.append(shu_jiu)
                san_fu = self._get_san_fu(year, month, d)
                if san_fu: special_tags.append(san_fu)

                # 农历/标签绘制，当日统一白字
                if is_today:
                    final_color = "white"
                else:
                    final_color = "red" if special_tags else text_color
                lunar_ty = solar_ty + SOLAR_FONT_SIZE - 2
                
                if special_tags:
                    # 计算总宽度居中
                    total_width = 0
                    for i, tag in enumerate(special_tags):
                        if i > 0:
                            total_width += WORD_GAP
                        for char in tag:
                            if '\u4e00' <= char <= '\u9fff':
                                total_width += LUNAR_FONT_SIZE
                            else:
                                total_width += LUNAR_FONT_SIZE // 2
                            total_width += CHAR_GAP
                    if total_width > 0:
                        total_width -= CHAR_GAP

                    current_x = cell_x + (self.CELL_W - total_width) // 2
                    
                    # 逐字绘制
                    for i, tag in enumerate(special_tags):
                        if i > 0:
                            current_x += WORD_GAP
                        
                        for char in tag:
                            self.draw_mixed_text(char, current_x, lunar_ty, size=LUNAR_FONT_SIZE, overlap=True, color=final_color)
                            
                            if '\u4e00' <= char <= '\u9fff':
                                current_x += LUNAR_FONT_SIZE
                            else:
                                current_x += LUNAR_FONT_SIZE // 2
                            
                            current_x += CHAR_GAP
                else:
                    # 普通农历日期
                    if lunar["l_day"] == 1:
                        leap_str = "闰" if lunar["is_leap"] else ""
                        final_txt = "{}{}月".format(leap_str, LUNAR_MONTHS[lunar["l_month"]-1])
                    else:
                        final_txt = LUNAR_DATES[lunar["l_day"]-1]
                    
                    lunar_width = self._estimate_text_width(final_txt, LUNAR_FONT_SIZE)
                    lunar_tx = cell_x + (self.CELL_W - lunar_width) // 2
                    self.draw_mixed_text(final_txt, lunar_tx, lunar_ty, size=LUNAR_FONT_SIZE, overlap=True, color=final_color)

    def _load_and_draw_weather_text(self):
        weather_icon = None
        try:
            with open("weather_now.json", 'r') as f:
                data = json.loads(f.read())
            
            if data.get("code") == "200":
                now = data.get("now", {})
                temp = now.get("temp")
                icon = now.get("icon")
                text = now.get("text")
                windDir = now.get("windDir")
                windScale = now.get("windScale")
                
                self.draw_mixed_text(text + " " + temp + "℃", 250, 9, size=16, overlap=True, color="black")
                self.draw_mixed_text(windDir + " " + windScale + "级", 250, 30, size=16, overlap=True, color="black")
                
                weather_icon = icon
        except Exception as e:
            print(f"Weather text error: {e}")
        return weather_icon

    def _load_and_draw_moon_icon(self):
        moon_icon = None
        try:
            with open("moon_phase.json", 'r', encoding="utf-8") as f:
                data = json.loads(f.read())
            
            if data.get("code") == "200":
                moon = data.get("moonPhase", [])
                if moon:
                    moon_icon = moon[0].get("icon")
        except Exception as e:
            print(f"Moon load error: {e}")
        return moon_icon

    # ======================== 公共API ========================
    def show(self, year=None, month=None):
        real_dt = self.get_localtime(8)
        
        if year is None or month is None:
            target_y = real_dt[0] if year is None else year
            target_m = real_dt[1] if month is None else month
        else:
            target_y = year
            target_m = month
            
        today_day = real_dt[2] if (target_y == real_dt[0] and target_m == real_dt[1]) else None

        days_total = self._get_days_in_month(target_y, target_m)
        first_day_week = self._get_weekday_of_first_day(target_y, target_m)

        self._load_holidays(target_y)

        self._clear()
        self._draw_header(target_y, target_m, real_dt)
        self._draw_weekdays()
        self._draw_dates(target_y, target_m, today_day, days_total, first_day_week)
        
        self.epd.write_buffer(self.buf_black, False)
        self.epd.write_buffer(self.buf_red, True)

        weather_icon = self._load_and_draw_weather_text()
        self.epd.write_buffer(self.buf_black, False)
        self.epd.write_buffer(self.buf_red, True)

        if weather_icon and weather_icon in self.image_data:
            self.epd.write_partial_buffer(
                data=self.image_data[weather_icon], x=208, y=9, w=32, h=32, is_red=False
            )
            
        moon_icon = self._load_and_draw_moon_icon()
        if moon_icon and moon_icon in self.image_data:
            self.epd.write_partial_buffer(
                data=self.image_data[moon_icon], x=360, y=9, w=32, h=32, is_red=False
            )

        self.epd.refresh()
        print(f"✅ 日历绘制完成: {target_y}年{target_m}月")

# ======================== 快捷函数 ========================
def show_calendar(year=None, month=None):
    calendar = SSD1683_Calendar()
    calendar.show(year=year, month=month)
