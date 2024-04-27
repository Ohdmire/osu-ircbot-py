# osu-ircbot-py
基于python使用irc自动轮换房主的osu机器人

# 文档
输入help获取吧 咕咕咕

# 教程
安装Python和必要运行库
```python
pip install -r requirements
```

运行程序
```bash
python3 irc_dlient.py
```


# 配置
请在根目录下创建`config.ini` 并填入以下内容 自行替换
```ini
[OSUAPI]
client_id = 你的osuapiv2 id
client_secret  = 你的osuapiv2 密钥
nickname = 你的osu名字
password = 你的irc密码

[OSU]
starlimit = 0 #超星限制0默认无限制
mpname = 你的mp房名字
mppassword = 你的mp房密码
```