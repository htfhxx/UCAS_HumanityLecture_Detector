# -*- coding: utf-8 -*-
import codecs
import json
import os
import time
from sys import exit
import requests
import re
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import yaml
       
class UserNameOrPasswordError(Exception):
    pass

class MailSender:

    def __init__(self, mail_user, mail_pass, destination_list, mail_host="smtp.qq.com"):

        self.mail_host = mail_host
        self.mail_user = mail_user
        self.mail_pass = mail_pass
        self.destination_list = destination_list

        if self.mail_user not in self.destination_list:
            self.destination_list.append(self.mail_user)
        self.getConnect()
    
    def getConnect(self):
        try:
            # self.smtpObj = smtplib.SMTP_SSL() 
            # self.smtpObj.connect(self.mail_host, 465)
            self.smtpObj = smtplib.SMTP() 
            self.smtpObj.connect(self.mail_host, 25)
            self.smtpObj.login(self.mail_user,self.mail_pass)
        except Exception:
            print("无法登录邮箱, 请检查用户名或密码是否正确")
            exit(1)
            

    def content(self, passage):
        message = MIMEText(passage, 'plain', 'utf-8')
        message['From'] = Header("人文讲座提醒", "utf-8")
        message['To'] =  Header("人文讲座", 'utf-8')
        subject = '人文讲座提醒'
        message['Subject'] = Header(subject, 'utf-8')
        return message
        

    def send(self, passage):
        for mail in self.destination_list:
            message = self.content(passage)
            try:
                self.smtpObj.sendmail(self.mail_user, mail, message.as_string())
                print ("成功发送至 ", mail)
            except smtplib.SMTPException:
                print ("无法发送邮件至 ", mail)


class LoginUCAS(object):

    def __init__(self, config):
        self.config = config
        self.session = requests.session()
        
        self.cnt = 0
        self.old_list = []
        self.mail_sender = MailSender(config["main_mail"], config["main_pwd"], config["otherMails"])

        self.url = {
            'base_url': 'http://onestop.ucas.ac.cn/home/index',
            'verification_code': None,
            'login_url': 'http://onestop.ucas.ac.cn/Ajax/Login/0'
        }
        # self.session.get(self.url['base_url'])
        self.headers = {
            'Host': 'onestop.ucas.ac.cn',
            "Connection": "keep-alive",
            'Referer': 'http://onestop.ucas.ac.cn/home/index',
            'X-Requested-With': 'XMLHttpRequest',
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/52.0.2743.116 Safari/537.36",
        }
        self.post_data = {
            "username": self.config["username"],
            "password": self.config["password"],
            "remember": 'checked',
        }

    def parser(self):
        url = 'http://jwxk.ucas.ac.cn/subject/humanityLecture'

        r = self.session.get(url, headers=self.headers)
        course_list = set(re.findall(r"<a href=\"/subject/([0-9]*)/humanityView\" target=\"_blank\"\>查看详情</a>", r.text))
        while len(course_list)==0:
            print("用户在其它地方登录, 正在重新登录...")
            self.login_jwxk()
            r = self.session.get(url, headers=self.headers)
            course_list = set(re.findall(r"<a href=\"/subject/([0-9]*)/humanityView\" target=\"_blank\"\>查看详情</a>", r.text))
        return course_list


    def check(self):
        count = 0
        while True:
            count += 1
            print("\n%d 次刷新..."%count)
            try:
                result = self.parser()
                print("当前讲座数 %d, 上一轮讲座数 %d "%(len(result), len(self.old_list)))
                if len(result) > len(self.old_list):
                    new_courses = result - self.old_list
                    print("New %d Courses!"%(len(new_courses)))
                    self.mail_sender = MailSender(self.config["main_mail"], self.config["main_pwd"], self.config["otherMails"])
                    self.mail_sender.send("已发布%d门新讲座!"%(len(new_courses)))
                    self.old_list = result
                    if self.config["autoChoose"]:
                        self.sign(new_courses)
                time.sleep(self.config["interval"])
            
            except requests.exceptions.ConnectionError:
                self.cnt += 1
                if self.cnt > 20:
                    print("教务处好像登不上, 5分钟后重新尝试连接...")
                    time.sleep(300)
                    self.cnt = 0
                return self.login_sep()

        
    def sign(self, new_courses):
        for info in new_courses:
            data = {
                "lectureId": info[0],
                "communicationAddress": info[1]
            }
            r = self.session.post("http://jwxk.ucas.ac.cn/subject/toSign", data=data, headers=self.headers)
            if r.text == "success":
                print("讲座报名成功!")
            else:
                print("讲座报名失败!")

    def login_jwxk(self):
        url = "http://sep.ucas.ac.cn/portal/site/226/821"
        r = self.session.get(url, headers=self.headers)
        try:
            code = re.findall(r'"http://jwxk.ucas.ac.cn/login\?Identity=(.*)"', r.text)[0]
        except IndexError:
            raise NoLoginError
        url = "http://jwxk.ucas.ac.cn/login?Identity=" + code
        self.headers['Host'] = "jwxk.ucas.ac.cn"
        self.session.get(url, headers=self.headers)
        self.old_list = self.parser()


    def login_sep(self):
        try:
            if not self.cnt:
                print('Login....' + self.url['base_url'])
            html = self.session.post(
                self.url['login_url'], data=self.post_data, headers=self.headers).text
            
            res = json.loads(html)

            if not res['f']:
                raise UserNameOrPasswordError
            else:
                html = self.session.get(res['msg']).text
                print("登录成功")
            
            self.login_jwxk()
            print("当前讲座数: %d"%(len(self.old_list)))
            self.cnt = 0
        except UserNameOrPasswordError:
            print('用户名或者密码错误')
            exit(1)
        except requests.exceptions.ConnectionError:
            self.cnt += 1
            if self.cnt > 20:
                print("教务处好像登不上, 5分钟后重新尝试连接...")
                time.sleep(300)
                self.cnt = 0
            return self.login_sep()
        return self


if __name__ == '__main__':

    with open("config", "r", encoding="utf8") as f:
        config = yaml.load(f.read())
    test = LoginUCAS(config)
    test.login_sep()
    test.check()