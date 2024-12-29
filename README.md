# osu-ircbot-py
基于python使用irc自动轮换房主的osu机器人

[![codecov](https://codecov.io/github/Ohdmire/osu-ircbot-py/graph/badge.svg?token=HZZ0PPME7L)](https://codecov.io/github/Ohdmire/osu-ircbot-py)

# 文档
输入help获取吧 咕咕咕

# 教程
创建python虚拟环境
```bash
python3 -m venv .venv
```

切换到python的环境(windows)
```bat
.\.venv\Scripts\activate
```

安装Python和必要运行库
```bash
pip install -r requirements.txt
```
运行程序
```bash
python3 irc_dlient.py
```
执行单元测试
```bash
pip install coverage
coverage run -m unittest discover -s tests -v
coverage report -m
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
starlimit = 0
timelimit = 0
mpname = 你的mp房名字
mppassword = 你的mp房密码

[PREDICT]
url = http://localhost:7777/predict
```

- starlimit 是超星限制0默认无限制
- timelimit 是谱面长度限制0默认无限制 单位s
- url = 是预测模型地址(可选)