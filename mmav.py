#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import platform
import requests
import shutil
import json
from time import sleep
from timeit import default_timer
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup

__version__ = "v2.1.0"

class Maomiav():

    __list = [
        ("/tupian/list-自拍偷拍", "自拍偷拍"),
        ("/tupian/list-亚洲色图", "亚洲色图"),
        ("/tupian/list-欧美色图", "欧美色图"),
        ("/tupian/list-美腿丝袜", "美腿丝袜"),
        ("/tupian/list-清纯唯美", "清纯唯美"),
        ("/tupian/list-乱伦熟女", "乱伦熟女"),
        ("/tupian/list-卡通动漫", "卡通动漫"),
    ]
    parts = OrderedDict([(str(k), v) for k, v in enumerate(__list, 1)])
    fjson = "settings.json"

    def __init__(self, bs4_parser, sysstr):
        self.bs4_parser = bs4_parser
        self.sysstr = sysstr

        self.saved_settings = read_from_json(self.fjson)
        self.threads_num = self.saved_settings.get("max_threads_num", 16)
        self.req_timeout = self.saved_settings.get("request_timeout", 15)
        self.default_part = self.saved_settings.get("default_part", "5")
        self.proxies = self.saved_settings.get("http_proxies", "")
        self.proxies_global = self.saved_settings.get("proxies_global", True)
        self.dload_tips = self.saved_settings.get("download_tips_all", True)

        self.sel_part = self.default_part

        self.page_no = 1
        self.last_page_no = 1
        self.__init2()

    def __init2(self):
        # 最大尝试次数
        __MAX_TRY_NUM = 5
        try_num = 1
        while try_num <= __MAX_TRY_NUM:
            os_clear_screen(self.sysstr)
            self.use_proxies = {"http": self.proxies, "https": self.proxies}
            print_in("正在获取最新的链接(第 %s 次尝试)..." % try_num)
            self.url = self.get_url()
            if self.url:
                print_in("已获取最新链接: " + self.url)
                # 蛤?
                sleep(1)
                if not self.proxies_global:
                    self.use_proxies = {"http": "", "https": ""}
                return
            sleep(0.5)
            try_num += 1
        print_an("Emmm... 尽管尝试了很多次, 但还是没能成功获取链接-_-!")
        print_an("请检查你的网络连接情况, 或者稍候再试？"
                 "(对了如果科学上网的话成功率会大大提高哟~)")
        if input_an("输入 \"S\" 进入设置菜单, 输入其他则退出: ").upper() == "S":
            self.set_settings()
            return self.__init2()

    def run(self, goto_sel_item_flag=False):
        os_clear_screen(self.sysstr)
        if not self.url:
            return
        urll = self.url + self.parts[self.sel_part][0]
        if self.page_no > 1:
            url_page = "-%s" % self.page_no
        else:
            url_page = ""
        print_in("正在请求页面并解析, 请稍候...")
        bsObj = self.get_bs(urll + url_page + ".html", self.bs4_parser)
        if not bsObj:
            self.open_failed(urll + url_page)
            temp = input_an("输入 \"0\" 重试, 输入 \"S\" 进入设置菜单,"
                            " 输入其他则退出: ")
            if temp == "0":
                return self.run()
            if temp.upper() == "S":
                self.set_settings()
                return self.run()
            return
        print_in("正在解析页面...")
        try:
            id_attr = "tpl-img-content"
            nb = bsObj.find("div", {"id": id_attr}).find_all("li")
            if self.page_no == 1:
                try:
                    lp = bsObj.find("div", {"class": "pagination"}) \
                                    .find_all("a")[-1]["href"]
                    self.last_page_no = int(
                        lp[lp.rindex("-") + 1:lp.rindex(".")])
                except:
                    pass
        except:
            self.analyze_failed(urll + url_page)
            return input_an("请按回车键退出: ")
        threads = []
        for thread in nb:
            try:
                threads.append(self.get_threads(thread))
            except:
                continue
        # 蛤?
        sleep(1)
        if goto_sel_item_flag:
            self.sel_item_init(threads)
        self.main_(threads)

    def main_(self, threads):
        while True:
            os_clear_screen(self.sysstr)
            self.show_title()
            print_in("当前图区: " + self.parts[self.sel_part][1])
            print_in("当前页码: " + str(self.page_no))
            print_in("选择操作:")
            print_l("1.爬取此页面下的所有项目")
            print_l("2.浏览项目列表并选择其中一项爬取")
            if self.page_no != 1:
                print_l("8.← 上一页")
            if self.page_no != self.last_page_no:
                print_l("9.→ 下一页")
            print_l("I.跳页")
            print_l("R.刷新页面")
            print_l("X.切换图区")
            print_l("S.程序设置")
            print_l("E.退出")
            temp = input_an("请输入选项并按回车键: ")
            if temp == "1":
                self.get_page_pics(threads)
            if temp == "2":
                self.sel_item_init(threads)
            if temp == "8" and self.page_no != 1:
                self.page_no -= 1
                return self.run()
            if temp == "9" and self.page_no != self.last_page_no:
                self.page_no += 1
                return self.run()
            if temp.upper() == "I":
                print_in("输入其他则返回:")
                try:
                    temp2 = int(input_an("范围: 1 ~ %s : " % self.last_page_no))
                except ValueError:
                    continue
                if temp2 < 1 or temp2 > self.last_page_no:
                    continue
                self.page_no = temp2
                return self.run()
            # Special
            if temp.upper() == "Z":
                self.page_flag = False
                sp_item = {}
                sp_item["date"] = "Special"
                sp_item["link"] = \
                    input_an("请输入页面链接(链接不正确可能会失败哟): ")
                sp_item["title"] = "unnamed"
                os_clear_screen(self.sysstr)
                print_()
                self.get_item_pics(sp_item)
            if temp.upper() == "X":
                if self.sel_pic_part():
                    return self.run()
            if temp.upper() == "S":
                if self.set_settings():
                    return self.run()
            if temp.upper() == "R":
                return self.run()
            if temp.upper() == "E":
                os_clear_screen(self.sysstr)
                sys.exit()

    def get_threads(self, thread):
        return {
            "title": self.adj_dir_name(thread.find("a")["title"]),
            "date": thread.find("a").find("span").get_text().strip()[5:],
            "link": self.url + thread.find("a")["href"]
        }

    def get_page_pics(self, threads):
        os_clear_screen(self.sysstr)
        num = 1
        self.page_flag = True
        page_time_start = default_timer()
        time_cost_all = 0
        for child in threads:
            print_in("开始下载第 %s 项, 共 %s 项" % (num, len(threads)))
            print_i()
            exit_flag = self.get_item_pics(child)
            if exit_flag == "break":
                print_an("任务已被用户终止!")
                break
            elif exit_flag == "pass":
                print_an("已跳过 %s !" % child["title"])
            elif exit_flag in ("timeout", "analyze_failed"):
                print_an("%s 下载失败!" % child["title"])
            else:
                time_cost_all += exit_flag
            num += 1
            # 稍作休息
            try:
                sleep(2)
            except KeyboardInterrupt:
                print_an("任务已被用户终止!")
                break
        page_time_cost = default_timer() - page_time_start
        self.page_flag = False
        print_in("下载任务已全部完成! "
                 "下载总计耗时 %i 分 %i 秒, 实际耗时 %i 分 %i 秒"
                 % (time_cost_all // 60, time_cost_all % 60,
                    page_time_cost // 60, page_time_cost % 60))
        return input_an("请按回车键返回主界面: ")

    def get_item_pics(self, item):
        mkdir("下载保存目录", False)
        if item["date"] == "Special":
            dir_2 = os.path.join("下载保存目录", "Special")
        else:
            dir_1 = os.path.join("下载保存目录", self.parts[self.sel_part][1])
            if item["date"]:
                mkdir(dir_1, False)
                dir_2 = os.path.join(dir_1, item["date"])
            else:
                dir_2 = dir_1
        mkdir(dir_2, False)
        dir_3 = os.path.join(dir_2, item["title"])
        if not mkdir(dir_3):
            if self.page_flag:
                temp2 = input_an("输入 \"0\" 则跳过, 输入 \"e\" 则跳过"
                                 "之后所有的项目, 否则将清空此目录重新下载: ")
                if temp2 == "0":
                    return "pass"
                if temp2.upper() == "E":
                    return "break"
            else:
                temp2 = input_an("输入 \"0\" 取消下载,"
                                 " 否则将清空此目录重新下载: ")
                if temp2 == "0":
                    return
            clean_dir(dir_3)
        bsObj = self.get_bs(item["link"], self.bs4_parser)
        if not bsObj:
            self.open_failed(item["link"])
            if self.page_flag:
                return "timeout"
            return input_an("下载失败! 请按回车键返回主界面: ")
        try:
            pics = bsObj.find("div", {"class": "content"}).find_all("img")
            if item["title"] == "unnamed":
                item["title"] = self.adj_dir_name(
                    bsObj.find("div", {"class": "page_title"}).get_text())
                dir_3_o = dir_3
                dir_3 = os.path.join(dir_2, item["title"])
                fmove(dir_3_o, dir_3)
        except:
            self.analyze_failed(item["link"])
            if self.page_flag:
                return "analyze_failed"
            return input_an("下载失败! 请按回车键返回主界面: ")
        print_i()
        print_i("开始下载 " + item["title"])
        print_i("共 %s 张" % len(pics))
        time_start = default_timer()
        dload_file_all(
            self.threads_num,
            (self.dload_tips, dir_3, self.proxies, self.req_timeout),
            pics
        )
        time_cost_all = default_timer() - time_start
        print_i()
        print_i("%s 下载已完成! 总耗时 %.3f 秒"
                % (item["title"], time_cost_all))
        if self.page_flag:
            return time_cost_all
        return input("\n=== 任务已完成!\n\n*** 请按回车键返回主界面: ")

    def sel_item_init(self, threads):
        self.page_flag = False
        while True:
            temp2 = self.sel_item(threads)
            if not temp2:
                break
            os_clear_screen(self.sysstr)
            print_()
            self.get_item_pics(threads[int(temp2) - 1])

    def sel_item(self, threads):
        while True:
            os_clear_screen(self.sysstr)
            print_in("当前图区: " + self.parts[self.sel_part][1])
            print_in("当前页码: " + str(self.page_no))
            num = 1
            for child in threads:
                print_in("%2s: %s %s"
                         % (num, child["date"], child["title"]))
                num += 1
            print_an("请输入你想要下载的项目标号")
            temp = input_an("输入 \"+\" 或 \"-\" 可直接翻页,"
                            " 输入 \"0\" 则返回: ")
            if temp == "0":
                return
            if temp == "-" and self.page_no != 1:
                self.page_no -= 1
                return self.run(goto_sel_item_flag=True)
            if temp == "+" and self.page_no != self.last_page_no:
                self.page_no += 1
                return self.run(goto_sel_item_flag=True)
            if temp in [str(a) for a in range(1, len(threads) + 1)]:
                return temp

    def set_settings(self):
        reset_flag_1 = False
        while True:
            os_clear_screen(self.sysstr)
            print_in("程序设置:")
            print_l("1.设置下载最大线程数 (当前: %s 线程)" % self.threads_num)
            print_l("2.设置请求超时 (当前: %s 秒)" % self.req_timeout)
            print_l("3.设置默认图区 (当前: %s)"
                    % self.parts[self.default_part][1])
            print_l("4.代理配置")
            print_l("5.下载提醒 (当前: ", end="")
            if self.dload_tips:
                print_("显示所有下载结果)")
            else:
                print_("仅显示下载失败的文件)")
            print_l("0.返回")
            temp = input_an("请输入选项并按回车键: ")
            if temp == "1":
                self.set_threads_num()
            if temp == "2":
                self.set_req_timeout()
            if temp == "3":
                self.set_default_part()
            if temp == "4":
                reset_flag_1 = self.set_proxies()
            if temp == "5":
                self.set_dload_tips()
            if temp == "0":
                # 保存设置
                save_to_json(self.saved_settings, self.fjson)
                return reset_flag_1

    def set_threads_num(self):
        self.threads_num = \
            self.set_index({"1": 4, "2": 8, "3": 16, "4": 32},
                           "线程",
                           "更低的线程数将降低下载失败的概率, "
                           "更高的线程数将提升下载速度, 推荐 16 线程",
                           "设置最大下载线程数")
        self.saved_settings["max_threads_num"] = self.threads_num

    def set_req_timeout(self):
        self.req_timeout = \
            self.set_index({"1": 5, "2": 10, "3": 15, "4": 30},
                           "秒",
                           "对于网络环境较差的用户, "
                           "提高超时时间可以降低下载失败的概率...或许",
                           "设置请求超时")
        self.saved_settings["request_timeout"] = self.req_timeout

    def set_default_part(self):
        while True:
            os_clear_screen(self.sysstr)
            print_in("设置打开程序后默认所在的图区:")
            for k, v in self.parts.items():
                print_l("%s: %s" % (k, v[1]))
            temp = input_an("请输入选项并按回车键: ")
            if temp in self.parts.keys():
                self.default_part = temp
                self.saved_settings["default_part"] = self.default_part
                return

    def set_dload_tips(self):
        self.dload_tips = not self.dload_tips
        self.saved_settings["download_tips_all"] = self.dload_tips

    def set_index(self, dic, unit, info, info_2=""):
        while True:
            os_clear_screen(self.sysstr)
            print_in("Tip: " + info)
            if info_2:
                print_in(info_2 + ":")
            for k in sorted(dic.keys()):
                print_l("%s: %-2s %s" % (k, dic[k], unit))
            temp = input_an("请输入选项并按回车键: ")
            if temp in dic.keys():
                return dic[temp]

    def set_proxies(self):
        reset_flag_2 = False
        while True:
            os_clear_screen(self.sysstr)
            print_in("当前使用的代理: ", end="")
            if self.proxies:
                print_(self.proxies)
            else:
                print_("未使用")
            print_in("代理模式: ", end="")
            if self.proxies_global:
                print_("全局")
            else:
                print_("仅用于获取链接")
            print_in("选择操作:")
            print_l("1.设置 HTTP 代理服务器")
            print_l("2.不使用代理")
            print_l("3.设置代理模式")
            print_l("0.返回")
            temp = input_an("请输入选项并按回车键: ")
            if temp == "1":
                proxies_address = input_an("请输入 HTTP 代理地址"
                                           "(留空则默认为 127.0.0.1): ")
                if not proxies_address.strip():
                    proxies_address = "127.0.0.1"
                while True:
                    try:
                        proxies_port = int(input_an("输入代理端口"
                                                    "(范围: 0 ~ 65535): "))
                    except ValueError:
                        print_an("输入有误! 请重新输入")
                    else:
                        if 0 <= proxies_port <= 65535:
                            break
                        print_an("输入有误! 请重新输入")
                self.proxies = "%s:%s" % (proxies_address, proxies_port)
                self.saved_settings["http_proxies"] = self.proxies
                print_in("代理已配置为 " + self.proxies)
                reset_flag_2 = True
                sleep(2)
            if temp == "2":
                self.proxies = ""
                self.saved_settings["http_proxies"] = ""
                print_in("已禁用代理")
                reset_flag_2 = True
                sleep(2)
            if temp == "3":
                print_in("你决定何时使用代理？")
                proxies_when = input_an("如果希望只在获取链接时使用, 请输入0, "
                                        "否则将全局使用代理(默认): ")
                self.proxies_global = (proxies_when != "0")
                self.saved_settings["proxies_global"] = self.proxies_global
            if temp == "0":
                if self.proxies_global:
                    self.use_proxies = {"http": self.proxies,
                                        "https": self.proxies}
                else:
                    self.use_proxies = {"http": "", "https": ""}
                return reset_flag_2

    def sel_pic_part(self):
        # 切换图区
        while True:
            os_clear_screen(self.sysstr)
            print_in("当前图区:" + self.parts[self.sel_part][1])
            print_in("所有图区:")
            for k, v in self.parts.items():
                print_l("%s: %s" % (k, v[1]))
            temp3 = input_an("请输入你要进入的图区编号(输入 \"0\" 则返回): ")
            if temp3 in self.parts.keys():
                self.sel_part = temp3
                self.page_no = 1
                self.last_page_no = 1
                return temp3
            if temp3 == "0":
                return

    def get_url(self):
        # 使用一种非常巧妙的方法获取页面跳转后的新url地址
        try:
            real_url = requests.get("http://www.mumu98.com",
                                    timeout=self.req_timeout,
                                    proxies=self.use_proxies).url
            if real_url.endswith("/"):
                return real_url[:-1]
            return real_url
        except:
            return

    def get_bs(self, urll, bs4_parser):
        # 使用浏览器 UA 来请求页面
        headers = {
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Apple"
                           "WebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3"
                           "202.94 Safari/537.36")
        }
        try:
            req = requests.get(url=urll, headers=headers,
                               timeout=self.req_timeout,
                               proxies=self.use_proxies)
            req.encoding = "utf-8"
            return BeautifulSoup(req.text, bs4_parser)
        except:
            return

    @staticmethod
    def adj_dir_name(dir_name):
        for char in ("?", "/", "\\", ":", "*", "\"", "<", ">", "|"):
            dir_name = dir_name.replace(char, "")
        return dir_name

    @staticmethod
    def open_failed(real_name=None):
        if real_name:
            print_n(real_name + os.linesep)
        print_a("请求失败或连接超时!")

    @staticmethod
    def analyze_failed(real_name=None):
        if real_name:
            print_n(real_name + os.linesep)
        print_a("页面解析失败!")

    @staticmethod
    def show_title():
        print_()
        print_("=" * 36)
        print_("===" + " " * 30 + "===")
        print_("===  猫咪 AV 图片爬取脚本 %6s ===" % __version__)
        print_("===" + " " * 30 + "===")
        print_("===" + " " * 21 + "By Pzqqt ===")
        print_("===" + " " * 30 + "===")
        print_("=" * 36)

def dload_file_all(max_threads_num, pars, pics):
    # 神奇的多线程下载
    with ThreadPoolExecutor(max_threads_num) as executor1:
        executor1.map(dload_file, [pars] * len(pics),
                                  [c["data-original"] for c in pics])

def dload_file(pars, url):
    # 下载文件
    dload_tips, save_path, proxies, req_timeout = pars
    file_name = url.split("/")[-1]
    try:
        r = requests.get(url, timeout=req_timeout,
                         proxies={"http": proxies, "https": proxies})
    except:
        try:
            r = requests.get(url, timeout=15,
                             proxies={"http": proxies, "https": proxies})
        except:
            return print_a("%s 下载失败! " % file_name)
    with open(file_name, 'wb') as f:
        f.write(r.content)
    fmove(file_name,
          os.path.join(os.path.abspath('.'), save_path, file_name))
    if dload_tips:
        print_i("%s 下载成功! " % file_name)

def clean_dir(path):
    # 清空文件夹
    ls = os.listdir(path)
    for i in ls:
        c_path = os.path.join(path, i)
        if os.path.isdir(c_path):
            clean_dir(c_path)
        else:
            os.remove(c_path)

def mkdir(path, print_flag=True):
    # 创建目录
    if os.path.exists(os.path.join(os.path.abspath('.'), path)):
        if print_flag:
            print_a(path + " 目录已存在!")
        return False
    else:
        os.makedirs(path)
        print_i(path + " 创建成功")
        return True

def fmove(srcfile, dstfile):
    # 移动/重命名文件或目录
    if not (os.path.isfile(srcfile) or os.path.isdir(srcfile)):
        print_a(srcfile + " 文件或目录不存在!")
    else:
        shutil.move(srcfile, dstfile)

def select_bs4_parser():
    # 选择 BS4 解析器(优先使用lxml)
    try:
        import lxml
        del lxml
        return "lxml"
    except ModuleNotFoundError:
        try:
            import html5lib
            del html5lib
            return "html5lib"
        except ModuleNotFoundError:
            return

def os_clear_screen(ostype):
    # 清屏
    os.system("cls") if ostype == "Windows" else os.system("clear")

def save_to_json(save_data, filename):
    # 保存字典到 json 文件
    try:
        with open(filename, "w") as savefile:
            json.dump(save_data, savefile,
                      sort_keys=True, indent=4, ensure_ascii=False)
    # Debug
    except:
        print_(save_data)
        raise Exception("Write json failed!")

def read_from_json(filename):
    # 从 json 文件中读取字典
    try:
        with open(filename, "r", errors="ignore") as savefile:
            return json.load(savefile)
    except:
        try:
            os.remove(filename)
        finally:
            return {}

def print_n(argv="", end=os.linesep):
    sys.stderr.write(os.linesep + argv + end)

def print_i(argv="", end=os.linesep):
    sys.stderr.write("=== " + argv + end)

def print_in(argv="", end=os.linesep):
    sys.stderr.write(os.linesep + "=== " + argv + end)

def print_a(argv="", end=os.linesep):
    sys.stderr.write("*** " + argv + end)

def print_an(argv="", end=os.linesep):
    sys.stderr.write(os.linesep + "*** " + argv + end)

def print_l(argv="", end=os.linesep):
    sys.stderr.write("  |" + os.linesep + "  === " + argv + end)

def print_(argv="", end=os.linesep):
    sys.stderr.write(argv + end)

def input_a(argv):
    return input("*** " + argv)

def input_an(argv):
    return input("\n*** " + argv)

def main():

    ''' 检查 OS '''
    sysstr = platform.system()
    if sysstr not in ("Windows", "Linux"):
        print_("\n运行失败!\n\n不支持你的操作系统!")
        sys.exit()

    ''' 检测 BS4 解析器 '''
    bs4_parser = select_bs4_parser()
    if not bs4_parser:
        print_("\n运行失败!\n\n请安装至少一个解析器!")
        print_("可选: \"lxml\" 或 \"html5lib\"!")
        sys.exit()

    ''' Windows 命令行窗口设置 '''
    if sysstr == "Windows":
        os.system("title 猫咪 AV 图片爬取脚本 " + __version__ + " By Pzqqt")
        term_lines = 87
        term_cols = 120
        hex_lines = hex(term_lines).replace("0x", "").zfill(4)
        hex_cols = hex(term_cols).replace("0x", "").zfill(4)
        set_terminal_size = (r'reg add "HKEY_CURRENT_USER\Console" '
                             '/t REG_DWORD /v WindowSize /d 0x')
        set_terminal_buffer = (r'reg add "HKEY_CURRENT_USER\Console" '
                               '/t REG_DWORD /v ScreenBufferSize /d 0x')
        os.system("%s%s%s /f >nul" % (set_terminal_size, hex_lines, hex_cols))
        os.system("%s%s%s /f >nul" % (set_terminal_buffer, "07d0", hex_cols))

    ''' 主界面 '''
    Maomiav(bs4_parser, sysstr).run()
    os_clear_screen(sysstr)
    sys.exit()

if __name__ == '__main__':
    main()
