# UCAS_HumanityLecture_Detector
国科大人文讲座监测及自动报名脚本

## 环境依赖

python 3.6

```sh
pip install -r requirements.txt
```


## 使用
修改配置文件 `config`, 格式如下
```yaml
# sep账号
username: xiaoming@163.com
# sep密码
password: mimamima

# 是否自动报名
autoChoose: False

# 查询间隔，单位 秒
interval: 180

# QQ邮箱及其授权码（QQ邮箱-账户-获取授权码）, 注意不是密码
main_mail: 1111111@qq.com
main_pwd: asdsadwqeqweqwee

# 需要提醒的邮箱, 按对应格式继续添加即可
otherMails:
    - 1111111@qq.com
    - 2222222@gmail.com
```
运行程序
```python
python main.py
```

## 问题

Q: Linux运行程序时smtp超时无法连接?
A: 修改`main.py` 32-33行:
```python
    self.smtpObj = smtplib.SMTP_SSL() 
    self.smtpObj.connect(self.mail_host, 465)
```
