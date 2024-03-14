import irc.client
import re
import requests

import threading

from requests.exceptions import HTTPError

client_id = "xxx"
client_secret = "xxxxxxxxxxxxxxxxxxxx"

osu_server = "irc.ppy.sh"
osu_port = 6667
osu_nickname = "xxxxxx"
osu_password = "xxxxxx"

#定义IRC客户端类
class MyIRCClient:

    def __init__(self, server, port, nickname,password):
        self.irc_react = irc.client.Reactor()
        self.server = self.irc_react.server()
        self.server.connect(server, port, nickname,password)
        self.irc_react.add_global_handler("welcome", self.on_connect)
        self.irc_react.add_global_handler("pubmsg", self.on_pubmsg)
        self.irc_react.add_global_handler("privmsg", self.on_privmsg)
        self.timer = None #定义定时器

    def start(self):
        self.irc_react.process_forever()

    #定义定时任务,每60s执行一次,检查房间状态
    def start_periodic_task(self):
        # Save the Timer object in an instance variable
        self.timer = threading.Timer(60, self.start_periodic_task)
        self.timer.start()
        if r.room_id!="":
            b.get_token()
            text=b.get_match_info(re.findall(r'\d+', r.room_id)[0])
            if ("match-disbanded" in str(text['events'])) == True: #match-disbanded #比赛关闭
                self.stop_periodic_task()
                #重置
                p.reset_player_list()
                p.clear_approved_list()
                p.approved_host_rotate_list.clear()
                b.clear_cache()
                r.create_room(self.server,"")
    #停止定时任务
    def stop_periodic_task(self):
        if self.timer is not None:
            self.timer.cancel()
            self.timer = None

    def on_connect(self, connection, event):
        r.get_last_room_id()
        r.close_last_room(connection,event)
        r.create_room(connection, event)

    def on_privmsg(self, connection, event):
        print(f"收到私人消息  {event.source.split('!')[0]}:{event.arguments[0]}")  # 打印接收到的私人消息
        text=event.arguments[0]
        #匹配第一次收到的房间号
        if text.find("Created the tournament match")!=-1 and event.source.find("BanchoBot")!=-1:
            romm_id="#mp_"+re.findall(r'\d+', text)[0]
            #更新room变量
            r.change_room_id(romm_id)
            #加入并监听房间
            r.join_room(connection, event)
            #修改房间密码
            r.change_password(connection, event)
            #保存房间IDs
            r.save_last_room_id()
            #启动定时任务
            self.start_periodic_task()
            
    def on_pubmsg(self, connection, event):
        print(f"收到频道消息  {event.source.split('!')[0]}:{event.arguments[0]}")  # 打印接收到的消息
        text=event.arguments[0]
        #加入房间
        if text.find("joined in slot")!=-1:
            playerid=re.findall(r'.*(?= joined in slot)',text)[0]
            print(f'玩家{playerid}加入房间')
            #如果第一次加入房间，更换房主
            if len(p.room_host_list)==0:
                r.change_host(connection,event,playerid)
            #加入房间队列，玩家队列
            p.add_host(playerid)
            p.add_player(playerid)
            print(f'玩家队列{p.player_list}')
        #离开房间
        if text.find("left the game")!=-1:
            playerid=re.findall(r'.*(?= left the game)',text)[0]
            print(f'玩家{playerid}离开房间')
            #不移除房主队列
            p.remove_player(playerid)
            print(f'玩家队列{p.player_list}')
        #地图变化
        if text.find("Beatmap changed to")!=-1:
            beatmap_url=re.findall(r'(?<=\()\S+(?=\))',text)[0]
            beatmap_id=re.findall(r'\d+', beatmap_url)[0]
            b.change_beatmap_id(beatmap_id)
            #获取地图信息
            b.get_token()
            b.get_beatmap_info()
            r.send_msg(connection,event,b.return_beatmap_info())

        #房主变化
        if text.find("became the host")!=-1:
            p.room_host=re.findall(r'.*(?= became the host)',text)[0]
            print(f'房主变为{p.room_host}')
    
        #准备就绪，开始游戏
        if text.find("All players are ready")!=-1:
            r.start_room(connection,event)

        #开始游戏
        if text.find("The match has started")!=-1:
            #将房主队列第一个人移动到最后
            p.host_rotate_pending(connection,event)
            p.clear_approved_list()

        #游戏结束,更换房主
        if text.find("The match has finished")!=-1:
            #对比房主队列,去除离开的玩家,更新房主队列
            p.host_rotate(connection,event)
            #换了房主以后立即清空投票列表
            p.approved_host_rotate_list.clear()
            p.clear_approved_list()
            #发送队列
            r.send_msg(connection,event,str(f'当前队列：{p.room_host_list}'))
    
        #投票丢弃游戏
        if text == "!abort":
            p.vote_for_abort(connection,event)
        if text == "！abort":
            p.vote_for_abort(connection,event)
        if text == "!ABORT":
            p.vote_for_abort(connection,event)
        if text == "！ABORT":
            p.vote_for_abort(connection,event)
    
        #投票开始游戏
        if text == "!start":
            p.vote_for_start(connection,event)
        if text == "！start":
            p.vote_for_start(connection,event)
        if text == "!START":
            p.vote_for_start(connection,event)
        if text == "！START":
            p.vote_for_start(connection,event)
    
        #投票跳过房主
        if text == "!skip":
            p.vote_for_host_rotate(connection,event)
        if text == "！skip":
            p.vote_for_host_rotate(connection,event)
        if text == "!SKIP":
            p.vote_for_host_rotate(connection,event)
        if text == "！SKIP":
            p.vote_for_host_rotate(connection,event)
    
        #投票关闭房间s
        if text == "!close":
            p.vote_for_close_room(connection,event)
        if text == "！close":
            p.vote_for_close_room(connection,event)
        if text == "!CLOSE":
            p.vote_for_close_room(connection,event)
        if text == "！CLOSE":
            p.vote_for_close_room(connection,event)
    
        #查看队列
        if text == "!queue":
            r.send_msg(connection,event,str(f'当前队列：{p.queue}'))
        if text == "！queue":
            r.send_msg(connection,event,str(f'当前队列：{p.queue}'))
        if text == "!QUEUE":
            r.send_msg(connection,event,str(f'当前队列：{p.queue}'))
        if text == "！QUEUE":
            r.send_msg(connection,event,str(f'当前队列：{p.queue}'))

        #帮助
        if text == "help":
            r.send_msg(connection,event,r.help())
        if text == "HELP":
            r.send_msg(connection,event,r.help())

        #快速查询成绩
        if text == "!pr":
            b.get_user_id(event.source.split('!')[0])
            r.send_msg(connection,event,b.get_recent_info(event.source.split('!')[0]))
        if text == "！pr":
            b.get_user_id(event.source.split('!')[0])
            r.send_msg(connection,event,b.get_recent_info(event.source.split('!')[0]))
        if text == "!PR":
            b.get_user_id(event.source.split('!')[0])
            r.send_msg(connection,event,b.get_recent_info(event.source.split('!')[0]))
        if text == "！PR":
            b.get_user_id(event.source.split('!')[0])
            r.send_msg(connection,event,b.get_recent_info(event.source.split('!')[0]))

        #快速当前谱面成绩
        if text == "!s":
            b.get_user_id(event.source.split('!')[0])
            r.send_msg(connection,event,b.get_beatmap_score(event.source.split('!')[0]))
        if text == "！s":
            b.get_user_id(event.source.split('!')[0])
            r.send_msg(connection,event,b.get_beatmap_score(event.source.split('!')[0]))
        if text == "!S":
            b.get_user_id(event.source.split('!')[0])
            r.send_msg(connection,event,b.get_beatmap_score(event.source.split('!')[0]))
        if text == "！S":
            b.get_user_id(event.source.split('!')[0])
            r.send_msg(connection,event,b.get_beatmap_score(event.source.split('!')[0]))


