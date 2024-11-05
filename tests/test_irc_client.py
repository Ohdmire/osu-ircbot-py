import unittest
import requests
from unittest.mock import patch, MagicMock
from io import StringIO
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