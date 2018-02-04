import praw
import re

from tvmaze.api import Api
api = Api()

reddit = praw.Reddit(client_id='yourCliendId', client_secret='yourClientSecret', user_agent='yourUserAgent')


def redditTest(subreddit_name):


    for submission in reddit.subreddit(subreddit_name).hot(limit=None):
        if ((submission.is_self == True) and (submission.link_flair_text is None)):
            print submission.title
            break



    print "Test"


#get next episode for a series
def get_next_episode(showName):
    output = ''
    try:
        show =  api.search.single_show(showName)
        #show id = 66
        if show and show._links.get('nextepisode'):
            nextEpisodeLink = show._links['nextepisode']['href'] #  u'http://api.tvmaze.com/episodes/1297342'
            episodeId = nextEpisodeLink.split('/')[-1]         #1297342
            episode = api.episode.get(episodeId)
            if episode:
                output += "%s S%s E%s : %s \n" %(show.name, episode.season, episode.number, episode.name)
                output += "Air date: %s %s \n" %(episode.airdate, episode.airtime)
                output += re.sub('<[^<]+?>', '', episode.summary)
        else:
            output = "Not found :( :("
    except Exception as e:
        print e
    finally:
        return output



if __name__ == '__main__':
    # redditTest("Quotes")
    # redditTest("LifeProTips")
    # redditTest("worldnews")
    redditTest("comics")
    # print get_next_episode("Big Bang Theory")
    # print get_next_episode("Arrow")
    # print get_next_episode("The Flash")
    # print get_next_episode("SuperGirl")
    # print get_next_episode("Super Girl")