#定义玩家类
class Player:
    def __init__(self):
        self.player_list = []
        self.room_host_list=[]
        self.approved_abort_list=[]
        self.approved_start_list=[]
        self.approved_host_rotate_list=[]
        self.approved_close_list=[]
        self.room_host=""

    def add_player(self,name):
        self.player_list.append(name)

    def add_host(self,name):
        self.room_host_list.append(name)
    
    def remove_host(self,name):
        if name in self.room_host_list:
            self.room_host_list.remove(name)

    def remove_player(self,name):
        if name in self.player_list:
            self.player_list.remove(name)

    def reset_player_list(self):
        self.player_list.clear()
    
    def clear_approved_list(self):
        self.approved_abort_list.clear()
        self.approved_start_list.clear()
        self.approved_close_list.clear()
        self.approved_host_rotate_list.clear()

    def host_rotate_pending(self,connection,event):
        now_host=self.room_host_list[0]
        self.remove_host(now_host)
        self.add_host(now_host)

    def host_rotate(self,connection,event):
        self.room_host_list=list(set(self.room_host_list).intersection(set(self.player_list)))
        r.change_host(connection,event,self.room_host_list[0])

    
    def vote_for_abort(self,connection,event):
        #获取发送者名字
        name=event.source.split('!')[0]
        if name not in self.approved_abort_list:
            self.approved_abort_list.append(name)
        if len(self.approved_abort_list)>=round(len(self.player_list)/2):
            r.abort_room(connection,event)
            self.approved_abort_list.clear()
        else:
            r.send_msg(connection,event,r'输入!abort强制放弃比赛 {} / {} '.format(str(len(self.approved_abort_list)),str(round(len(self.player_list)/2))))

    def vote_for_start(self,connection,event):
        #获取发送者名字
        name=event.source.split('!')[0]
        if name not in self.approved_start_list:
            self.approved_start_list.append(name)
        if len(self.approved_start_list)>=round(len(self.player_list)/2):
            r.start_room(connection,event)
            self.approved_start_list.clear()
        else:
            r.send_msg(connection,event,r'输入!start强制开始比赛 {} / {} '.format(str(len(self.approved_start_list)),str(round(len(self.player_list)/2))))
    
    def vote_for_host_rotate(self,connection,event):
        #获取发送者名字
        name=event.source.split('!')[0]
        #如果发送者是房主，直接换房主
        if name == self.room_host:
            self.host_rotate_pending(connection,event)
            self.host_rotate(connection,event)
            self.approved_host_rotate_list.clear()
            print("房主自行更换")
            return
        if name not in self.approved_host_rotate_list:
            self.approved_host_rotate_list.append(name)
        if len(self.approved_host_rotate_list)>=round(len(self.player_list)/2):
            self.host_rotate_pending(connection,event)
            self.host_rotate(connection,event)
            self.approved_host_rotate_list.clear()
        else:
            r.send_msg(connection,event,r'输入!skip强制跳过房主 {} / {} '.format(str(len(self.approved_host_rotate_list)),str(round(len(self.player_list)/2))))
        
    def vote_for_close_room(self,connection,event):
        #获取发送者名字
        name=event.source.split('!')[0]
        if name not in self.approved_close_list:
            self.approved_close_list.append(name)
        if len(self.approved_close_list)==len(self.player_list):
            r.close_room(connection,event)
            self.approved_close_list.clear()
        else:
            r.send_msg(connection,event,r'输入!close强制关闭房间(1min后自动重启) {} / {} '.format(str(len(self.approved_close_list)),str(len(self.player_list))))
        

