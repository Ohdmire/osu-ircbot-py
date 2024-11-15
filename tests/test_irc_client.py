import unittest
import requests
import time
from unittest.mock import patch, MagicMock
from io import StringIO
import irc_dlient
import rosu_pp_py as rosu

class TestMyIRCClient(unittest.TestCase):
    def setUp(self):
        # 构造模拟config
        self.mock_config = MagicMock()
        self.mock_config.osuclientid = 'test_client_id'
        self.mock_config.osuclientsecret = 'test_client_secret'
        self.mock_config.timelimit = '100'  # Example value
        self.mock_config.starlimit = '5.0'
        self.mock_config.mpname = 'TestMP'
        self.mock_config.mppassword = 'testpassword'
        
        # 创建Player、Room、Beatmap和PP实例
        self.player = irc_dlient.Player()
        self.room = irc_dlient.Room(self.mock_config)
        self.beatmap = irc_dlient.Beatmap(self.mock_config)
        self.pp = irc_dlient.PP()

        # 模拟Room类的方法
        self.room.join_room = MagicMock()
        self.room.change_password = MagicMock()
        self.room.get_mp_settings = MagicMock()
        self.room.create_room = MagicMock()
        self.room.close_room = MagicMock()
        self.room.change_host = MagicMock()
        self.room.start_room = MagicMock()
        self.room.abort_room = MagicMock()
        self.room.change_beatmap_to = MagicMock()
        self.room.change_mods_to_FM = MagicMock()
        self.room.get_mp_settings = MagicMock()
        self.room.send_msg = MagicMock()
        self.room.change_room_id = MagicMock()
        self.room.save_last_room_id = MagicMock()
        
        # 模拟PP类的方法
        self.pp.calculate_pp_fully = MagicMock(return_value="mock_pp_result")
        self.pp.calculate_pp_obj = MagicMock(return_value="mock_pp_obj_result")
        self.pp.get_beatmap_file = MagicMock()
        
        # 模拟Beatmap类的方法
        self.beatmap.get_match_info = MagicMock(return_value={'events': ['match-disbanded']})
        self.beatmap.get_recent_info = MagicMock(return_value="mock_recent_info")
        self.beatmap.get_user_id = MagicMock()
        self.beatmap.get_token = MagicMock()
        self.beatmap.get_beatmap_info = MagicMock()

        # 模拟Player类的方法
        self.player.vote_for_abort = MagicMock()
        self.player.vote_for_start = MagicMock()
        self.player.vote_for_host_rotate = MagicMock()
        self.player.vote_for_close_room = MagicMock()
        self.player.convert_host = MagicMock()
        self.player.extract_player_name = MagicMock(return_value="BanchoBot114")
        
        # 创建MyIRCClient实例，但不实际连接服务器
        with patch('irc.client.Reactor') as MockReactor:
            self.mock_reactor = MockReactor.return_value
            self.mock_server = self.mock_reactor.server.return_value
            self.client = irc_dlient.MyIRCClient("irc.ppy.sh", 6667, self.mock_config, self.player, self.room, self.beatmap, self.pp)

    def tearDown(self):
        self.client.stop()
        time.sleep(0.1)

    @patch('builtins.input', side_effect=["stop"])
    @patch('builtins.print')
    def test_on_connect_existing_room(self, mock_print, mock_input):
        """
        测试已存在房间
        """
        # 模拟获取上一个房间ID
        self.room.room_id = "#mp_114514"
        self.room.get_last_room_id = MagicMock(return_value="#mp_114514")
        self.client.check_last_room_status = MagicMock(return_value=True)
        
        # 创建一个模拟的连接和事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        
        # 调用on_connect
        self.client.on_connect(mock_connection, mock_event)
        time.sleep(0.1)
        
        # 断言加入房间和修改密码被调用
        self.room.join_room.assert_called_with(mock_connection, mock_event)
        self.room.change_password.assert_called_with(mock_connection, mock_event)
        self.room.get_mp_settings.assert_called_with(mock_connection, mock_event)
        
        # 断言已连接事件
        self.assertTrue(self.client.has_connected.is_set())


    @patch('builtins.input', side_effect=["stop"])
    @patch('builtins.print')
    def test_on_connect_new_room(self, mock_print, mock_input):
        """
        测试新房间
        """
        # 模拟获取上一个房间ID为空
        self.room.get_last_room_id = MagicMock(return_value="")
        self.client.check_last_room_status = MagicMock(return_value=False)
        
        # 创建一个模拟的连接和事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        
        # 调用on_connect，启动发送消息的线程
        self.client.on_connect(mock_connection, mock_event)
        
        # 等待线程运行，确保input被调用
        time.sleep(0.2)  # 根据需要调整等待时间
        
        # 断言创建房间被调用
        self.room.create_room.assert_called_with(mock_connection, mock_event)
        
        # 断言已连接事件
        self.assertTrue(self.client.has_connected.is_set())
        

    @patch('builtins.input', side_effect=["!start", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_start_command(self, mock_print, mock_input):
        """
        测试处理!start命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["!start"]
        # 一个叫BanchoBot114的用户发送了!start命令
        mock_event.source = "BanchoBot114!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言投票开始游戏的方法被调用
        self.player.vote_for_start.assert_called_with(mock_connection, mock_event)

    @patch('builtins.input', side_effect=["!abort", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_abort_command(self, mock_print, mock_input):
        """
        测试处理!abort命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["!abort"]
        # 一个叫BanchoBot114的用户发送了!abort命令
        mock_event.source = "BanchoBot114!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言投票丢弃游戏的方法被调用
        self.client.p.vote_for_abort.assert_called_with(mock_connection, mock_event)

    @patch('builtins.input', side_effect=["!skip", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_skip_command(self, mock_print, mock_input):
        """
        测试处理!skip命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["!skip"]
        # 一个叫BanchoBot114的用户发送了!skip命令
        mock_event.source = "BanchoBot114!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言投票跳过房主的方法被调用
        self.client.p.vote_for_host_rotate.assert_called_with(mock_connection, mock_event)

    @patch('builtins.input', side_effect=["!close", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_close_command(self, mock_print, mock_input):
        """
        测试处理!close命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["!close"]
        # 一个叫BanchoBot114的用户发送了!close命令
        mock_event.source = "BanchoBot114!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言投票关闭房间的方法被调用
        self.client.p.vote_for_close_room.assert_called_with(mock_connection, mock_event)

    @patch('builtins.input', side_effect=["!queue", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_queue_command(self, mock_print, mock_input):
        """
        测试处理!queue命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["!queue"]
        # 一个叫BanchoBot114的用户发送了!queue命令
        mock_event.source = "BanchoBot114!user@ppy.sh"
        self.client.p.remain_hosts_to_player = MagicMock(return_value=1)

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言转换房主的方法被调用
        self.client.p.convert_host.assert_called()
        # 断言剩余人数获取方法被调用
        self.client.p.remain_hosts_to_player.assert_called_with("BanchoBot114")
        # 断言发送消息的方法被调用
        self.client.r.send_msg.assert_called_with(mock_connection, mock_event, "你前面剩余人数：1")

    @patch('builtins.input', side_effect=["help", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_help_command(self, mock_print, mock_input):
        """
        测试处理help命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["help"]
        # 一个叫BanchoBot114的用户发送了help命令
        mock_event.source = "BanchoBot114!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言帮助信息发送的方法被调用
        self.client.r.send_msg.assert_called_with(mock_connection, mock_event, self.client.r.help())

    @patch('builtins.input', side_effect=["!pr", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_pr_command(self, mock_print, mock_input):
        """
        测试处理!pr命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["!pr"]
        # 一个叫BanchoBot114的用户发送了!pr命令
        mock_event.source = "BanchoBot114!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言获取用户ID的方法被调用
        self.client.b.get_user_id.assert_called_with(mock_event.source.split('!')[0])
        # 断言获取最近信息的方法被调用
        self.client.b.get_recent_info.assert_called_with(mock_event.source.split('!')[0])
        # 断言获取谱面文件的方法被调用
        self.client.pp.get_beatmap_file.assert_called_with(beatmap_id=self.client.b.pr_beatmap_id)
        # 断言计算PP对象的方法被调用
        self.client.pp.calculate_pp_obj.assert_called_with(
            mods=self.client.b.pr_mods,
            combo=self.client.b.pr_maxcombo,
            acc=self.client.b.pr_acc,
            misses=self.client.b.pr_miss
        )
        # 断言发送消息的方法被调用两次
        self.assertEqual(self.client.r.send_msg.call_count, 2)

    @patch('builtins.input', side_effect=["!ping", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_ping_command(self, mock_print, mock_input):
        """
        测试处理!ping命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["!ping"]
        # 一个叫BanchoBot114的用户发送了!ping命令
        mock_event.source = "BanchoBot114!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言发送'ping'响应的方法被调用
        self.client.r.send_msg.assert_called_with(mock_connection, mock_event, 'pong')

    @patch('builtins.input', side_effect=["!m+", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_m_plus_command(self, mock_print, mock_input):
        """
        测试处理!m+命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["!m+HardRock"]
        # 一个叫BanchoBot114的用户发送了!m+HardRock命令
        mock_event.source = "BanchoBot114!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言获取谱面文件的方法被调用
        self.client.pp.get_beatmap_file.assert_called_with(beatmap_id=self.client.b.beatmap_id)
        # 断言计算PP完全的方法被调用
        self.client.pp.calculate_pp_fully.assert_called_with('HardRock')
        # 断言发送消息的方法被调用
        self.client.r.send_msg.assert_called_with(mock_connection, mock_event, self.client.pp.calculate_pp_fully('HardRock'))

    @patch('builtins.input', side_effect=["!about", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_about_command(self, mock_print, mock_input):
        """
        测试处理!about命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["!about"]
        # 一个叫BanchoBot114的用户发送了!about命令
        mock_event.source = "BanchoBot114!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言发送关于信息的方法被调用
        self.client.r.send_msg.assert_called_with(
            mock_connection, 
            mock_event, 
            "[https://github.com/Ohdmire/osu-ircbot-py ATRI高性能bot]"
        )

    @patch('builtins.input', side_effect=["！start", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_start_command_with_full_width_exclamation(self, mock_print, mock_input):
        """
        测试处理全角感叹号的!start命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["！start"]  # 全角感叹号
        # 一个叫BanchoBot114的用户发送了！start命令
        mock_event.source = "BanchoBot114!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言投票开始游戏的方法被调用
        self.client.p.vote_for_start.assert_called_with(mock_connection, mock_event)

    @patch('builtins.input', side_effect=["！i", "stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_start_command_with_full_width_exclamation(self, mock_print, mock_input):
        """
        测试处理全角感叹号的!i命令
        """
        # 模拟公共消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["！i"]  # 全角感叹号
        # 一个叫BanchoBot114的用户发送了！i命令
        mock_event.source = "BanchoBot114!user@ppy.sh"
        self.client.b.beatmap_mirror_sayo_url = "https://osu.sayobot.cn/home?search=1"
        self.client.b.beatmap_mirror_inso_url = "http://inso.link/yukiho/?b=1"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言方法被调用
        self.client.b.get_token.assert_called()
        self.client.b.get_beatmap_info.assert_called()
        self.client.r.send_msg.assert_called_with(mock_connection, mock_event, ' | 0*| [  - ]| bpm: length:0s| ar: cs: od: hp:| [https://osu.sayobot.cn/home?search=1 Sayobot] OR [http://inso.link/yukiho/?b=1 inso]')

    @patch('builtins.print')
    def test_on_privmsg_handle_room_creation_message_failure(self, mock_print):
        """
        测试处理来自BanchoBot的房间创建消息失败的情况（消息格式错误）
        """
        # 模拟接收私有消息事件，格式错误
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["Created the tournament match"]  # 缺少房间ID
        mock_event.source = "BanchoBot114!user@host"

        # 调用on_privmsg
        self.client.on_privmsg(mock_connection, mock_event)
        
        # 断言room_id为空，并检查相关方法的调用
        self.client.r.change_room_id.assert_called_with("")
        self.client.r.join_room.assert_called_with(mock_connection, mock_event)
        self.client.r.change_password.assert_called_with(mock_connection, mock_event)
        self.client.r.save_last_room_id.assert_called()
        self.assertTrue(self.client.timer)

    @patch('builtins.print')
    def test_on_privmsg_handle_non_bancho_bot_message(self, mock_print):
        """
        测试处理来自非BanchoBot的私有消息
        """
        # 模拟接收私有消息事件，非BanchoBot发送
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["Some random message"]
        mock_event.source = "BanchoBot!user@ppy.sh"

        # 调用on_privmsg
        self.client.on_privmsg(mock_connection, mock_event)
        
        # 断言相关方法未被调用
        self.client.r.change_room_id.assert_not_called()
        self.client.r.join_room.assert_not_called()
        self.client.r.change_password.assert_not_called()
        self.client.r.save_last_room_id.assert_not_called()
        self.assertFalse(self.client.timer)

    @patch('builtins.input', side_effect=["stop"])
    @patch('builtins.print')
    def test_on_pubmsg_handle_exception_in_room_creation(self, mock_print, mock_input):
        """
        测试处理来自BanchoBot的房间创建消息时发生异常的情况
        """
        # 模拟接收频道消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["joined in slot"]
        mock_event.source = "BanchoBot!user@ppy.sh"

        # 设置send_msg方法抛出异常
        self.client.r.send_msg.side_effect = Exception("模拟异常")

        # 调用on_pubmsg
        try:
            self.client.on_pubmsg(mock_connection, mock_event)
        except Exception as e:
            self.client.stop_periodic_task()
        
        # 断言打印了错误信息
        mock_print.assert_called_with(f'-----------------未知错误---------------------\n模拟异常')

    # @patch('builtins.print')
    # def test_on_privmsg_handle_multiple_room_creation_messages(self, mock_print):
    #     """
    #     测试处理连续多条来自BanchoBot的房间创建消息
    #     """
    #     # 模拟接收第一个私有消息事件
    #     mock_connection1 = MagicMock()
    #     mock_event1 = MagicMock()
    #     mock_event1.arguments = ["Created the tournament match (123456)"]
    #     mock_event1.source = "收到消息  BanchoBot:Created the tournament match (123456)"

    #     self.client.on_privmsg(mock_connection1, mock_event1)

    #     # 断言第一次调用
    #     self.client.r.change_room_id.assert_called_with("#mp_123456")
    #     self.client.r.join_room.assert_called_with(mock_connection1, mock_event1)
    #     self.client.r.change_password.assert_called_with(mock_connection1, mock_event1)
    #     self.client.r.save_last_room_id.assert_called()
    #     self.assertTrue(self.client.timer)

    #     # 重置mock
    #     self.client.r.change_room_id.reset_mock()
    #     self.client.r.join_room.reset_mock()
    #     self.client.r.change_password.reset_mock()
    #     self.client.r.save_last_room_id.reset_mock()

    #     # 模拟接收第二个私有消息事件
    #     mock_connection2 = MagicMock()
    #     mock_event2 = MagicMock()
    #     mock_event2.arguments = ["Created the tournament match (654321)"]
    #     mock_event2.source = "收到消息  BanchoBot:Created the tournament match (654321)"

    #     self.client.on_privmsg(mock_connection2, mock_event2)

    #     # 断言第二次调用
    #     self.client.r.change_room_id.assert_called_with("#mp_654321")
    #     self.client.r.join_room.assert_called_with(mock_connection2, mock_event2)
    #     self.client.r.change_password.assert_called_with(mock_connection2, mock_event2)
    #     self.client.r.save_last_room_id.assert_called()
    #     self.assertTrue(self.client.timer)

    @patch('builtins.print')
    def test_on_pubmsg_handle_bot_joined_room(self, mock_print):
        """
        测试处理ATRI加入房间后，BanchoBot发送的房间信息
        """
        # 模拟接收频道消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["Slot 1 Ready https://osu.ppy.sh/u/1234567890 BanchoBot114     [Host]"]
        mock_event.source = "BanchoBot!cho@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言
        self.assertEqual("BanchoBot114", self.client.p.room_host_list[0])
        self.assertEqual("BanchoBot114", self.client.p.player_list[0])
        

    @patch('builtins.print')
    def test_on_pubmsg_handle_beatmap_changed_message(self, mock_print):
        """
        测试处理来自BanchoBot的谱面变化消息
        """
        # 模拟接收频道消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["Beatmap changed to (https://osu.ppy.sh/b/1234567890)"]
        mock_event.source = "BanchoBot!user@ppy.sh"
        self.client.b.beatmap_id = ""

        self.client.b.check_beatmap_if_out_of_star = MagicMock(return_value=True)
        self.client.on_pubmsg(mock_connection, mock_event)
        self.assertEqual("3459231", self.client.b.beatmap_id)

        self.client.b.check_beatmap_if_out_of_star = MagicMock(return_value=False)
        self.client.b.check_beatmap_if_out_of_time = MagicMock(return_value=True)
        self.client.on_pubmsg(mock_connection, mock_event)
        self.assertEqual("3459231", self.client.b.beatmap_id)

        self.client.b.beatmap_id = "1"
        self.client.b.check_beatmap_if_out_of_star = MagicMock(return_value=False)
        self.client.b.check_beatmap_if_out_of_time = MagicMock(return_value=False)
        self.client.on_pubmsg(mock_connection, mock_event)
        self.assertEqual("1234567890", self.client.b.beatmap_id)
        self.client.r.send_msg.assert_called()

    @patch('builtins.print')
    def test_on_pubmsg_handle_room_host_changed_message(self, mock_print):
        """
        测试处理来自BanchoBot的房间房主变化消息
        """
        # 模拟接收频道消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["BanchoBot114 became the host"]
        mock_event.source = "BanchoBot!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言
        self.assertEqual("BanchoBot114", self.client.p.room_host)

    def test_on_pubmsg_handle_bancho_restart_message(self):
        """
        测试处理来自BanchoBot的服务器重启消息
        """
        # 模拟接收频道消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["Bancho will be right back!"]
        mock_event.source = "BanchoBot!user@ppy.sh"

        # 保存调用on_pubmsg前的restarting_task
        restarting_task = self.client.restarting_task

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        time.sleep(125)
        
        # 断言
        self.assertNotEqual(restarting_task, self.client.restarting_task)
        
    @patch('builtins.print')
    def test_on_pubmsg_handle_player_joined_room(self, mock_print):
        """
        测试处理玩家加入房间后，BanchoBot发送的房间信息
        """
        # 模拟接收频道消息事件
        mock_connection = MagicMock()
        mock_event = MagicMock()
        mock_event.arguments = ["BanchoBot114 joined in slot"]
        mock_event.source = "BanchoBot!user@ppy.sh"

        # 调用on_pubmsg
        self.client.on_pubmsg(mock_connection, mock_event)
        
        # 断言
        self.assertEqual("BanchoBot114", self.client.p.room_host_list[0])
        self.assertEqual("BanchoBot114", self.client.p.player_list[0])

class TestConfig(unittest.TestCase):
    @patch('irc_dlient.configparser.ConfigParser')
    @patch('irc_dlient.chardet.detect')
    @patch('builtins.open')
    def test_config_initialization(self, mock_open, mock_detect, mock_configparser):
        # 设置模拟返回值
        mock_detect.return_value = {'encoding': 'utf-8'}
        mock_config = MagicMock()
        mock_config.__getitem__.return_value = {
            'client_id': 'test_id',
            'client_secret': 'test_secret',
            'nickname': 'test_nick',
            'password': 'test_pass',
            'mpname': 'test_mp',
            'starlimit': '5.0',
            'timelimit': '300',
            'mppassword': 'mp_pass'
        }
        mock_configparser.return_value = mock_config

        config = irc_dlient.Config()

        self.assertEqual(config.osuclientid, 'test_id')
        self.assertEqual(config.osuclientsecret, 'test_secret')
        self.assertEqual(config.osunickname, 'test_nick')
        self.assertEqual(config.osupassword, 'test_pass')
        self.assertEqual(config.mpname, 'test_mp')
        self.assertEqual(config.starlimit, '5.0')
        self.assertEqual(config.timelimit, '300')
        self.assertEqual(config.mppassword, 'mp_pass')

class TestPlayer(unittest.TestCase):
    def setUp(self):
        self.player = irc_dlient.Player()

    def test_add_player(self):
        self.player.add_player("Player1")
        self.assertIn("Player1", self.player.player_list)

    def test_remove_player(self):
        self.player.add_player("Player1")
        self.player.remove_player("Player1")
        self.assertNotIn("Player1", self.player.player_list)

    def test_add_host(self):
        self.player.add_host("Host1")
        self.assertIn("Host1", self.player.room_host_list)

    def test_remove_host(self):
        self.player.add_host("Host1")
        self.player.remove_host("Host1")
        self.assertNotIn("Host1", self.player.room_host_list)

class TestBeatmap(unittest.TestCase):
    def setUp(self):
        # 构造模拟config
        self.mock_config = MagicMock()
        self.mock_config.osuclientid = 'test_client_id'
        self.mock_config.osuclientsecret = 'test_client_secret'
        self.mock_config.timelimit = '100'  # Example value
        self.mock_config.starlimit = '5.0'
        self.mock_config.mpname = 'TestMP'
        self.mock_config.mppassword = 'testpassword'

        # 实例化Beatmap
        self.beatmap = irc_dlient.Beatmap(self.mock_config)

    @patch('irc_dlient.requests.post')
    def test_get_token_success(self, mock_post):
        """
        获取 Token 成功
        """
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {'access_token': 'test_token'}
        mock_post.return_value = mock_response

        self.beatmap.get_token()

        self.assertEqual(self.beatmap.osu_token, 'test_token')

    def test_clear_cache(self):
        """
        清除缓存
        """
        self.beatmap.osu_token = "test_token"
        self.beatmap.id2name = {"test_user": "test_id"}
        self.beatmap.clear_cache()
        self.assertEqual(self.beatmap.osu_token, "")
        self.assertEqual(self.beatmap.id2name, {})

    def test_check_beatmap_if_out_of_time(self):
        """
        检查谱面时间限制
        """
        self.mock_config.timelimit = 0
        self.beatmap.beatmap_length = 100
        self.beatmap.check_beatmap_if_out_of_time()
        self.assertEqual(self.beatmap.check_beatmap_if_out_of_time(), False)

        self.beatmap.beatmap_length = 95950
        self.beatmap.check_beatmap_if_out_of_time()
        self.assertEqual(self.beatmap.check_beatmap_if_out_of_time(), False)

        self.mock_config.timelimit = 100
        self.beatmap.beatmap_length = 100
        self.beatmap.check_beatmap_if_out_of_time()
        self.assertEqual(self.beatmap.check_beatmap_if_out_of_time(), False)

        self.beatmap.beatmap_length = 101
        self.beatmap.check_beatmap_if_out_of_time()
        self.assertEqual(self.beatmap.check_beatmap_if_out_of_time(), True)

    @patch('irc_dlient.requests.get')
    def test_get_beatmap_info_success(self, mock_get):
        """
        发送正确的beatmap id到 osu! API
        """
        # 构造mock数据
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            'beatmapset_id': '1',
            'beatmapset': {
                'title_unicode': 'DISCO PRINCE',
                'artist_unicode': 'Kenji Ninuma',
                'ranked_date': '2007-10-06'
            },
            'difficulty_rating': 2.55,
            'status': 'ranked',
            'bpm': 120,
            'cs': 4,
            'ar': 6,
            'accuracy': 6,
            'drain': 6,
            'total_length': 142,
            'url': 'https://osu.ppy.sh/beatmaps/75'
        }
        mock_get.return_value = mock_response

        # 设置 beatmap_id
        self.beatmap.change_beatmap_id('75')  # osu第一个ranked图

        # 调用获取 beatmap 信息的方法
        self.beatmap.get_beatmap_info()

        # 验证响应内容
        self.assertEqual(self.beatmap.beatmap_name, 'DISCO PRINCE')
        self.assertEqual(self.beatmap.beatmap_songs_id, '1')
        self.assertEqual(self.beatmap.beatmap_artist, 'Kenji Ninuma')
        self.assertEqual(self.beatmap.beatmap_star, 2.55)
        self.assertEqual(self.beatmap.beatmap_status, 'ranked')
        self.assertEqual(self.beatmap.beatmap_bpm, 120)
        self.assertEqual(self.beatmap.beatmap_cs, 4)
        self.assertEqual(self.beatmap.beatmap_ar, 6)
        self.assertEqual(self.beatmap.beatmap_od, 6)
        self.assertEqual(self.beatmap.beatmap_hp, 6)
        self.assertEqual(self.beatmap.beatmap_length, 142)
        self.assertEqual(self.beatmap.beatmap_ranked_date, '2007-10-06')
        self.assertEqual(self.beatmap.beatmap_osudirect_url, 'https://osu.ppy.sh/beatmaps/75')
        self.assertEqual(self.beatmap.beatmap_mirror_sayo_url, 'https://osu.sayobot.cn/home?search=1')
        self.assertEqual(self.beatmap.beatmap_mirror_inso_url, 'http://inso.link/yukiho/?b=75')

    @patch('irc_dlient.requests.get')
    def test_get_beatmap_info_with_wrong_beatmap_id(self, mock_get):
        """
        发送错误的beatmap id到 osu! API
        """
        # 构造mock数据
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_response

        # 获取 Token
        self.beatmap.get_token()
        self.assertIsNotNone(self.beatmap.osu_token, "Token 获取失败")

        # 设置 beatmap_id
        self.beatmap.change_beatmap_id('1')  # 错误的beatmap id

        # 调用获取 beatmap 信息的方法
        self.beatmap.get_beatmap_info()

        # 验证响应内容
        self.assertEqual(self.beatmap.beatmap_name, '获取谱面信息失败')
        self.assertEqual(self.beatmap.beatmap_songs_id, '')
        self.assertEqual(self.beatmap.beatmap_artist, '')
        self.assertEqual(self.beatmap.beatmap_star, 0)
        self.assertEqual(self.beatmap.beatmap_status, '')
        self.assertEqual(self.beatmap.beatmap_bpm, '')
        self.assertEqual(self.beatmap.beatmap_cs, '')
        self.assertEqual(self.beatmap.beatmap_ar, '')
        self.assertEqual(self.beatmap.beatmap_od, '')
        self.assertEqual(self.beatmap.beatmap_hp, '')
        self.assertEqual(self.beatmap.beatmap_length, 0)
        self.assertEqual(self.beatmap.beatmap_ranked_date, '')
        self.assertEqual(self.beatmap.beatmap_osudirect_url, '')
        self.assertEqual(self.beatmap.beatmap_mirror_sayo_url, '')
        self.assertEqual(self.beatmap.beatmap_mirror_inso_url, '')

    @patch('irc_dlient.requests.get')
    def test_get_beatmap_score_success(self, mock_get):
        """
        发送正确的username查询分数
        """
        # 设置username
        self.beatmap.id2name = {"LittleStone": "123456"}
        self.beatmap.get_user_id("LittleStone")
        self.assertIsNotNone(self.beatmap.id2name, "用户ID获取失败")

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            'score': {
                'created_at': '2020-12-04T00:00:00+00:00',
                'accuracy': 0.8385,
                'max_combo': 122,
                'statistics': {
                    'count_300': 150,
                    'count_100': 35,
                    'count_50': 6,
                    'count_miss': 3
                },
                'pp': 28.0404,
                'rank': 'C',
                'mods': ['HD', 'HR', 'DT'],
                'beatmap': {
                    'url': 'https://osu.ppy.sh/beatmaps/75'
                }
            }
        }
        mock_get.return_value = mock_response

        # 设置 beatmap_id
        self.beatmap.beatmap_id = '75'  # osu第一个ranked图

        # 调用获取 beatmap 信息的方法
        self.beatmap.get_beatmap_score("LittleStone")
    
        self.assertEqual(self.beatmap.pr_title, '')
        self.assertEqual(self.beatmap.pr_artist, '')
        self.assertEqual(self.beatmap.pr_star, 0)
        self.assertEqual(self.beatmap.beatmap_score_created_at, '2020-12-04')
        self.assertEqual(self.beatmap.pr_acc, 83.85)
        self.assertEqual(self.beatmap.pr_maxcombo, 122)
        self.assertEqual(self.beatmap.pr_300, 150)
        self.assertEqual(self.beatmap.pr_100, 35)
        self.assertEqual(self.beatmap.pr_50, 6)
        self.assertEqual(self.beatmap.pr_miss, 3)
        self.assertEqual(self.beatmap.pr_pp, 28.0404)
        self.assertEqual(self.beatmap.pr_rank, 'C')
        self.assertEqual(self.beatmap.pr_mods, 'HDHRDT')
        self.assertEqual(self.beatmap.pr_beatmap_url, 'https://osu.ppy.sh/beatmaps/75')
        self.assertEqual(self.beatmap.pr_username, 'LittleStone')
        self.assertEqual(self.beatmap.pr_acc, 83.85)
    
    @patch('sys.stdout', new_callable=StringIO)
    def test_get_beatmap_score_with_wrong_username_1(self, fake_out):
        """
        发送错误的username查询分数-场景1
        """
        self.beatmap.id2name = {}
        self.beatmap.get_beatmap_score("PPYNOTPPYGUESSIMPPYORNOT")
        self.assertIn("获取谱面成绩失败", fake_out.getvalue(), "Output does not contain expected failure message.")

    @patch('sys.stdout', new_callable=StringIO)
    def test_get_beatmap_score_with_wrong_username_2(self, fake_out):
        """
        发送错误的username查询分数-场景2
        """
        # 构造mock数据
        mock_post = MagicMock()
        mock_post.raise_for_status = MagicMock()
        mock_post.json.return_value = {'access_token': 'test_token'}
        with patch('irc_dlient.requests.post', return_value=mock_post):
            self.beatmap.get_token()
            self.assertEqual(self.beatmap.osu_token, 'test_token')

        # 设置 username
        self.beatmap.id2name = {"LittleStone": "123456"}

        # 设置 beatmap_id
        self.beatmap.beatmap_id = '75'  # osu第一个ranked图

        # 设置错误的 username，并捕获输出
        self.beatmap.get_beatmap_score("ATRI1024")
        self.assertIn(
            "获取谱面成绩失败，错误信息：'ATRI1024'\n| [ 获取谱面成绩失败 - ]| *|  [  ] 0pp acc:0% combo:0x| 0/0/0/0| date:|\n",
            fake_out.getvalue(),
            "Output does not contain expected failure message."
        )

    @patch('irc_dlient.requests.get')
    @patch('irc_dlient.requests.post')
    def test_get_beatmap_score_with_wrong_beatmap_id(self, mock_post, mock_get):
        """
        发送错误的beatmap id查询分数
        """
        # 构造mock数据
        mock_post_response = MagicMock()
        mock_post_response.raise_for_status = MagicMock()
        mock_post_response.json.return_value = {'access_token': 'test_token'}
        mock_post.return_value = mock_post_response

        # 获取 Token
        self.beatmap.get_token()
        self.assertEqual(self.beatmap.osu_token, 'test_token')

        # 设置 username
        self.beatmap.id2name = {"LittleStone": "123456"}

        # 设置 beatmap_id
        self.beatmap.beatmap_id = '1145141919810'  # 不存在的图

        # 调用获取谱面成绩的方法
        mock_get_response = MagicMock()
        mock_get_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
        mock_get.return_value = mock_get_response

        with patch('sys.stdout', new_callable=StringIO) as fake_out:
            self.beatmap.get_beatmap_score("LittleStone")
            self.assertIn(
                "未查询到LittleStone在该谱面上留下的成绩\n",
                fake_out.getvalue(),
                "Output does not contain expected failure message."
            )

    @patch('irc_dlient.requests.get')
    def test_get_recent_info_success(self, mock_get):
        """
        发送正确的username查询最近成绩，并模拟返回数据
        """
        # 设置username
        self.beatmap.id2name = {"LittleStone": "123456"}
        self.beatmap.get_user_id("LittleStone")
        self.assertIsNotNone(self.beatmap.id2name, "用户ID获取失败")

        # 构造返回数据
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {
                "beatmap": {
                    "id": 123456,
                    "difficulty_rating": 5.25,
                    "url": "https://osu.ppy.sh/beatmapsets/123456#osu/654321"
                },
                "beatmapset": {
                    "title_unicode": "示例歌曲",
                    "artist_unicode": "示例艺术家"
                },
                "accuracy": 0.98,
                "max_combo": 1000,
                "statistics": {
                    "count_300": 950,
                    "count_100": 30,
                    "count_50": 10,
                    "count_miss": 5
                },
                "pp": 250.75,
                "rank": "S",
                "mods": ["HD", "HR"]
            }
        ]
        mock_get.return_value = mock_response

        self.beatmap.get_recent_info("LittleStone")

        self.assertEqual(self.beatmap.pr_beatmap_id, 123456)
        self.assertEqual(self.beatmap.pr_title, '示例歌曲')
        self.assertEqual(self.beatmap.pr_artist, '示例艺术家')
        self.assertEqual(self.beatmap.pr_star, 5.25)
        self.assertEqual(self.beatmap.pr_acc, 98)
        self.assertEqual(self.beatmap.pr_maxcombo, 1000)
        self.assertEqual(self.beatmap.pr_300, 950)
        self.assertEqual(self.beatmap.pr_100, 30)
        self.assertEqual(self.beatmap.pr_50, 10)
        self.assertEqual(self.beatmap.pr_miss, 5)
        self.assertEqual(self.beatmap.pr_pp, 250.75)
        self.assertEqual(self.beatmap.pr_rank, 'S')
        self.assertEqual(self.beatmap.pr_mods, 'HDHR')
        self.assertEqual(self.beatmap.pr_beatmap_url, 'https://osu.ppy.sh/beatmapsets/123456#osu/654321')
        self.assertEqual(self.beatmap.pr_username, 'LittleStone')

    @patch('sys.stdout', new_callable=StringIO)
    def test_get_recent_info_with_wrong_username(self, fake_out):
        """
        发送错误的username查询最近成绩
        """
        # 构造mock数据
        mock_post = MagicMock()
        mock_post.raise_for_status = MagicMock()
        mock_post.json.return_value = {'access_token': 'test_token'}
        with patch('irc_dlient.requests.post', return_value=mock_post):
            self.beatmap.get_token()
            self.assertEqual(self.beatmap.osu_token, 'test_token')

        # 设置 username
        self.beatmap.id2name = {"LittleStone": "123456"}

        # 设置beatmap id
        self.beatmap.beatmap_id = '75'

        # 调用获取最近成绩的方法
        self.beatmap.get_recent_info("ATRI1024")
        self.assertIn(
            "获取最近成绩失败，错误信息：'ATRI1024'\n| [ 获取最近成绩失败 - ]| *|  [  ] 0pp acc:0% combo:0x| 0/0/0/0|\n",
            fake_out.getvalue(),
            "Output does not contain expected failure message."
        )

class TestPP(unittest.TestCase):
    def setUp(self):
        self.beatmap = irc_dlient.rosu.Beatmap(path='./tests/75.osu')

    @patch('irc_dlient.os.path.exists')
    @patch('irc_dlient.requests.get')
    def test_get_beatmap_file_exists(self, mock_get, mock_exists):
        mock_exists.return_value = True
        pp = irc_dlient.PP()
        pp.get_beatmap_file('12345')
        mock_get.assert_not_called()

    @patch('irc_dlient.os.path.exists')
    @patch('irc_dlient.requests.get')
    def test_get_beatmap_file_download(self, mock_get, mock_exists):
        mock_exists.return_value = False
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'osu file content'
        mock_get.return_value = mock_response

        pp = irc_dlient.PP()
        pp.get_beatmap_file('12345')

        mock_get.assert_called_with('https://osu.ppy.sh/osu/12345')
        # 可以进一步检查文件写入，但需要更多的patching

    @patch('irc_dlient.rosu.Beatmap')
    def test_calculate_pp_fully_success(self,mock_beatmap):
        mock_beatmap.return_value = self.beatmap

        pp = irc_dlient.PP()
        pp.calculate_pp_fully('HDHRDT')
        self.assertEqual(pp.maxpp, 1100)
        self.assertEqual(pp.maxbeatmapcombo, 3581)
        self.assertEqual(pp.fc95pp, 656)
        self.assertEqual(pp.fc96pp, 698)
        self.assertEqual(pp.fc97pp, 751)
        self.assertEqual(pp.fc98pp, 824)
        self.assertEqual(pp.fc99pp, 931)
        self.assertEqual(pp.stars, 7.79)
        self.assertEqual(pp.afterar, 11.0)
        self.assertEqual(pp.aftercs, 4.9)
        self.assertEqual(pp.afterod, 11.1)
        self.assertEqual(pp.afterhp, 7.0)

    def test_calculate_pp_fully_failed(self):
        pp = irc_dlient.PP()
        pp.calculate_pp_fully('HDHRDT')
        self.assertEqual(pp.maxpp, 0)
        self.assertEqual(pp.maxbeatmapcombo, 0)
        self.assertEqual(pp.fc95pp, 0)

    @patch('irc_dlient.rosu.Beatmap')
    def test_calculate_pp_obj_success(self,mock_beatmap):
        mock_beatmap.return_value = self.beatmap

        pp = irc_dlient.PP()
        pp.calculate_pp_obj('HDHRDT', 0.98, 5, 1000)
        self.assertEqual(pp.maxpp, 1100)
        self.assertEqual(pp.maxbeatmapcombo, 3581)
        self.assertEqual(pp.fc95pp, 656)
        self.assertEqual(pp.fc96pp, 698)
        self.assertEqual(pp.fc97pp, 751)
        self.assertEqual(pp.fc98pp, 824)
        self.assertEqual(pp.fc99pp, 931)
        self.assertEqual(pp.currpp, 24)
        self.assertEqual(pp.curraimpp, 21)
        self.assertEqual(pp.currspeedpp, 0)
        self.assertEqual(pp.curraccpp, 0)

    def test_calculate_pp_obj_failed(self):
        pp = irc_dlient.PP()
        pp.calculate_pp_obj('HDHRDT', 0.98, 5, 1000)
        self.assertEqual(pp.maxpp, 0)
        self.assertEqual(pp.maxbeatmapcombo, 0)
        self.assertEqual(pp.currpp, 0)
        self.assertEqual(pp.curraimpp, 0)

class TestRoom(unittest.TestCase):
    def setUp(self):
        # 构造模拟config
        self.mock_config = MagicMock()
        self.mock_config.osuclientid = 'test_client_id'
        self.mock_config.osuclientsecret = 'test_client_secret'
        self.mock_config.timelimit = '100'  # Example value
        self.mock_config.starlimit = '5.0'
        self.mock_config.mpname = 'TestMP'
        self.mock_config.mppassword = 'testpassword'

        # 实例化Room
        self.room = irc_dlient.Room(self.mock_config)

    @patch('builtins.open')
    def test_save_last_room_id(self, mock_open):
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        self.room.room_id = '#room123'
        self.room.save_last_room_id()

        mock_file.write.assert_called_with('#room123')

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_last_room_id_file_not_found(self, mock_open):
        last_id = self.room.get_last_room_id()
        self.assertEqual(last_id, '')

if __name__ == '__main__':
    unittest.main()