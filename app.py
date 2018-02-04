'''
#Original code and tutorial: https://pythontips.com/2017/04/13/making-a-reddit-facebook-messenger-bot/

# Build a FB chat bot that can answer simple queries 
# Change logs:
- Refactoring code
- Add new query keywords
- Add new feature: get next episode info
'''



from flask import Flask, request
import json
import requests
from flask_sqlalchemy import SQLAlchemy
import os
import praw
import myLib
import sys

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
#using client Id and key from Reddit App
reddit = praw.Reddit(client_id='yourClientId', client_secret='yourClientSecret', user_agent='yourUserAgent')

# This needs to be filled with the Page Access Token that will be provided
# by the Facebook App that will be created.
PAT = 'yourPAT'

quick_replies_list = [{
    "content_type": "text",
    "title": "Meme",
    "payload": "meme",
},
    {
        "content_type": "text",
        "title": "Motivation",
        "payload": "motivation",
    },
    {
        "content_type": "text",
        "title": "Comics",
        "payload": "comics",
    },
    {
        "content_type": "text",
        "title": "LifeProTips",
        "payload": "LifeProTips",
    },
    # {
    #     "content_type": "text",
    #     "title": "Shower Thought",
    #     "payload": "Shower_Thought",
    # },
    {
        "content_type": "text",
        "title": "Quotes",
        "payload": "Quotes",
    },
    {
        "content_type": "text",
        "title": "News",
        "payload": "worldnews",
    },
    {
        "content_type": "text",
        "title": "Jokes",
        "payload": "Jokes",
    }
]


@app.route('/', methods=['GET'])
def handle_verification():
    print "Handling Verification."
    if request.args.get('hub.verify_token', '') == 'my_voice_is_my_password_verify_me':
        print "Verification successful!"
        return request.args.get('hub.challenge', '')
    else:
        print "Verification failed!"
        return 'Error, wrong validation token'


@app.route('/', methods=['POST'])
def handle_messages():
    print "Handling Messages"
    payload = request.get_data()
    print payload
    for sender, message in messaging_events(payload):
        print "Incoming from %s: %s" % (sender, message)
        send_message(PAT, sender, message)
    return "ok"


def messaging_events(payload):
    """Generate tuples of (sender_id, message_text) from the
    provided payload.
    """
    data = json.loads(payload)
    messaging_events = data["entry"][0]["messaging"]
    for event in messaging_events:
        if "message" in event and "text" in event["message"]:
            yield event["sender"]["id"], event["message"]["text"].encode('unicode_escape')
        else:
            yield event["sender"]["id"], "I can't echo this"


def send_message(token, recipient, text):
    """Send the message text to recipient with id recipient.
    """
    try:
        text = text.rstrip(' \t\r\n\0')
        print "message received: %s" %text
        if "show:" in text.lower():
            showName = text.split(":")[-1]
            print showName
            nextEpisodeInfo = myLib.get_next_episode(showName)
            r = post_requests("Next Episode", recipient, token)
            r = post_requests(nextEpisodeInfo, recipient, token)
        else: #reddit sources
            subreddit_name = get_subreddit_name(text)
            myUser = get_or_create(db.session, Users, name=recipient)
            if subreddit_name in ["Showerthoughts" , "Quotes", "LifeProTips"]:
                submission = get_submission(myUser, subreddit_name)
                r = post_requests(submission.title, recipient, token)
            elif subreddit_name in ["worldnews"]:
                submission = get_submission(myUser, subreddit_name)
                r = post_requests(submission.title, recipient, token)
                r = post_requests(submission.url, recipient, token)

            elif subreddit_name == "Jokes":
                submission = get_submission_no_flair_text(myUser, subreddit_name)
                payload = submission.title
                payload_text = submission.selftext
                r = post_requests(payload, recipient, token)
                r = post_requests(payload_text, recipient, token)
            else:
                submission = get_submission_with_image(myUser, subreddit_name)
                r = post_requests_with_attachment(submission.url, recipient, token)

        if r.status_code != requests.codes.ok:
            print r.text
    except:
        print "Unexpected error:", sys.exc_info()[0]
        raise
        exit(1)


def get_submission_with_image(myUser, subreddit_name):
    for submission in reddit.subreddit(subreddit_name).hot(limit=None):
        if (submission.link_flair_css_class == 'image') or (
                    (submission.is_self != True) and ((".jpg" in submission.url) or (".png" in submission.url))):
            query_result = Posts.query.filter(Posts.name == submission.id).first()
            if query_result is None:
                myPost = Posts(submission.id, submission.url)
                append_query_result(myUser, myPost)
                break
            elif myUser not in query_result.users:
                append_query_result(myUser, query_result)
                break
            else:
                continue
    return submission


def get_submission_no_flair_text(myUser, subreddit_name):
    for submission in reddit.subreddit(subreddit_name).hot(limit=None):
        if ((submission.is_self == True) and (submission.link_flair_text is None)):
            query_result = Posts.query.filter(Posts.name == submission.id).first()
            if query_result is None:
                append_submission(myUser, submission)
                break
            elif myUser not in query_result.users:
                append_query_result(myUser, query_result)
                break
            else:
                continue
    return submission


def get_subreddit_name(text):
    subreddit_name = "GetMotivated"
    if "meme" in text.lower():
        subreddit_name = "memes"
    elif "shower" in text.lower():
        subreddit_name = "Showerthoughts"
    elif "joke" in text.lower():
        subreddit_name = "Jokes"
    elif "quote" in text.lower():
        subreddit_name = "Quotes"
    elif "lifeprotip" in text.lower():
        subreddit_name = "LifeProTips"
    elif "news" in text.lower():
        subreddit_name = "worldnews"
    elif "comic" in text.lower():
        subreddit_name = "Comics"

    return subreddit_name


def get_submission(myUser, subreddit_name):
    for submission in reddit.subreddit(subreddit_name).hot(limit=None):
        if (submission.is_self == True):
            query_result = Posts.query.filter(Posts.name == submission.id).first()
            if query_result is None:
                append_submission(myUser, submission)
                break
            elif myUser not in query_result.users:
                append_query_result(myUser, query_result)
                break
            else:
                continue
    return submission


def append_query_result(myUser, query_result):
    myUser.posts.append(query_result)
    db.session.commit()


def append_submission(myUser, submission):
    myPost = Posts(submission.id, submission.title)
    append_query_result(myUser, myPost)



def post_requests_with_attachment(payload, recipient, token):
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": token},
                      data=json.dumps({
                          "recipient": {"id": recipient},
                          "message": {"attachment": {
                              "type": "image",
                              "payload": {
                                  "url": payload
                              }},
                              "quick_replies": quick_replies_list}
                      }),
                      headers={'Content-type': 'application/json'})
    return r

def post_requests(payload, recipient, token):
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": token},
                      data=json.dumps({
                          "recipient": {"id": recipient},
                          "message": {"text": payload,
                                      "quick_replies": quick_replies_list}
                      }),
                      headers={'Content-type': 'application/json'})
    return r



def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance


relationship_table = db.Table('relationship_table',
                              db.Column('user_id', db.Integer, db.ForeignKey('users.id'), nullable=False),
                              db.Column('post_id', db.Integer, db.ForeignKey('posts.id'), nullable=False),
                              db.PrimaryKeyConstraint('user_id', 'post_id'))


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    posts = db.relationship('Posts', secondary=relationship_table, backref='users')

    def __init__(self, name=None):
        self.name = name


class Posts(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    url = db.Column(db.String, nullable=False)

    def __init__(self, name=None, url=None):
        self.name = name
        self.url = url


if __name__ == '__main__':
    app.run()