#定义房间操作类
class Room:
    def __init__(self):
        self.room_id=""
        self.last_romm_id=""
        self.room_password=""
        self.room_name=""
        self.room_player=[]
        self.room_status=""

    def get_last_room_id(self):
        try:
            with open('last_room_id.txt', 'r') as f:
                self.last_romm_id=f.read()
                print(f'获取上一个房间ID{self.last_romm_id}')
        except:
            print("未获取上一个房间ID")

    #保存当前id到文件
    def save_last_room_id(self):
        try:
            with open('last_room_id.txt', 'w') as f:
                f.write(self.room_id)
                print(f'保存当前房间ID{self.room_id}')
        except:
            print("未保存当前房间ID")
    
    def help(self):
        return r'!queue 查看队列 | !abort 投票丢弃游戏 | !start 投票开始游戏 | !skip 投票跳过房主 | !close 投票关闭(1min后自动重启)房间 | !pr 查询最近成绩 | !s 查询当前谱面bp | help 查看帮助'

    def change_room_id(self,id):
        self.room_id=id
        print(f'更换当前房间ID为{self.room_id}')
    
    def send_msg(self,connection,evetn,msg_text):
        connection.privmsg(self.room_id, msg_text)
        print("发送消息："+msg_text)

    def close_last_room(self,connection,event):
        if self.last_romm_id!=self.room_id:
            connection.join(self.last_romm_id)
            connection.privmsg(self.last_romm_id, "!mp close")
            connection.part(self.last_romm_id)
            print("关闭上一个房间")
        else:
            print("不需要关闭上一个房间")

    def create_room(self,connection,event):
        connection.privmsg("BanchoBot", "!mp make ATRI高性能MP房 | 自动轮换 | 全天常驻")
        print("创建房间")

    def join_room(self,connection, event):
        connection.join(self.room_id)  # 加入 #osu 频道
        print(f'加入房间{self.room_id}')

    def close_room(self,connection, event):
        connection.privmsg(self.room_id, "!mp close")
        print(f'关闭房间{self.room_id}')

    def change_host(self,connection, event,playerid):
        connection.privmsg(self.room_id, "!mp host "+playerid)
        print("更换房主为 "+playerid)

    def start_room(self,connection, event):
        connection.privmsg(self.room_id, "!mp start")
        print("开始游戏")

    def abort_room(self,connection, event):
        connection.privmsg(self.room_id, "!mp abort")
        print("丢弃游戏")
    
    def change_password(self,connection, event):
        connection.privmsg(self.room_id, "!mp password a114514")
        print("修改密码")

