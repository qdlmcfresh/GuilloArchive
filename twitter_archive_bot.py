# Archive the twitter account https://twitter.com/GuillotineTea 
# The Achive includes tweets, images, videos and gifs
# The archive is stored in a sqlite database, and the images and videos are stored in a directory

import tweepy
import os
import sqlite3
import urllib.request
import argparse


class TwitterArchiveBot:
    def __init__(self, twitter_id, bearer_token, db_file):
        self.id = twitter_id
        self.media_path = "./media"
        self.token = bearer_token
        self.db_file = db_file
        # if the database doesnt have the tables, create them
        create = False
        if not os.path.isfile(db_file):
            create = True
        self.conn = sqlite3.connect(db_file)
        self.db_cursor = self.conn.cursor()
        if(create):
            self.create_database()
        


    def create_database(self):
        
        print("Creating database file")
        c = self.db_cursor
        c.execute('''CREATE TABLE tweets
                        (tweet_id integer primary key, text text)''')
        # tweet_id is foreign key to tweets table
        c.execute('''CREATE TABLE media
                        (id integer primary key autoincrement, media_id text, tweet_id integer, media_url text, media_type text, FOREIGN KEY(tweet_id) REFERENCES tweets(tweet_id))''')
        self.conn.commit()

    
    def save_tweet(self, tweet, media_dict):
        # save the tweet to the database
        # save the media to the media directory with the media_id as the filename
        # if the media is a video, save the video
        # if the media is a gif, save the gif
        # if the media is an image, save the image
        c = self.db_cursor
        # save the tweet
        c.execute("INSERT INTO tweets VALUES (?,?)", (tweet.id, tweet.text))
        if tweet.attachments is not None:
            for media_key in tweet.attachments["media_keys"]:
                media = media_dict[media_key]
                url = media.url
                if media.type == "video":
                    url = media.variants[-1]["url"]
                c.execute("INSERT INTO media VALUES (NULL,?,?,?,?)", (media.media_key, tweet.id, url, media.type))
        self.conn.commit()

    def download_media(self):
        media = self.db_cursor.execute("SELECT * FROM media").fetchall()
        for file in media:
            key = file[1]
            url = file[3]
            media_type = file[4]

            if not os.path.isdir(self.media_path):
                os.mkdir(self.media_path)
            #   get all files in the media directory
            files = ''.join(os.listdir(self.media_path))
            if key in files:
                continue
            print(f"Downloading {url}")
            if media_type == "photo":
                # download the image
                print("Downloading image")
                urllib.request.urlretrieve(url, self.media_path + "/" + key + ".jpg")
            elif media_type == "video":
                # download the video
                print("Downloading video")
                urllib.request.urlretrieve(url, self.media_path + "/" + key + ".mp4")
            elif media_type == "animated_gif":
                # download the gif
                print("Downloading gif")
                urllib.request.urlretrieve(url, self.media_path + "/" + key + ".gif")


    def get_tweets(self, since_id=None):
        # get the tweets from the twitter account using tweepy
        client = tweepy.Client(bearer_token=self.token)
        for results in tweepy.Paginator(client.get_users_tweets, id=self.id, since_id=since_id,  exclude='replies,retweets',expansions='attachments.media_keys', media_fields='type,media_key,url,variants', max_results=100):
            #self.download_media(results.includes['media'])
            if(results.data is None):
                break
            print(f"Saving {len(results)} tweets")
            media_dict = {}
            for media in results.includes['media']:
                media_dict[media.media_key] = media
            for tweet in results.data:
                self.save_tweet(tweet, media_dict)
    
    def close(self):
        self.conn.close()
    
    
    def to_html(self):
        tweets = self.db_cursor.execute("SELECT * FROM tweets").fetchall()
        # convert the database to html
        post_footer = '''
        </div>
      </div>
      <!-- post ends -->
      '''
        html = '''
        <!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta http-equiv="X-UA-Compatible" content="IE=edge" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Guillo-Archiv</title>
    <link rel="stylesheet" href="styles.css" />
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet" />
    <link
      rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.3/css/all.min.css"
      integrity="sha512-iBBXm8fW90+nuLcSKlbmrPcLa0OT92xO1BIsZ+ywDWZCvqsWgccV3gFoRBv0z+8dLJgyAHIhR35VZc2oM/gI1w=="
      crossorigin="anonymous"
    />
  </head>
  
      <!-- feed starts -->
    <div class="feed">
      <div class="feed__header">
        <h2>Home</h2>
      </div>
        '''
        for tweet in tweets:
            post_header = f'''
              <!-- post starts -->
      <div class="post">
        <div class="post__avatar">
          <img
            src="https://pbs.twimg.com/profile_images/1356319145403494402/L2ZsJGIK_400x400.jpg"
            alt=""
          />
        </div>

        <div class="post__body">
          <div class="post__header">
            <div class="post__headerText">
              <h3>
                {"Guillotine Tea"}
                <span class="post__headerSpecial"
                  ><span class="material-icons post__badge"> verified </span>@GuillotineTea</span
                >
              </h3>
            </div>
            <div class="post__headerDescription">
              <p>{tweet[1]}</p>
            </div>
          </div>
        '''
            html += post_header
            media = self.db_cursor.execute("SELECT * FROM media WHERE tweet_id=?", (tweet[0],)).fetchall()
            for file in media:
                key = file[1]
                url = file[3]
                media_type = file[4]
                if media_type == "photo":
                    html += f"<img src='{self.media_path}/{key}.jpg' alt='image'><br>"
                elif media_type == "video":
                    html += f"<video src='{self.media_path}/{key}.mp4' alt='video'></video><br>"
                elif media_type == "animated_gif":
                    html += f"<img src='{self.media_path}/{key}.gif' alt='gif'><br>"
            html += post_footer
        html += '''
            </div>
    <!-- feed ends -->
        </body>
        </html>
        '''
        with open("index.html", "w") as f:
            f.write(html)

    def to_markdown(self):
        # convert the database to markdown
        tweets = self.db_cursor.execute("SELECT * FROM tweets").fetchall()
        for tweet in tweets:
            print(tweet[1])
            media = self.db_cursor.execute("SELECT * FROM media WHERE tweet_id=?", (tweet[0],)).fetchall()
            for file in media:
                key = file[1]
                url = file[3]
                media_type = file[4]
                if media_type == "photo":
                    print(f"![]({self.media_path}/{key}.jpg)")
                elif media_type == "video":
                    print(f"![]({self.media_path}/{key}.mp4)")
                elif media_type == "animated_gif":
                    print(f"![]({self.media_path}/{key}.gif)")
            print("  ")

if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("-b", "--bearer_token", help="Bearer Token", required=True, type=str)
    argparser.add_argument("-i", "--id", help="Twitter ID", required=True)
    argparser.add_argument("-d", "--db", help="Database File", required=True)
    args = argparser.parse_args()
    bearer_token = args.bearer_token
    twitter_id = args.id
    db_file = args.db
    archive_bot = TwitterArchiveBot(twitter_id, bearer_token, db_file)
    latest_tweet = archive_bot.db_cursor.execute("SELECT tweet_id FROM tweets ORDER BY tweet_id DESC LIMIT 1").fetchone()
    if latest_tweet is not None:
        latest_tweet = latest_tweet[0]
    archive_bot.get_tweets(since_id=latest_tweet)
    archive_bot.download_media()
    archive_bot.to_html()
    archive_bot.close()

    



