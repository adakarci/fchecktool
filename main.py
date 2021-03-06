#-*- coding:utf-8 -*-
import sys
reload(sys)
sys.setdefaultencoding('utf-8')
sys.path.insert(0, 'libs')
from google.appengine.ext import ndb
import jinja2
import webapp2
import oauth2 as oauth
import json
from cron import CheckUnFollowers
import re

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader("templates"), autoescape=True)

consumer_key = ''
consumer_secret = ''
access_token = ''
access_secret = ''


consumer = oauth.Consumer(key=consumer_key, secret=consumer_secret)
token = oauth.Token(key=access_token, secret=access_secret)
client = oauth.Client(consumer, token)


class User(ndb.Model):
    username = ndb.StringProperty()
    created_date = ndb.DateTimeProperty(auto_now=True)
    follower_list = ndb.StringProperty(repeated=True)
    email = ndb.StringProperty()


class Search(webapp2.RequestHandler):

    def post(self):
        context = {}
        username = self.request.get("username")
        compiled = re.compile(r'^[A-Za-z0-9_-]{3,15}$')
        if not compiled.search(username):
            context["message"] = "You dont exist :)"
        else:   # I get user info
            header, response = client.request(
                'https://api.twitter.com/1.1/statuses/user_timeline'
                '.json?include_entities=true&screen_name='+username+'&count=1')
            try:
                info = json.loads(response)[0]
                name = info["user"]["name"]
                image = info["user"]["profile_image_url"]
                max_id = info["id"]
                count = 0
                list_tweets = []
                while count < 18:
                    header, response = client.request(
                        'https://api.twitter.com/1.1'
                        '/statuses/user_timeline.json?'
                        'include_entities=true&include_rts=false&screen_name='
                        ''+username+'&max_id='+str(max_id)+'&count=200')

                    data = json.loads(response)
                    list_tweets.extend(data)
                    # I must find max_id so I can get all tweets
                    max_id = data[len(data)-1]["id"]
                    count += 1
                # I seperate text, image part from data I get from twitter.
                tweets = map(lambda x: x["text"], list_tweets[::-1])
                context["data"] = tweets
                context["name"] = name
                context["image"] = image
            except KeyError:
                context["message"] = "You dont exist :)"

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(context))


class AddUSer(webapp2.RequestHandler):

    def post(self):
        import re
        username = self.request.get("username")
        email = self.request.get("email")
        messages = []
        compiled = re.compile(r'^[A-Za-z0-9_-]{3,15}$')
        compile_email = re.compile(
            r"^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$")
        if not compiled.search(username):
            messages.append("You dont exist :)")
        elif not compile_email.search(email):
            messages.append("Gecerli mail adresi giriniz")
        else:
            header, response = client.request(
                'https://api.twitter.com/1.1/followers/ids.json?cursor='
                '-1&screen_name='+username+'&count=5000')
            try:
                # I get ids_list of user's followers.
                ids = [str(id) for id in json.loads(response)["ids"]]
                # I check if user is saved before.
                # There is a better way of course to check but I want to sleep.
                userlist = [user.username for user in User.query().fetch(
                            projection=["username"])]
                if username not in userlist:
                    user = User()
                    user.username = username
                    user.email = email
                    user.follower_list = ids
                    key = user.put()  # I saved user.
                    messages.append("@"+username+" "+"Ok we added you")
                    messages.append("Your followers:"+str(len(ids)))
                else:
                    # if user was saved before I compare old and current list.
                    followerlist = [
                        user.follower_list[0] for user in User.query().filter(
                            User.username == username).fetch(
                                projection=["follower_list"])]
                    # if there is no difference between two list
                    if len(set(followerlist)-set(ids)) == 0:
                        messages.append("No one has unfollowed you :)")
                    # if there is a difference between old and current
                    #I find out who unfollwed.
                    else:
                        for id in set(followerlist)-set(ids):
                            header, response = client.request(
                                'https://api.twitter.com/1.1/users/lookup.'
                                'json?user_id='+id+'')
                            username = json.loads(response)[0]["screen_name"]
                            msg = "{} unfollowed you".format(username)
                            messages.append(msg)
                    # I save current list again.
                    user = User.query(
                        User.username == username).get(keys_only=True).get()
                    user.follower_list = ids
                    user.put()
                    messages.append("We updated your followerlist")
                    messages.append(
                        "Old Followers:"+str(len(followerlist))+"\
                        "+"New Followers:"+str(len(ids))+"")
            except KeyError:
                messages.append("You dont exist :)")

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render({"messages": messages}))


class MainPage(webapp2.RequestHandler):

    def get(self):

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render({}))

application = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/search', Search),
    ('/add', AddUSer),
    ('/check', CheckUnFollowers),
], debug=True)
