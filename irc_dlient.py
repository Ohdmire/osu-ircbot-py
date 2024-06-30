import irc.client
import re
import requests

import threading

import configparser

from requests.exceptions import HTTPError

from datetime import datetime

import rosu_pp_py as rosu

import os
import json
import time

osu_server = "irc.ppy.sh"
osu_port = 6667

# 定义IRC客户端类


class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')

        self.osuclientid = self.config['OSUAPI']['client_id']
        self.osuclientsecret = self.config['OSUAPI']['client_secret']
        self.osunickname = self.config['OSUAPI']['nickname']
        self.osupassword = self.config['OSUAPI']['password']
        self.mpname = self.config['OSU']['mpname']
        self.starlimit = self.config['OSU']['starlimit']
        self.timelimit = self.config['OSU']['timelimit']
        self.mppassword = self.config['OSU']['mppassword']


class MyIRCClient:

    def __init__(self, server, port, nickname, password):
        self.irc_react = irc.client.Reactor()
        self.server = self.irc_react.server()
        self.server.connect(server, port, nickname, password)
        self.irc_react.add_global_handler("welcome", self.on_connect)
        self.irc_react.add_global_handler("pubmsg", self.on_pubmsg)
        self.irc_react.add_global_handler("privmsg", self.on_privmsg)
        self.timer = None  # 定义定时器
        self.restarting_task = threading.Thread(target=(self.restart))

    def start(self):
        self.irc_react.process_forever()

    def reset_all(self):
        # 重置
        p.reset_player_list()
        p.reset_host_list()
        p.clear_approved_list()
        b.clear_cache()

    def restart(self):
        print(f'尝试重启...{datetime.now()+datetime.timedelta(hours=8)}')
        time.sleep(120)
        self.reset_all()
        r.create_room(self.server, "")
        self.restarting_task = threading.Thread(target=(self.restart))
        print(f'重启完成{datetime.now()+datetime.timedelta(hours=8)}')

    # 定义定时任务,每60s执行一次,检查房间状态
    def start_periodic_task(self):
        # Save the Timer object in an instance variable
        self.timer = threading.Timer(60, self.start_periodic_task)
        self.timer.start()
        if r.room_id != "":
            b.get_token()
            try:
                text = b.get_match_info(re.findall(r'\d+', r.room_id)[0])
            except:
                text = ""
            # match-disbanded #比赛关闭
            try:
                if ("match-disbanded" in str(text['events'])) == True:
                    self.stop_periodic_task()
                    # 重置
                    p.reset_player_list()
                    p.reset_host_list()
                    p.clear_approved_list()
                    p.approved_host_rotate_list.clear()
                    b.clear_cache()
                    # 尝试重新创建房间
                    try:
                        r.create_room(self.server, "")
                    except:
                        print("创建房间失败")
                        self.timer.start()
            except:
                print("无法判断比赛信息")
    # 停止定时任务

    def stop_periodic_task(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def export_json(self):
        result = {}
        result['player_list'] = p.player_list
        result['beatmap_name'] = b.beatmap_name
        result['beatmap_artist'] = b.beatmap_artist
        result['beatmap_star'] = b.beatmap_star

        try:
            with open('data.json', 'w', encoding='utf-8') as f:
                json.dump(result, f)
            print("导出json")
        except:
            print("导出json失败")

    def on_connect(self, connection, event):
        r.get_last_room_id()
        r.close_last_room(connection, event)
        self.reset_all()
        r.create_room(connection, event)

        def send_loop():
            while True:
                message = input(">")
                r.send_msg(connection, event, message)

        threading.Thread(target=(send_loop)).start()

    def on_privmsg(self, connection, event):
        # 打印接收到的私人消息
        print(f"收到私人消息  {event.source.split('!')[0]}:{event.arguments[0]}")
        text = event.arguments[0]
        # 匹配第一次收到的房间号
        if text.find("Created the tournament match") != -1 and event.source.find("BanchoBot") != -1:
            try:
                romm_id = "#mp_"+re.findall(r'\d+', text)[0]
            except:
                romm_id = ""
            # 更新room变量
            r.change_room_id(romm_id)
            # 加入并监听房间
            r.join_room(connection, event)
            # 修改房间密码
            r.change_password(connection, event)
            # 保存房间IDs
            r.save_last_room_id()
            # 启动定时任务
            self.start_periodic_task()

    def on_pubmsg(self, connection, event):
        try:
            # 打印接收到的消息
            print(f"收到频道消息  {event.source.split('!')[0]}:{event.arguments[0]}")
            text = event.arguments[0]
            # 判断是否是banchobot发送的消息
            if event.source.find("BanchoBot") != -1 or event.source.find("ATRI1024") != -1:
                # 加入房间
                if text.find("joined in slot") != -1:
                    # 尝试
                    try:
                        playerid = re.findall(
                            r'.*(?= joined in slot)', text)[0]
                    except:
                        playerid = ""
                    print(f'玩家{playerid}加入房间')
                    # 发送欢迎消息
                    if "ATRI1024" not in playerid:
                        if b.beatmap_length != "" and r.game_start_time != "":
                            timeleft = int(b.beatmap_length)+10 - \
                                int((datetime.now()-r.game_start_time).seconds)
                            text_timeleft = f'| 剩余游玩时间：{timeleft}s 请主人耐心等待哦~'
                        else:
                            timeleft = 0
                        text_Welcome = f'欢迎{playerid}酱~＼(≧▽≦)／ 输入help获取指令详情'
                        if timeleft > 0:
                            r.send_msg(connection, event,
                                       text_Welcome+text_timeleft)
                        else:
                            r.send_msg(connection, event, text_Welcome)
                    # 如果第一次加入房间，更换房主，清空房主队列，设置FM
                    if len(p.player_list) == 0:
                        p.reset_host_list()
                        r.change_host(connection, event, playerid)
                        r.change_mods_to_FM(connection, event)
                    # 加入房间队列，玩家队列
                    p.add_host(playerid)
                    p.add_player(playerid)
                    print(f'玩家队列{p.player_list}')
                    print(f'房主队列{p.room_host_list}')
                    # 输出
                    self.export_json()
                # 离开房间
                if text.find("left the game") != -1:
                    # 尝试
                    try:
                        playerid = re.findall(r'.*(?= left the game)', text)[0]
                    except:
                        playerid = ""
                    print(f'玩家{playerid}离开房间')
                    # 不移除房主队列
                    p.remove_player(playerid)
                    # 房主离开立刻更换房主
                    if playerid == p.room_host and len(p.player_list) != 0:
                        p.host_rotate(connection, event)
                    print(f'玩家队列{p.player_list}')
                    # 输出
                    self.export_json()
                # 谱面变化
                if text.find("Beatmap changed to") != -1:
                    # 尝试
                    try:
                        beatmap_url = re.findall(r'(?<=\()\S+(?=\))', text)[0]
                        beatmap_id = re.findall(r'\d+', beatmap_url)[0]
                    except:
                        beatmap_url = ""
                        beatmap_id = ""

                    last_beatmap_id = b.beatmap_id
                    if last_beatmap_id == "":
                        last_beatmap_id = "3459231"
                    b.change_beatmap_id(beatmap_id)
                    # 获取谱面信息
                    b.get_token()
                    b.get_beatmap_info()

                    if b.check_beatmap_if_out_of_star():
                        r.send_msg(connection, event,
                                   f'{b.beatmap_star}*>{config.starlimit}* 请重新选择')
                        r.change_beatmap_to(connection, event, last_beatmap_id)
                        b.change_beatmap_id(last_beatmap_id)
                        return
                    if b.check_beatmap_if_out_of_time():
                        r.send_msg(connection, event,
                                   f'{b.beatmap_length}s>{config.timelimit}s 请重新选择')
                        r.change_beatmap_to(connection, event, last_beatmap_id)
                        b.change_beatmap_id(last_beatmap_id)
                        return

                    r.send_msg(connection, event, b.return_beatmap_info())
                    # 输出
                    self.export_json()

                # 房主变化
                if text.find("became the host") != -1:
                    # 尝试
                    try:
                        p.room_host = re.findall(
                            r'.*(?= became the host)', text)[0]
                    except:
                        p.room_host = ""
                    print(f'房主变为{p.room_host}')

                # 准备就绪，开始游戏
                if text.find("All players are ready") != -1:
                    r.start_room(connection, event)

                # 开始游戏
                if text.find("The match has started") != -1:
                    # 将房主队列第一个人移动到最后
                    p.host_rotate_pending(connection, event)
                    print(f'游戏开始，房主队列{p.room_host_list}')
                    p.clear_approved_list()
                    # 获取游戏开始时间
                    r.set_game_start_time()

                # 游戏结束,更换房主
                if text.find("The match has finished") != -1:
                    # 对比房主队列,去除离开的玩家,更新房主队列
                    p.host_rotate(connection, event)
                    print(f'游戏结束，房主队列{p.room_host_list}')
                    # 换了房主以后立即清空投票列表
                    p.approved_host_rotate_list.clear()
                    p.clear_approved_list()
                    # 发送队列
                    p.convert_host()
                    r.send_msg(connection, event, str(
                        f'当前队列：{p.room_host_list_apprence_final}'))
                    # 重置游戏开始时间
                    r.reset_game_start_time()

                # 游戏被丢弃
                if text.find("Aborted the match") != -1:
                    # 判断游戏是否结束
                    timeleft = int(b.beatmap_length)+10 - \
                        int((datetime.now()-r.game_start_time).seconds)
                    if timeleft > 0:  # 大于0代表没打，先不更换房主，退回队列
                        p.reverse_host_pending(connection, event)
                        print("比赛被丢弃，房主队列退回")
                    else:  # 小于0代表已经打完，更换房主
                        # 对比房主队列,去除离开的玩家,更新房主队列
                        p.host_rotate(connection, event)
                    print(f'游戏结束，房主队列{p.room_host_list}')
                    # 换了房主以后立即清空投票列表
                    p.approved_host_rotate_list.clear()
                    p.clear_approved_list()
                    # 发送队列
                    p.convert_host()
                    r.send_msg(connection, event, str(
                        f'当前队列：{p.room_host_list_apprence_final}'))
                    # 重置游戏开始时间
                    r.reset_game_start_time()
                # bancho重启
                if text.find("Bancho will be right back!") != -1:
                    r.send_msg(connection, event,
                               "Bancho重启中，房间将在2min后自动重启")
                    self.restarting_task.start()

            # 玩家发送的消息响应部分

            # 投票丢弃游戏
            if text in ["!abort", "！abort", "!ABORT", "！ABORT"]:
                p.vote_for_abort(connection, event)

            # 投票开始游戏
            if text in ["!start", "！start", "!START", "！START"]:
                p.vote_for_start(connection, event)

            # 投票跳过房主
            if text in ["!skip", "！skip", "!SKIP", "！SKIP"]:
                p.vote_for_host_rotate(connection, event)

            # 投票关闭房间s
            if text in ["!close", "！close", "!CLOSE", "！CLOSE"]:
                p.vote_for_close_room(connection, event)

            # 手动查看队列，就只返回前面剩余多少人
            if text in ["!queue", "！queue", "!QUEUE", "！QUEUE", "!q", "！q", "!Q", "！Q"]:
                p.convert_host()
                index = p.remain_hosts_to_player(event.source.split('!')[0])
                r.send_msg(connection, event, str(
                    f'你前面剩余人数：{index}'))

            # 帮助
            if text in ["help", "HELP", "!help", "！help", "!HELP", "！HELP"]:
                r.send_msg(connection, event, r.help())

            # ping
            if text in ["ping", "PING", "!ping", "！ping", "!PING", "！PING"]:
                r.send_msg(connection, event, r'pong')

            # 快速查询成绩
            if text in ["!pr", "！pr", "!PR", "！PR", "!p", "！p", "!P", "！P"]:
                b.get_user_id(event.source.split('!')[0])
                detail_1 = b.get_recent_info(event.source.split('!')[0])
                pp.get_beatmap_file(beatmap_id=b.pr_beatmap_id)
                detail_2 = pp.calculate_pp_obj(
                    mods=b.pr_mods_int, combo=b.pr_maxcombo, acc=b.pr_acc, misses=b.pr_miss)
                r.send_msg(connection, event, detail_1)
                r.send_msg(connection, event, detail_2)

            # 快速当前谱面成绩
            if text in ["!s", "！s", "!S", "！S"]:
                b.get_user_id(event.source.split('!')[0])
                s = b.get_beatmap_score(event.source.split('!')[0])
                r.send_msg(connection, event, s)
                if s.find("未查询到") == -1:
                    pp.get_beatmap_file(beatmap_id=b.beatmap_id)
                    r.send_msg(connection, event, pp.calculate_pp_obj(
                        mods=b.pr_mods_int, combo=b.pr_maxcombo, acc=b.pr_acc, misses=b.pr_miss))

            # 快速查询谱面得分情况
            if text.find("!m+") != -1:
                try:
                    modslist = re.findall(r'\+(.*)', event.arguments[0])[0]
                except:
                    modslist = ""
                new_mods_list = []
                # 循环遍历字符串，步长为2
                for i in range(0, len(modslist), 2):
                    # 每次取两个字符，并添加到列表中
                    new_mods_list.append(modslist[i:i+2])
                pp.get_beatmap_file(beatmap_id=b.beatmap_id)
                r.send_msg(connection, event, pp.calculate_pp_fully(
                    pp.cal_mod_int(new_mods_list)))
            if text.find("!M+") != -1:
                try:
                    modslist = re.findall(r'\+(.*)', event.arguments[0])[0]
                except:
                    modslist = ""
                new_mods_list = []
                # 循环遍历字符串，步长为2
                for i in range(0, len(modslist), 2):
                    # 每次取两个字符，并添加到列表中
                    new_mods_list.append(modslist[i:i+2])
                pp.get_beatmap_file(beatmap_id=b.beatmap_id)
                r.send_msg(connection, event, pp.calculate_pp_fully(
                    pp.cal_mod_int(new_mods_list)))

            if text.find("！M+") != -1:
                try:
                    modslist = re.findall(r'\+(.*)', event.arguments[0])[0]
                except:
                    modslist = ""
                new_mods_list = []
                # 循环遍历字符串，步长为2
                for i in range(0, len(modslist), 2):
                    # 每次取两个字符，并添加到列表中
                    new_mods_list.append(modslist[i:i+2])
                pp.get_beatmap_file(beatmap_id=b.beatmap_id)
                r.send_msg(connection, event, pp.calculate_pp_fully(
                    pp.cal_mod_int(new_mods_list)))

            if text.find("！M+") != -1:
                try:
                    modslist = re.findall(r'\+(.*)', event.arguments[0])[0]
                except:
                    modslist = ""
                new_mods_list = []
                # 循环遍历字符串，步长为2
                for i in range(0, len(modslist), 2):
                    # 每次取两个字符，并添加到列表中
                    new_mods_list.append(modslist[i:i+2])
                pp.get_beatmap_file(beatmap_id=b.beatmap_id)
                r.send_msg(connection, event, pp.calculate_pp_fully(
                    pp.cal_mod_int(new_mods_list)))

            if text in ["!m", "！m", "!M", "！M"]:
                pp.get_beatmap_file(beatmap_id=b.beatmap_id)
                r.send_msg(connection, event,
                           pp.calculate_pp_fully(pp.cal_mod_int([])))

            # 快速获取剩余时间 大约10s游戏延迟
            if text in ["!ttl", "！ttl", "!TTL", "！TTL"]:
                if b.beatmap_length != "" and r.game_start_time != "":
                    timeleft = int(b.beatmap_length)+10 - \
                        int((datetime.now()-r.game_start_time).seconds)
                    r.send_msg(connection, event, f'剩余游玩时间：{timeleft}s')
                else:
                    r.send_msg(connection, event, f'剩余游玩时间：未知')

            if text in ["!i", "！i"]:
                b.get_token()
                b.get_beatmap_info()
                r.send_msg(connection, event, b.return_beatmap_info())

            if text in ["!about", "！about", "!ABOUT", "！ABORT"]:
                r.send_msg(connection, event,
                           "[https://github.com/Ohdmire/osu-ircbot-py ATRI高性能bot]")

        except Exception as e:
            print(f'-----------------未知错误---------------------\n{e}')


# 定义玩家类
class Player:
    def __init__(self):
        self.player_list = []
        self.room_host_list = []
        self.room_host_list_apprence = []
        self.room_host_list_apprence_final = ""
        self.approved_abort_list = []
        self.approved_start_list = []
        self.approved_host_rotate_list = []
        self.approved_close_list = []
        self.room_host = ""

    def add_player(self, name):
        self.player_list.append(name)

    def add_host(self, name):
        if name not in self.room_host_list:
            self.room_host_list.append(name)

    def remove_host(self, name):
        if name in self.room_host_list:
            self.room_host_list.remove(name)

    def remain_hosts_to_player(self, name):
        if name in self.room_host_list:
            index = self.room_host_list.index(name)
            return index

    def convert_host(self):
        try:
            self.room_host_list_apprence.clear()
            for i in self.room_host_list:
                url_i = i.replace(" ", "%20")
                new_name = f'[https://osu.ppy.sh/users/{url_i} {i}]'
                self.room_host_list_apprence.append(new_name)
            self.room_host_list_apprence_final = ""
            count = 0
            total_count = len(self.room_host_list_apprence)
            for i in self.room_host_list_apprence:  # 遍历列表
                self.room_host_list_apprence_final += i + "-->"
                count += 1
                if count == 2:  # 如果已经显示过了2个，就直接加上 中间的还有多少个 和最后的一个
                    if total_count != 3:  # 如果不是刚好三个人
                        self.room_host_list_apprence_final += str(
                            total_count - count - 1) + "players......" + "-->" + self.room_host_list_apprence[-1]
                    else:  # 刚好3个人就不要 显示中间有多少人了
                        self.room_host_list_apprence_final += self.room_host_list_apprence[-1]
                    break

        except:
            print("房主队列为空")

    def remove_player(self, name):
        if name in self.player_list:
            self.player_list.remove(name)

    def reset_player_list(self):
        self.player_list.clear()

    def reset_host_list(self):
        self.room_host_list.clear()

    def clear_approved_list(self):
        self.approved_abort_list.clear()
        self.approved_start_list.clear()
        self.approved_close_list.clear()
        self.approved_host_rotate_list.clear()

    def host_rotate_pending(self, connection, event):
        now_host = self.room_host_list[0]
        self.remove_host(now_host)
        self.add_host(now_host)

    def reverse_host_pending(self, connection, event):
        self.remove_host(self.room_host)
        self.room_host_list.insert(0, self.room_host)

    def host_rotate(self, connection, event):
        result_list = []
        for i in self.room_host_list:
            if i in self.player_list:
                result_list.append(i)
        self.room_host_list = result_list
        r.change_host(connection, event, self.room_host_list[0])

    def vote_for_abort(self, connection, event):
        # 获取发送者名字
        name = event.source.split('!')[0]
        if name not in self.approved_abort_list:
            self.approved_abort_list.append(name)
        if len(self.approved_abort_list) >= round(len(self.player_list)/2):
            r.abort_room(connection, event)
            self.approved_abort_list.clear()
        else:
            r.send_msg(connection, event, r'输入!abort强制放弃比赛 {} / {} '.format(
                str(len(self.approved_abort_list)), str(round(len(self.player_list)/2))))

    def vote_for_start(self, connection, event):
        # 获取发送者名字
        name = event.source.split('!')[0]
        if name not in self.approved_start_list:
            self.approved_start_list.append(name)
        if len(self.approved_start_list) >= round(len(self.player_list)/2):
            r.start_room(connection, event)
            self.approved_start_list.clear()
        else:
            r.send_msg(connection, event, r'输入!start强制开始比赛 {} / {} '.format(
                str(len(self.approved_start_list)), str(round(len(self.player_list)/2))))

    def vote_for_host_rotate(self, connection, event):
        # 获取发送者名字
        name = event.source.split('!')[0]
        # 如果发送者是房主，直接换房主
        if name == self.room_host:
            self.host_rotate_pending(connection, event)
            self.host_rotate(connection, event)
            self.approved_host_rotate_list.clear()
            print("房主自行更换")
            return
        if name not in self.approved_host_rotate_list:
            self.approved_host_rotate_list.append(name)
        if len(self.approved_host_rotate_list) >= round(len(self.player_list)/2):
            self.host_rotate_pending(connection, event)
            self.host_rotate(connection, event)
            self.approved_host_rotate_list.clear()
        else:
            r.send_msg(connection, event, r'输入!skip强制跳过房主 {} / {} '.format(
                str(len(self.approved_host_rotate_list)), str(round(len(self.player_list)/2))))

    def vote_for_close_room(self, connection, event):
        # 获取发送者名字
        name = event.source.split('!')[0]
        if name not in self.approved_close_list:
            self.approved_close_list.append(name)
        if len(self.approved_close_list) == len(self.player_list):
            r.close_room(connection, event)
            self.approved_close_list.clear()
        else:
            r.send_msg(connection, event, r'输入!close强制关闭房间(1min后自动重启) {} / {} '.format(
                str(len(self.approved_close_list)), str(len(self.player_list))))


# 定义房间操作类
class Room:
    def __init__(self):
        self.room_id = ""
        self.last_romm_id = ""
        self.game_start_time = ""

    def set_game_start_time(self):
        self.game_start_time = datetime.now()
        return self.game_start_time

    def reset_game_start_time(self):
        self.game_start_time = ""

    def get_last_room_id(self):
        try:
            with open('last_room_id.txt', 'r') as f:
                self.last_romm_id = f.read()
                print(f'获取上一个房间ID{self.last_romm_id}')
        except:
            print("未获取上一个房间ID")

    # 保存当前id到文件
    def save_last_room_id(self):
        try:
            with open('last_room_id.txt', 'w') as f:
                f.write(self.room_id)
                print(f'保存当前房间ID{self.room_id}')
        except:
            print("未保存当前房间ID")

    def help(self):
        return r'!queue(!q) 查看队列 | !abort 投票丢弃游戏 | !start 投票开始游戏 | !skip 投票跳过房主 | !pr(!p) 查询最近成绩 | !s 查询当前谱面bp | !m+{MODS} 查询谱面模组PP| !i 返回当前谱面信息| !ttl 查询剩余时间 | !close 投票关闭(1min后自动重启)房间 | help 查看帮助 | !about 关于机器人'

    def change_room_id(self, id):
        self.room_id = id
        print(f'更换当前房间ID为{self.room_id}')

    def send_msg(self, connection, evetn, msg_text):
        connection.privmsg(self.room_id, msg_text)
        print("发送消息："+msg_text)

    def close_last_room(self, connection, event):
        if self.last_romm_id != self.room_id:
            connection.join(self.last_romm_id)
            connection.privmsg(self.last_romm_id, "!mp close")
            connection.part(self.last_romm_id)
            print("关闭上一个房间")
        else:
            print("不需要关闭上一个房间")

    def create_room(self, connection, event):
        connection.privmsg(
            "BanchoBot", "!mp make "+config.mpname)
        print("创建房间")

    def join_room(self, connection, event):
        connection.join(self.room_id)  # 加入 #osu 频道
        print(f'加入房间{self.room_id}')

    def close_room(self, connection, event):
        connection.privmsg(self.room_id, "!mp close")
        print(f'关闭房间{self.room_id}')

    def change_host(self, connection, event, playerid):
        connection.privmsg(self.room_id, "!mp host "+playerid)
        print("更换房主为 "+playerid)

    def start_room(self, connection, event):
        connection.privmsg(self.room_id, "!mp start")
        print("开始游戏")

    def abort_room(self, connection, event):
        connection.privmsg(self.room_id, "!mp abort")
        print("丢弃游戏")

    def change_password(self, connection, event):
        connection.privmsg(self.room_id, "!mp password "+config.mppassword)
        print("修改密码")

    def change_beatmap_to(self, connection, event, beatmapid):
        connection.privmsg(self.room_id, "!mp map "+beatmapid)
        print("更换谱面为"+beatmapid)

    def change_mods_to_FM(self, connection, event):
        connection.privmsg(self.room_id, "!mp mods FreeMod")
        print("开启Freemod")


# 定义谱面类


class Beatmap:
    def __init__(self):
        self.osu_client_id = client_id
        self.osu_client_secret = client_secret
        self.osu_token = ""
        self.beatmap_id = ""
        self.beatmap_songs_id = ""
        self.beatmap_name = ""
        self.beatmap_artist = ""
        self.beatmap_star = 0
        self.beatmap_status = ""
        self.beatemap_bpm = ""
        self.beatmap_cs = ""
        self.beatmap_ar = ""
        self.beatmap_od = ""
        self.beatmap_hp = ""
        self.beatmap_length = 0
        self.beatmap_ranked_date = ""
        self.beatmatp_submit_date = ""
        self.beatmap_mirror_sayo_url = ""
        self.beatmap_osudirect_url = ""

        self.id2name = {}

        self.pr_beatmap_id = ""
        self.pr_beatmap_url = ""

        self.pr_title = ""
        self.pr_artist = ""
        self.pr_star = ""

        self.pr_acc = 0
        self.pr_maxcombo = 0
        self.pr_300 = 0
        self.pr_100 = 0
        self.pr_50 = 0
        self.pr_miss = 0
        self.pr_pp = 0
        self.pr_rank = ""
        self.pr_mods = ""
        self.pr_mods_int = 0

        self.pr_username = ""

    def clear_cache(self):
        self.osu_token = ""
        self.id2name.clear()

    def get_token(self):
        try:
            url = 'https://osu.ppy.sh/oauth/token'
            data = {
                'client_id': self.osu_client_id,
                'client_secret': self.osu_client_secret,
                'grant_type': 'client_credentials',
                'scope': 'public'
            }
            response = requests.post(url, data=data)
            response.raise_for_status()  # 如果请求失败，这会抛出一个异常
            self.osu_token = response.json()['access_token']
        except:
            self.osu_token = ""
            print("获取访问令牌失败")

    # 使用访问令牌查询
    def get_beatmap_info(self):

        try:
            url = f'https://osu.ppy.sh/api/v2/beatmaps/'+self.beatmap_id
            headers = {'Authorization': f'Bearer {self.osu_token}'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 如果请求失败，这会抛出一个异常

            self.beatmap_songs_id = str(response.json()['beatmapset_id'])

            self.beatmap_name = response.json()['beatmapset']['title_unicode']
            self.beatmap_artist = response.json(
            )['beatmapset']['artist_unicode']
            self.beatmap_star = response.json()['difficulty_rating']
            self.beatmap_status = response.json()['status']
            self.beatemap_bpm = response.json()['bpm']
            self.beatmap_cs = response.json()['cs']
            self.beatmap_ar = response.json()['ar']
            self.beatmap_od = response.json()['accuracy']
            self.beatmap_hp = response.json()['drain']
            self.beatmap_length = response.json()['total_length']
            if self.beatmap_status == "ranked":
                self.beatmap_ranked_date = response.json(
                )['beatmapset']['ranked_date'][:10]
            else:
                self.beatmap_ranked_date = response.json(
                )['beatmapset']['submitted_date'][:10]
            self.beatmap_mirror_sayo_url = "https://osu.sayobot.cn/home?search="+self.beatmap_songs_id
            self.beatmap_mirror_inso_url = "http://inso.link/yukiho/?b="+self.beatmap_id
            self.beatmap_osudirect_url = response.json()['url']
        except:
            print("获取谱面信息失败")
            self.beatmap_name = "获取谱面信息失败"
            self.beatmap_songs_id = ""
            self.beatmap_artist = ""
            self.beatmap_star = 0
            self.beatmap_status = ""
            self.beatemap_bpm = ""
            self.beatmap_cs = ""
            self.beatmap_ar = ""
            self.beatmap_od = ""
            self.beatmap_hp = ""
            self.beatmap_length = 0
            self.beatmap_ranked_date = ""
            self.beatmap_mirror_sayo_url = ""
            self.beatmap_mirror_inso_url = ""
            self.beatmap_osudirect_url = ""

    def change_beatmap_id(self, id):
        self.beatmap_id = id
        print(f'更换谱面ID为 {self.beatmap_id}')

    def check_beatmap_if_out_of_star(self):
        if float(config.starlimit) == 0:
            return False
        if self.beatmap_star > float(config.starlimit):
            return True
        else:
            return False

    def check_beatmap_if_out_of_time(self):
        if float(config.timelimit) == 0:
            return False
        if self.beatmap_length > float(config.timelimit):
            return True
        else:
            return False

    def return_beatmap_info(self):
        result = r'{} {}| {}*| [{} {} - {}]| bpm:{} length:{}s| ar:{} cs:{} od:{} hp:{}| [{} Sayobot] OR [{} inso]'.format(self.beatmap_ranked_date, self.beatmap_status, self.beatmap_star, self.beatmap_osudirect_url,
                                                                                                                           self.beatmap_name, self.beatmap_artist, self.beatemap_bpm, self.beatmap_length, self.beatmap_ar, self.beatmap_cs, self.beatmap_od, self.beatmap_hp, self.beatmap_mirror_sayo_url, self.beatmap_mirror_inso_url)
        print(result)
        return result

    def get_match_info(self, match_id):
        try:
            url = f'https://osu.ppy.sh/api/v2/matches/{match_id}'
            headers = {'Authorization': f'Bearer {self.osu_token}'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 如果请求失败，这将抛出一个异常
            return response.json()
        except:
            print("获取比赛信息失败")
            return ""

    def get_user_id(self, username):
        try:
            if username not in self.id2name:
                print("获取用户ID")
                url = f'https://osu.ppy.sh/api/v2/users/{username}?key=username'
                headers = {'Authorization': f'Bearer {self.osu_token}'}
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # 如果请求失败，这将抛出一个异常
                self.id2name[username] = response.json()['id']
                print(self.id2name)
        except:
            print("获取用户ID失败")

    def cal_mod_int(self, modname):
        mod_int = 0
        for i in modname:
            if i == "NF" or i == "nf":
                mod_int += 1
            if i == "EZ" or i == "ez":
                mod_int += 2
            if i == "TD" or i == "td":
                mod_int += 4
            if i == "HD" or i == "hd":
                mod_int += 8
            if i == "HR" or i == "hr":
                mod_int += 16
            if i == "SD" or i == "sd":
                mod_int += 32
            if i == "DT" or i == "dt":
                mod_int += 64
            if i == "RX" or i == "rx":
                mod_int += 128
            if i == "HT" or i == "ht":
                mod_int += 256
            if i == "NC" or i == "nc":
                mod_int += 512
            if i == "FL" or i == "fl":
                mod_int += 1024
            if i == "AT" or i == "at":
                mod_int += 2048
            if i == "SO" or i == "so":
                mod_int += 4096
            if i == "AP" or i == "ap":
                mod_int += 8192
            if i == "PF" or i == "pf":
                mod_int += 16384
            if i == "4K" or i == "4k":
                mod_int += 32768
            if i == "5K" or i == "5k":
                mod_int += 65536
            if i == "6K" or i == "6k":
                mod_int += 131072
            if i == "7K" or i == "7k":
                mod_int += 262144
            if i == "8K" or i == "8k":
                mod_int += 524288
            if i == "FI" or i == "fi":
                mod_int += 1048576
            if i == "RD" or i == "rd":
                mod_int += 2097152
            if i == "CM" or i == "cm":
                mod_int += 4194304
            if i == "TP" or i == "tp":
                mod_int += 8388608
            if i == "9K" or i == "9k":
                mod_int += 16777216
            if i == "CO" or i == "co":
                mod_int += 33554432
            if i == "1K" or i == "1k":
                mod_int += 67108864
            if i == "3K" or i == "3k":
                mod_int += 134217728
            if i == "2K" or i == "2k":
                mod_int += 268435456
            if i == "V2" or i == "v2":
                mod_int += 536870912
            if i == "MR" or i == "mr":
                mod_int += 1073741824
        return mod_int

    def get_beatmap_score(self, username):
        try:
            user_id = self.id2name[username]
            url = f"https://osu.ppy.sh/api/v2/beatmaps/{self.beatmap_id}/scores/users/{user_id}"
            headers = {'Authorization': f'Bearer {self.osu_token}'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 如果请求失败，这会抛出一个异常

            self.pr_title = self.beatmap_name
            self.pr_artist = self.beatmap_artist
            self.pr_star = self.beatmap_star

            self.beatmap_score_created_at = response.json()[
                'score']['created_at'][:10]

            self.pr_acc = response.json()['score']['accuracy']
            self.pr_maxcombo = response.json()['score']['max_combo']
            self.pr_300 = response.json()['score']['statistics']['count_300']
            self.pr_100 = response.json()['score']['statistics']['count_100']
            self.pr_50 = response.json()['score']['statistics']['count_50']
            self.pr_miss = response.json()['score']['statistics']['count_miss']
            self.pr_pp = response.json()['score']['pp']
            self.pr_rank = response.json()['score']['rank']
            self.pr_mods = response.json()['score']['mods']

            self.pr_beatmap_url = response.json()['score']['beatmap']['url']

            self.pr_username = username

            self.pr_acc = round(self.pr_acc*100, 2)

            if self.pr_mods == []:
                self.pr_mods = "NM"
                self.pr_mods_int = 0
            else:
                tempmod = ""
                for i in self.pr_mods:
                    tempmod = tempmod+i
                    # 获取mod数值
                self.pr_mods_int = self.cal_mod_int(self.pr_mods)

                self.pr_mods = tempmod

        except HTTPError:
            print(f"未查询到{username}在该谱面上留下的成绩")
            return f"未查询到{username}在该谱面上留下的成绩"

        except:
            print("获取谱面成绩失败")
            self.pr_title = "获取谱面成绩失败"
            self.pr_artist = ""
            self.pr_star = ""
            self.pr_acc = 0
            self.pr_maxcombo = 0
            self.pr_300 = 0
            self.pr_100 = 0
            self.pr_50 = 0
            self.pr_miss = 0
            self.pr_pp = 0
            self.pr_rank = ""
            self.pr_mods = ""
            self.pr_username = ""

            self.beatmap_score_created_at = ""

        result = r'{}| [{} {} - {}]| {}*| {} [ {} ] {}pp acc:{}% combo:{}x| {}/{}/{}/{}| date:{}|'.format(
            self.pr_username, self.pr_beatmap_url, self.pr_title, self.pr_artist, self.pr_star, self.pr_mods, self.pr_rank, self.pr_pp, self.pr_acc, self.pr_maxcombo, self.pr_300, self.pr_100, self.pr_50, self.pr_miss, self.beatmap_score_created_at)
        print(result)
        return result

    def get_recent_info(self, username):
        try:
            user_id = self.id2name[username]
            url = f'https://osu.ppy.sh/api/v2/users/{user_id}/scores/recent'
            headers = {'Authorization': f'Bearer {self.osu_token}'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 如果请求失败，这将抛出一个异常

            self.pr_beatmap_id = response.json()[0]['beatmap']['id']
            self.pr_title = response.json()[0]['beatmapset']['title_unicode']
            self.pr_artist = response.json()[0]['beatmapset']['artist_unicode']
            self.pr_star = response.json()[0]['beatmap']['difficulty_rating']

            self.pr_acc = response.json()[0]['accuracy']
            self.pr_maxcombo = response.json()[0]['max_combo']
            self.pr_300 = response.json()[0]['statistics']['count_300']
            self.pr_100 = response.json()[0]['statistics']['count_100']
            self.pr_50 = response.json()[0]['statistics']['count_50']
            self.pr_miss = response.json()[0]['statistics']['count_miss']
            self.pr_pp = response.json()[0]['pp']
            self.pr_rank = response.json()[0]['rank']
            self.pr_mods = response.json()[0]['mods']

            self.pr_beatmap_url = response.json()[0]['beatmap']['url']

            self.pr_username = username

            self.pr_acc = round(self.pr_acc*100, 2)

            if self.pr_mods == []:
                self.pr_mods = "NM"
                self.pr_mods_int = 0
            else:
                tempmod = ""
                for i in self.pr_mods:
                    tempmod = tempmod+i
                    # 获取mod数值
                self.pr_mods_int = self.cal_mod_int(self.pr_mods)
                self.pr_mods = tempmod

        except:
            print("获取最近成绩失败")
            self.pr_title = "获取最近成绩失败"
            self.pr_artist = ""
            self.pr_star = ""
            self.pr_acc = 0
            self.pr_maxcombo = 0
            self.pr_300 = 0
            self.pr_100 = 0
            self.pr_50 = 0
            self.pr_miss = 0
            self.pr_pp = 0
            self.pr_rank = ""
            self.pr_mods = ""
            self.pr_username = ""
            self.pr_beatmap_url = ""

        result = r'{}| [{} {} - {}]| {}*| {} [ {} ] {}pp acc:{}% combo:{}x| {}/{}/{}/{}|'.format(
            self.pr_username, self.pr_beatmap_url, self.pr_title, self.pr_artist, self.pr_star, self.pr_mods, self.pr_rank, self.pr_pp, self.pr_acc, self.pr_maxcombo, self.pr_300, self.pr_100, self.pr_50, self.pr_miss,)
        print(result)
        return result


class PP:
    def __init__(self):
        self.beatmap_id = ""
        self.mods = 0
        self.acc = 0
        self.combo = 0
        self.misses = 0

        self.maxbeatmapcombo = 0

        self.stars = 0

        self.modsnamelist = []

        self.maxpp = 0
        self.maxaimpp = 0
        self.maxspeedpp = 0
        self.maxaccpp = 0

        self.afterar = 0
        self.aftercs = 0
        self.afterod = 0
        self.afterhp = 0

        self.currpp = 0
        self.curraimpp = 0
        self.currspeedpp = 0
        self.curraccpp = 0

        self.fcpp = 0
        self.fc95pp = 0
        self.fc96pp = 0
        self.fc97pp = 0
        self.fc98pp = 0
        self.fc99pp = 0

        self.tempmod = ""

    def get_beatmap_file(self, beatmap_id):
        self.beatmap_id = beatmap_id

        if os.path.exists(f'./maps/{beatmap_id}.osu'):
            print(f'谱面文件已存在')
        else:
            try:
                url = f'https://osu.ppy.sh/osu/{beatmap_id}'
                response = requests.get(url)
                response.raise_for_status()  # 如果请求失败，这会抛出一个异常
                with open(f'./maps/{beatmap_id}.osu', 'wb') as f:
                    f.write(response.content)
            except:
                print("获取谱面文件失败")

    def cal_mod_int(self, modname):
        self.modsnamelist = modname
        mod_int = 0
        for i in modname:
            if i == "NF" or i == "nf":
                mod_int += 1
            if i == "EZ" or i == "ez":
                mod_int += 2
            if i == "TD" or i == "td":
                mod_int += 4
            if i == "HD" or i == "hd":
                mod_int += 8
            if i == "HR" or i == "hr":
                mod_int += 16
            if i == "SD" or i == "sd":
                mod_int += 32
            if i == "DT" or i == "dt":
                mod_int += 64
            if i == "RX" or i == "rx":
                mod_int += 128
            if i == "HT" or i == "ht":
                mod_int += 256
            if i == "NC" or i == "nc":
                mod_int += 512
            if i == "FL" or i == "fl":
                mod_int += 1024
            if i == "AT" or i == "at":
                mod_int += 2048
            if i == "SO" or i == "so":
                mod_int += 4096
            if i == "AP" or i == "ap":
                mod_int += 8192
            if i == "PF" or i == "pf":
                mod_int += 16384
            if i == "4K" or i == "4k":
                mod_int += 32768
            if i == "5K" or i == "5k":
                mod_int += 65536
            if i == "6K" or i == "6k":
                mod_int += 131072
            if i == "7K" or i == "7k":
                mod_int += 262144
            if i == "8K" or i == "8k":
                mod_int += 524288
            if i == "FI" or i == "fi":
                mod_int += 1048576
            if i == "RD" or i == "rd":
                mod_int += 2097152
            if i == "CM" or i == "cm":
                mod_int += 4194304
            if i == "TP" or i == "tp":
                mod_int += 8388608
            if i == "9K" or i == "9k":
                mod_int += 16777216
            if i == "CO" or i == "co":
                mod_int += 33554432
            if i == "1K" or i == "1k":
                mod_int += 67108864
            if i == "3K" or i == "3k":
                mod_int += 134217728
            if i == "2K" or i == "2k":
                mod_int += 268435456
            if i == "V2" or i == "v2":
                mod_int += 536870912
            if i == "MR" or i == "mr":
                mod_int += 1073741824
        return mod_int

    def calculate_pp_fully(self, mods):

        try:

            self.mods = mods

            map = rosu.Beatmap(path=f"./maps/{self.beatmap_id}.osu")

            max_perf = rosu.Performance(mods=mods)

            attrs = max_perf.calculate(map)

            self.maxpp = attrs.pp

            # 计算maxbeatmapcombo
            self.maxbeatmapcombo = attrs.difficulty.max_combo

            # 计算stars
            self.stars = attrs.difficulty.stars

            # 计算cal的ar

            self.afterar = attrs.difficulty.ar
            # self.aftercs = attrs.difficulty.cs
            self.afterod = attrs.difficulty.od
            self.afterhp = attrs.difficulty.hp

            # 计算if 95% pp
            max_perf.set_accuracy(95)
            fc95_perf = max_perf.calculate(map)
            self.fc95pp = fc95_perf.pp

            # 计算if 96% pp
            max_perf.set_accuracy(96)
            fc96_perf = max_perf.calculate(map)
            self.fc96pp = fc96_perf.pp

            # 计算if 97% pp
            max_perf.set_accuracy(97)
            fc97_perf = max_perf.calculate(map)
            self.fc97pp = fc97_perf.pp

            # 计算if 98% pp
            max_perf.set_accuracy(98)
            fc98_perf = max_perf.calculate(map)
            self.fc98pp = fc98_perf.pp

            # 计算if 99% pp
            max_perf.set_accuracy(99)
            fc99_perf = max_perf.calculate(map)
            self.fc99pp = fc99_perf.pp

            self.maxpp = round(self.maxpp)
            self.fc95pp = round(self.fc95pp)
            self.fc96pp = round(self.fc96pp)
            self.fc97pp = round(self.fc97pp)
            self.fc98pp = round(self.fc98pp)
            self.fc99pp = round(self.fc99pp)
            self.stars = round(self.stars, 2)

            if self.modsnamelist == []:
                self.tempmod = "NM"
            else:
                self.tempmod = ""
                for i in self.modsnamelist:
                    self.tempmod = self.tempmod+i

            self.afterar = round(self.afterar, 1)
            # self.aftercs = round(self.aftercs, 1)
            self.afterarcs = "???"
            self.afterod = round(self.afterod, 1)
            self.afterhp = round(self.afterhp, 1)

        except:
            print("计算pp失败")
            self.tempmod = "NM"
            self.maxpp = 0
            self.maxbeatmapcombo = 0
            self.fc95pp = 0
            self.fc96pp = 0
            self.fc97pp = 0
            self.fc98pp = 0
            self.fc99pp = 0
            self.stars = 0

            self.afterar = 0
            self.aftercs = 0
            self.afterod = 0
            self.afterhp = 0

        return f'{self.tempmod}| {self.stars}*| {self.maxbeatmapcombo}x| ar:{self.afterar} cs:{self.aftercs} od:{self.afterod} hp:{self.afterhp} | SS:{self.maxpp}pp| 99%:{self.fc99pp}pp| 98%:{self.fc98pp}pp| 97%:{self.fc97pp}pp| 96%:{self.fc96pp}pp| 95%:{self.fc95pp}pp'

    def calculate_pp_obj(self, mods, acc, misses, combo):

        try:

            self.mods = mods

            map = rosu.Beatmap(path=f"./maps/{self.beatmap_id}.osu")

            max_perf = rosu.Performance(mods=mods)

            attrs = max_perf.calculate(map)

            self.maxpp = attrs.pp

            self.maxbeatmapcombo = attrs.difficulty.max_combo

            self.maxaimpp = attrs.pp_aim
            self.maxspeedpp = attrs.pp_speed
            self.maxaccpp = attrs.pp_acc

            # 计算玩家的current performance
            max_perf.set_misses(misses)
            max_perf.set_accuracy(acc)
            max_perf.set_combo(combo)

            curr_perf = max_perf.calculate(map)
            self.currpp = curr_perf.pp
            self.curraccpp = curr_perf.pp
            self.curraimpp = curr_perf.pp_aim
            self.currspeedpp = curr_perf.pp_speed
            self.curraccpp = curr_perf.pp_acc

            # 计算if fc pp
            max_perf.set_misses(0)
            max_perf.set_combo(None)

            fc_perf = max_perf.calculate(map)
            self.fcpp = fc_perf.pp

            # 计算if 95% pp
            max_perf.set_accuracy(95)
            fc95_perf = max_perf.calculate(map)
            self.fc95pp = fc95_perf.pp

            # 计算if 96% pp
            max_perf.set_accuracy(96)
            fc96_perf = max_perf.calculate(map)
            self.fc96pp = fc96_perf.pp

            # 计算if 97% pp
            max_perf.set_accuracy(97)
            fc97_perf = max_perf.calculate(map)
            self.fc97pp = fc97_perf.pp

            # 计算if 98% pp
            max_perf.set_accuracy(98)
            fc98_perf = max_perf.calculate(map)
            self.fc98pp = fc98_perf.pp

            # 计算if 99% pp
            max_perf.set_accuracy(99)
            fc99_perf = max_perf.calculate(map)
            self.fc99pp = fc99_perf.pp

            self.maxpp = round(self.maxpp)
            self.maxaimpp = round(self.maxaimpp)
            self.maxspeedpp = round(self.maxspeedpp)
            self.maxaccpp = round(self.maxaccpp)

            self.currpp = round(self.currpp)
            self.curraimpp = round(self.curraimpp)
            self.currspeedpp = round(self.currspeedpp)
            self.curraccpp = round(self.curraccpp)

            self.fcpp = round(self.fcpp)
            self.fc95pp = round(self.fc95pp)
            self.fc96pp = round(self.fc96pp)
            self.fc97pp = round(self.fc97pp)
            self.fc98pp = round(self.fc98pp)
            self.fc99pp = round(self.fc99pp)

        except Exception as e:
            print("计算pp失败")
            self.maxpp = 0
            self.maxaimpp = 0
            self.maxspeedpp = 0
            self.maxaccpp = 0

            self.maxbeatmapcombo = 0

            self.currpp = 0
            self.curraimpp = 0
            self.currspeedpp = 0
            self.curraccpp = 0

            self.fcpp = 0
            self.fc95pp = 0
            self.fc96pp = 0
            self.fc97pp = 0
            self.fc98pp = 0
            self.fc99pp = 0

        return f'now:{self.currpp}pp| if FC({self.maxbeatmapcombo}x):{self.fcpp}pp| 95%:{self.fc95pp}pp| 96%:{self.fc96pp}pp| 97%:{self.fc97pp}pp| 98%:{self.fc98pp}pp| 99%:{self.fc99pp}pp| SS:{self.maxpp}pp| aim:{self.curraimpp}/{self.maxaimpp}pp| speed:{self.currspeedpp}/{self.maxspeedpp}pp| acc:{self.curraccpp}/{self.maxaccpp}pp'


config = Config()

client_id = config.osuclientid
client_secret = config.osuclientsecret

osu_nickname = config.osunickname
osu_password = config.osupassword


p = Player()
r = Room()
b = Beatmap()
pp = PP()


client = MyIRCClient(osu_server, osu_port, osu_nickname, osu_password)
client.start()
