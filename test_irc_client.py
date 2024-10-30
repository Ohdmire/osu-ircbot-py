import unittest
from unittest.mock import patch, MagicMock
import irc_dlient

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
        # 从 config.ini 中读取 client_id 和 client_secret
        config = irc_dlient.Config()
        self.client_id = config.osuclientid
        self.client_secret = config.osuclientsecret

        # 实例化 Beatmap 对象并设置 client_id 和 client_secret
        self.beatmap = irc_dlient.Beatmap(self.client_id, self.client_secret)

    @patch('irc_dlient.requests.post')
    def test_get_token_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {'access_token': 'test_token'}
        mock_post.return_value = mock_response

        self.beatmap.get_token()

        self.assertEqual(self.beatmap.osu_token, 'test_token')

    def test_get_beatmap_info_success(self):
        """
        这个测试用例将发送真实的 HTTP 请求到 osu! API
        并验证返回的真实响应是否符合预期。
        """
        # 获取 Token
        self.beatmap.get_token()
        self.assertIsNotNone(self.beatmap.osu_token, "Token 获取失败")

        # 设置 beatmap_id
        self.beatmap.beatmap_id = '75'  # osu第一个ranked图

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

class TestPP(unittest.TestCase):
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

class TestRoom(unittest.TestCase):
    @patch('builtins.open')
    def test_save_last_room_id(self, mock_open):
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        room = irc_dlient.Room()
        room.room_id = '#room123'
        room.save_last_room_id()

        mock_file.write.assert_called_with('#room123')

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_get_last_room_id_file_not_found(self, mock_open):
        room = irc_dlient.Room()
        last_id = room.get_last_room_id()
        self.assertEqual(last_id, '')

if __name__ == '__main__':
    unittest.main()