#定义地图类
class Beatmap:
    def __init__(self):
        self.osu_client_id = client_id
        self.osu_client_secret = client_secret
        self.osu_token = ""
        self.beatmap_id=""
        self.beatmap_name=""
        self.beatmap_artist=""
        self.beatmap_star=""
        self.beatmap_status=""
        self.beatemap_bpm=""
        self.beatmap_cs=""
        self.beatmap_ar=""
        self.beatmap_od=""
        self.beatmap_length=""
        self.beatmap_ranked_date=""
        self.beatmatp_submit_date=""
        self.beatmap_mirror_url=""

        self.id2name={}

        self.pr_title=""
        self.pr_artist=""
        self.pr_star=""

        self.pr_acc=0
        self.pr_maxcombo=0
        self.pr_300=0
        self.pr_100=0
        self.pr_50=0
        self.pr_miss=0
        self.pr_pp=0
        self.pr_rank=""
        self.pr_mods=""

        self.pr_username=""



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
            self.osu_token=response.json()['access_token']
        except:
            self.osu_token=""
            print("获取访问令牌失败")
    
    # 使用访问令牌查询
    def get_beatmap_info(self):
        try:
            url=f'https://osu.ppy.sh/api/v2/beatmaps/'+self.beatmap_id
            headers = {'Authorization': f'Bearer {self.osu_token}'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 如果请求失败，这会抛出一个异常

            self.beatmap_name=response.json()['beatmapset']['title']
            self.beatmap_artist=response.json()['beatmapset']['artist']
            self.beatmap_star=response.json()['difficulty_rating']
            self.beatmap_status=response.json()['status']
            self.beatemap_bpm=response.json()['bpm']
            self.beatmap_cs=response.json()['cs']
            self.beatmap_ar=response.json()['ar']
            self.beatmap_od=response.json()['accuracy']
            self.beatmap_length=response.json()['total_length']
            if self.beatmap_status=="ranked":
                self.beatmap_ranked_date=response.json()['beatmapset']['ranked_date'][:10]
            else:
                self.beatmap_ranked_date=response.json()['beatmapset']['submitted_date'][:10]
            self.beatmap_mirror_url="https://osu.sayobot.cn/home?search="+self.beatmap_id
        except:
            print("获取地图信息失败")
            self.beatmap_name="获取地图信息失败"
            self.beatmap_artist=""
            self.beatmap_star=""
            self.beatmap_status=""
            self.beatemap_bpm=""
            self.beatmap_cs=""
            self.beatmap_ar=""
            self.beatmap_od=""
            self.beatmap_length=""
            self.beatmap_ranked_date=""
            self.beatmap_mirror_url=""

    def change_beatmap_id(self,id):
        self.beatmap_id=id
        print(f'更换地图ID为 {self.beatmap_id}')

    def return_beatmap_info(self):
        result=r'{} {}| {}*| {} - {}| bpm:{} length:{}s cs:{} ar:{} od:{}| [{} Sayobot]'.format(self.beatmap_ranked_date,self.beatmap_status,self.beatmap_star,self.beatmap_name,self.beatmap_artist,self.beatemap_bpm,self.beatmap_length,self.beatmap_cs,self.beatmap_ar,self.beatmap_od,self.beatmap_mirror_url)
        print(result)
        return result
    
    def get_match_info(self,match_id):
        try:
            url = f'https://osu.ppy.sh/api/v2/matches/{match_id}'
            headers = {'Authorization': f'Bearer {self.osu_token}'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 如果请求失败，这将抛出一个异常
            return response.json()
        except:
            print("获取比赛信息失败")
    
    def get_user_id(self,username):
        try:
            if username not in self.id2name:
                print("获取用户ID")
                url = f'https://osu.ppy.sh/api/v2/users/{username}'
                headers = {'Authorization': f'Bearer {self.osu_token}'}
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # 如果请求失败，这将抛出一个异常
                self.id2name[username]=response.json()['id']
                print(self.id2name)
        except:
            print("获取用户ID失败")

    def get_beatmap_score(self, username):
        try:
            user_id=self.id2name[username]
            url = f"https://osu.ppy.sh/api/v2/beatmaps/{self.beatmap_id}/scores/users/{user_id}"
            headers = {'Authorization': f'Bearer {self.osu_token}'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 如果请求失败，这会抛出一个异常
            
            self.pr_title=self.beatmap_name
            self.pr_artist=self.beatmap_artist
            self.pr_star=self.beatmap_star

            self.pr_acc=response.json()['score']['accuracy']
            self.pr_maxcombo=response.json()['score']['max_combo']
            self.pr_300=response.json()['score']['statistics']['count_300']
            self.pr_100=response.json()['score']['statistics']['count_100']
            self.pr_50=response.json()['score']['statistics']['count_50']
            self.pr_miss=response.json()['score']['statistics']['count_miss']
            self.pr_pp=response.json()['score']['pp']
            self.pr_rank=response.json()['score']['rank']
            self.pr_mods=response.json()['score']['mods']
            self.pr_username=username

            self.pr_acc=round(self.pr_acc*100,2)

            if self.pr_mods==[]:
                self.pr_mods="NM"
            else:
                tempmod=""
                for i in self.pr_mods:
                    tempmod=tempmod+i
                self.pr_mods=tempmod
        
        except HTTPError:
            print(f"获取谱面成绩失败,可能是{username}未在谱面上留下成绩")
            return f"获取谱面成绩失败,可能是{username}未在谱面上留下成绩"

        except:
            print("获取谱面成绩失败")
            self.pr_title="获取谱面成绩失败"
            self.pr_artist=""
            self.pr_star=""
            self.pr_acc=0
            self.pr_maxcombo=0
            self.pr_300=0
            self.pr_100=0
            self.pr_50=0
            self.pr_miss=0
            self.pr_pp=0
            self.pr_rank=""
            self.pr_mods=""
            self.pr_username=""

        result=r'{}| {} - {}| {}*| {} {} {}pp acc:{}% combo:{}x  300: {}x  100: {}x  50: {}x  miss: {}x'.format(self.pr_username,self.pr_title,self.pr_artist,self.pr_star,self.pr_mods,self.pr_rank,self.pr_pp,self.pr_acc,self.pr_maxcombo,self.pr_300,self.pr_100,self.pr_50,self.pr_miss,)
        print(result)
        return result
    

    def get_recent_info(self,username):
        try:
            user_id=self.id2name[username]
            url = f'https://osu.ppy.sh/api/v2/users/{user_id}/scores/recent'
            headers = {'Authorization': f'Bearer {self.osu_token}'}
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # 如果请求失败，这将抛出一个异常


            self.pr_title=response.json()[0]['beatmapset']['title']
            self.pr_artist=response.json()[0]['beatmapset']['artist']
            self.pr_star=response.json()[0]['beatmap']['difficulty_rating']


            self.pr_acc=response.json()[0]['accuracy']
            self.pr_maxcombo=response.json()[0]['max_combo']
            self.pr_300=response.json()[0]['statistics']['count_300']
            self.pr_100=response.json()[0]['statistics']['count_100']
            self.pr_50=response.json()[0]['statistics']['count_50']
            self.pr_miss=response.json()[0]['statistics']['count_miss']
            self.pr_pp=response.json()[0]['pp']
            self.pr_rank=response.json()[0]['rank']
            self.pr_mods=response.json()[0]['mods']
            self.pr_username=username

            self.pr_acc=round(self.pr_acc*100,2)

            if self.pr_mods==[]:
                self.pr_mods="NM"
            else:
                tempmod=""
                for i in self.pr_mods:
                    tempmod=tempmod+i
                self.pr_mods=tempmod
            
        
        except:
            print("获取最近成绩失败")
            self.pr_title="获取最近成绩失败"
            self.pr_artist=""
            self.pr_star=""
            self.pr_acc=0
            self.pr_maxcombo=0
            self.pr_300=0
            self.pr_100=0
            self.pr_50=0
            self.pr_miss=0
            self.pr_pp=0
            self.pr_rank=""
            self.pr_mods=""
            self.pr_username=""
            
        result=r'{}| {} - {}| {}*| {} {} {}pp acc:{}% combo:{}x  300: {}x  100: {}x  50: {}x  miss: {}x'.format(self.pr_username,self.pr_title,self.pr_artist,self.pr_star,self.pr_mods,self.pr_rank,self.pr_pp,self.pr_acc,self.pr_maxcombo,self.pr_300,self.pr_100,self.pr_50,self.pr_miss,)
        print(result)
        return result


p=Player()
r=Room()
b=Beatmap()


client = MyIRCClient(osu_server, osu_port, osu_nickname,osu_password)
client.start()
