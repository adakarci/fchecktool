#-*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.insert(0, 'libs')
from google.appengine.ext import ndb
import webapp2
import httplib2
import oauth2 as oauth
import json
import main
from google.appengine.api import mail


consumer_key = 'HqbjPiR0KvDwdBEtKp0ENm0P5'
consumer_secret = '5LN9szWMU5ZgdmiGP0BOEKOkTfuFC4SGq0CZEBlLbKFdpz0HV4'
access_token = '998866135-Y9KOUiUmPjQv80BCyC79BWL50EwAmClh1kqh6456'
access_secret = 'rdINa5GokDOxiGuCgpCh4olS7hh6ebNnJejc0fDGV8T1J'


consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)
token = oauth.Token(key=access_token, secret=access_secret)
client = oauth.Client(consumer, token)


class CheckUnFollowers(webapp2.RequestHandler):
    def get(self):
        userlist = [user for user in main.User.query().fetch()]
        for user in userlist:
            header, response = client.request(
                'https://api.twitter.com/1.1/followers/ids.json?cursor='
                '-1&screen_name='+user.username+'&count=5000')
            new_followers_id = [str(id) for id in json.loads(response)["ids"]]
            old_followers_id = user.follower_list
            if list(set(old_followers_id)-set(new_followers_id)):
                for id in list(set(old_followers_id)-set(new_followers_id)):
                    header, response = client.request(
                        'https://api.twitter.com/1.1/users/lookup.'
                            'json?user_id='+id+'')
                    username = json.loads(response)[0]["screen_name"]
                    body = "@{} unfollowed you".format(username)
                    sender = "tooltwitter@gmail.com"
                    subject = "Unfollow var"
                    to = user.email
                    mail.send_mail(sender, to, subject, body)

            save_user = main.User.query(
                main.User.username == user.username).fetch(1)
            save_user[0].follower_list = new_followers_id
            save_user[0].put()
