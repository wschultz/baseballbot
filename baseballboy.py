#!/usr/bin/env python

import private.credentials

from apscheduler.schedulers.background import BackgroundScheduler
import datetime
import json
import logging
import os
import pytz 
import time
import tweepy
import urllib


""" This is the recommended code to use tweepy """
class TwitterAPI:
  def __init__(self):
    consumer_key        = private.credentials.consumer_key
    consumer_secret     = private.credentials.consumer_secret
    auth                = tweepy.OAuthHandler(consumer_key, consumer_secret)
    access_token        = private.credentials.access_token
    access_token_secret = private.credentials.access_token_secret
    auth.set_access_token(access_token, access_token_secret)
    self.api            = tweepy.API(auth)

  def tweet(self, message):
    self.api.update_status(status=message)

twitter = TwitterAPI()


""" These are the only variables that need to be changed.
    May turn this into args later. """
team         = 'sf'          # This is what mlb uses, we key off of this
team_hashtag = "#SFGiants"   # This is the team #hashtag
timezone     = "US/Pacific"  # This is the local timezone of the host machine
last_day     = "2016-10-02"  # This is the last day of baseball. #SadPanda



""" We'll log our tweets. """
logging.basicConfig(filename='baseball.log',level=logging.DEBUG,format='%(asctime)s %(message)s')


""" This is the process of grabbing the json for a specific team """
def get_fresh_data(team):
  """ This section grabs json data from mlbam """

  """ Create the URL for today """
  now = datetime.datetime.now()
  url = "http://gd2.mlb.com/gdcross/components/game/mlb/year_" + '{}'.format(now.year) + "/month_" + '{:02d}'.format(now.month) + "/day_" + '{:02d}'.format(now.day) + "/miniscoreboard.json"

  """ Grab the first response and write it to a file, we'll update it once the game starts """
  data_write_file = '{}'.format(now.year) + '{:02d}'.format(now.month) + '{:02d}'.format(now.day) + ".json"

  """ Get the json data if the file doesn't exist, or if it's over three minutes old """
  if not os.path.isfile(data_write_file) or time.time() - os.path.getmtime(data_write_file) > 180:
    response  = urllib.urlopen(url)
    full_data = json.loads(response.read())
    with open(data_write_file, 'w') as outfile:
      json.dump(full_data, outfile, sort_keys=True, indent=2, ensure_ascii=False)

  """ Use the data from the status file """
  with open(data_write_file, 'r') as json_data:
    full_data = json.load(json_data)

  """ This will return false if there is no game today, else will return json data for just our team """
  my_game  = False
  for game in full_data['data']['games']['game']:
    if team in game['home_file_code'] or team in game['away_file_code']:
      my_game = game
  
  return my_game




""" 
    These 3 def's should be combined into a single function that loops 
    starting at 8am and finishes once there's a final score
"""


def do_the_things():
  returned_no_game    = False
  returned_game_time  = False
  returned_game_final = False
  returned_game_soon  = False
  """
     'sched' starts this up at 8am, then it continually runs until either it returns the final
      statements of 'there is no game today' or 'the game is over'
  """
  while not (returned_no_game or returned_game_final):
    game_data = get_fresh_data(team)

    """ The default TZ for mlb is US/Eastern, we'll do some things and make it local TZ """
    tz = pytz.timezone('US/Eastern')
    eastern_time = datetime.datetime.strptime("%s %s" % (game_data['time_date'], game_data['ampm']), '%Y/%m/%d %I:%M %p')
    eastern_time = tz.localize(eastern_time)
    pacific_time = eastern_time.astimezone(pytz.timezone(timezone))

    opponent, our_score, their_score, venue = set_vars(game_data)

    if not game_data and not returned_no_game:
      returned_no_game = True
      #twitter.tweet("The %s don't have a game scheduled today. Rest well guys!" % team_hashtag)
      print("The %s don't have a game scheduled today. Rest well guys!" % team_hashtag)

    if game_data and not returned_game_time:
      returned_game_time = True
      #twitter.tweet(("The %s are playing against the %s today, first pitch is at " + pacific_time.strftime("%-I:%M%p %Z") + " at %s") % (team_hashtag, opponent, venue))
      print(("The %s are playing against the %s today, first pitch is at " + pacific_time.strftime("%-I:%M%p %Z") + " at %s") % (team_hashtag, opponent, venue))

    if "Warmup" in game_data["status"] and not returned_game_soon:
      returned_game_soon = True
      #twitter.tweet(("The %s are playing against the %s in a moment, first pitch is at " + pacific_time.strftime("%-I:%M%p %Z") + " at %s") % (team_hashtag, opponent, venue))
      print(("The %s are playing against the %s in a moment, first pitch is at " + pacific_time.strftime("%-I:%M%p %Z") + " at %s") % (team_hashtag, opponent, venue))

    if "In Progress" in game_data["status"]:
      if int(our_score) > int(their_score):
        print("The %s are winning against the %s, the score is currently %s-%s" % (team_hashtag, opponent, our_score, their_score))
        #twitter.tweet("The %s are winning against the %s, the score is currently %s-%s" % (team_hashtag, opponent, our_score, their_score))
      elif int(our_score) < int(their_score):
        print("The %s are losing against the %s, the score is currently %s-%s" % (team_hashtag, opponent, our_score, their_score))
        #twitter.tweet("The %s are losing against the %s, the score is currently %s-%s" % (team_hashtag, opponent, our_score, their_score))
      elif int(our_score) == int(their_score):
        print("The %s are tied with the %s, the score is currently %s-%s" % (team_hashtag, opponent, our_score, their_score))
        #twitter.tweet("The %s are tied with the %s, the score is currently %s-%s" % (team_hashtag, opponent, our_score, their_score))

    if "Final" in game_data["status"]:
      returned_game_final = True
      if our_score > their_score:
        print("The %s beat the %s today at %s with a score of %s-%s" % (team_hashtag, opponent, venue, our_score, their_score))
        #twitter.tweet("The %s beat the %s today at %s with a score of %s-%s" % (team_hashtag, opponent, venue, our_score, their_score))
      else:
        print("The %s lost against the %s today at %s with a score of %s-%s. Get 'em tomorrow!" % (team_hashtag, opponent, venue, our_score, their_score))
        #twitter.tweet("The %s lost against the %s today at %s with a score of %s-%s. Get 'em tomorrow!" % (team_hashtag, opponent, venue, our_score, their_score))

    #print("reached the end of the loop")
    time.sleep(5)


""" Here we set some variables for later formatting """
def set_vars(game_data):
  if team in game_data['home_file_code']:
    we_are      = "home"
    they_are    = "away"
  else:
    we_are      = "away"
    they_are    = "home"

  try:
    our_score   = game_data[we_are   + "_team_runs"]
    their_score = game_data[they_are + "_team_runs"]
  except:
    our_score   = None
    their_score = None

  opponent      = game_data[they_are +'_team_name']
  venue         = game_data['venue']

  return opponent, our_score, their_score, venue


if __name__ == '__main__':
  print "Starting..."

  do_the_things()
  # These 4 lines are required
  sched = BackgroundScheduler()
  #sched.add_job(do_the_things, 'cron', hour=8, minute=0, end_date=last_day)
  #
  #sched.start()

  try:
    # This is here to simulate application activity (which keeps the main thread alive).
    while True:
        time.sleep(2)
  except (KeyboardInterrupt, SystemExit):
    # Not strictly necessary if daemonic mode is enabled but should be done if possible
    sched.shutdown()




