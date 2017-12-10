# coding: utf-8
import time
import os
import os.path
import json
import argparse
from attr import attrs, attrib
import requests as rq
import twitter as tw
import logging

logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)


@attrs
class Configuration:
    """Handles persistent configuration"""
    consumer_key = attrib(default='')
    consumer_secret = attrib(default='')
    access_token_key = attrib(default='')
    access_token_secret = attrib(default='')
    download_folder = attrib(
        default=os.path.dirname(
            os.path.realpath(__file__)) +
        '/imgs')

    def load_settings(self):
        path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(path, 'config.json')) as f:
            self.__dict__.update(json.load(f))
        logger.info(f'Loaded {self}')
        return self

    def save_settings(self):
        path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(path, 'config.json'), 'w') as f:
            json.dump(attrs.asdict(self), f)
        logger.info(f'Saved {self}')
        return self


@attrs
class TweetFetcher:
    """Gets tweets from API"""
    consumer_key = attrib(default=None)
    consumer_secret = attrib(default=None)
    access_token_key = attrib(default=None)
    access_token_secret = attrib(default=None)
    user = attrib(default=None)
    tweet_type = attrib(default='likes')
    api = attrib(default=None)

    def connect_to_api(self):
        self.api = tw.Api(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token_key=self.access_token_key,
            access_token_secret=self.access_token_secret)
        logger.info(f'Logged in with as {repr(self.api.VerifyCredentials())}')
        return self

    def fetch_tweets(self):
        if not self.api:
            self.connect_to_api()
        apicall = dict(
            likes=self.api.GetFavorites,
            tweets=self.api.GetUserTimeline,
        )
        self.tweets = []
        try:
            res = apicall[self.tweet_type](screen_name=self.user, count=200)
        except KeyError:
            logger.warn(
                f'Unsupported tweet type. Type should be one of: {apicall.keys()}')
            return self
        while True:
            if res:
                self.tweets.extend(res)
            try:
                res = apicall[self.tweet_type](
                    screen_name=self.user, count=200, max_id=res[-1].id)
                res.pop(0)  # remove the over-lapping tweet to avoid duplicates
            except tw.TwitterError:
                logger.warn('Encountered rate-limit, waiting 5 minutes')
                time.sleep(5 * 60)
            logger.info(res)
            time.sleep(5)
            if not res:
                break
        return self

    def get_media_urls(self, media_type='photo', no_duplicates=True):
        urls = set()
        for s in self.tweets:
            try:
                for m in s.media:
                    if m.type == media_type:
                        url = m.media_url
                        urls.add(url)
            except TypeError:
                pass
        if no_duplicates:
            urls = list(set(urls))
        return urls

    # def remove_duplicates(self):
    #     tmp = []
    #     for x in self.tweets:
    #         if x in tmp:
    #             continue
    #         tmp.append(x)

    #     self.tweets = tmp
    #     return self


def download(
        url_list=None,
        download_folder=os.path.dirname(
            os.path.realpath(__file__)) + '/imgs'):
    for img in url_list:
        req = rq.get(img)
        if req.status_code != 200:
            logger.warn(
                f'Received status code {req.status_code} while downloading images')
            time.sleep(5)
        name = img.split('/')[-1]
        os.makedirs(download_folder, exist_ok=True)
        with open(os.path.join(download_folder, name), 'wb') as f:
            f.write(req.content)


@attrs
class Downloader:
    """Downloads image urls to a folder"""
    url_list = attrib()
    download_folder = attrib(default=os.path.dirname(
        os.path.realpath(__file__)) +
        '/imgs')

    def download(self):
        for img in self.url_list:
            req = rq.get(img)
            if req.status_code != 200:
                logger.warn(
                    f'Received status code {req.status_code} while downloading images')
                time.sleep(5)
            name = img.split('/')[-1]
            os.makedirs(self.download_folder, exist_ok=True)
            with open(os.path.join(self.download_folder, name), 'wb') as f:
                f.write(req.content)

        return self


@attrs
class TwitterImageDownloader:

    config = attrib(default=Configuration())

    def get_urls(self, user=None, tweet_type=None, save_file=None):
        tweetfetcher = TweetFetcher(
            config=self.config)
        urls = tweetfetcher.fetch_tweets().get_media_urls()
        return urls

    def download_images(self, urls):
        return Downloader(url_list=self.get_urls()).download()


def main():
    parser = argparse.ArgumentParser(
        description="""Download images from user's tweets or likes on twitter""")
    parser.add_argument(
        '--download',
        action='store_true',
        help='Download images to download_folder or to ./imgs instead of just getting a list of urls.')
    parser.add_argument(
        '--user',
        default=None,
        help='The username(screen name) of the user whose tweets or likes you want do get.')
    parser.add_argument(
        '--tweet_type',
        default='likes',
        help='Valid values are "likes" or "tweets"')
    parser.add_argument(
        '-v',
        '--verbose',
        action='count',
        default=0,
        help='Verbosity level.')
    parser.add_argument(
        '--load',
        action='store_true',
        help='Load the configuration from config.json')
    parser.add_argument(
        '--save',
        action='store_true',
        help='Save the arguments to config.json')
    parser.add_argument('--consumer_key')
    parser.add_argument('--consumer_secret')
    parser.add_argument('--access_token_key')
    parser.add_argument('--access_token_secret')
    parser.add_argument(
        '--download_folder',
        help='Absolute path of the desired download destination folder.')
    args = parser.parse_args()
    logger.setLevel([logging.WARN, logging.INFO, logging.DEBUG][args.verbose])
    if args.load:
        config = Configuration().load_settings()
    else:
        cargs = vars(args)
        cargs = {k: v for k, v in vars(
            args).items() if k in vars(Configuration)}
        config = Configuration(**cargs)
    if args.save:
        config = config.save_settings()
    tid = TweetFetcher(args.user)
    if args.download:
        download(url_list=tid.fetch_tweets().get_media_urls(
            user=args.user,
            tweet_type=args.tweet_type))
        tid.download_images(
            tid.get_urls(
                user=args.user,
                tweet_type=args.tweet_type))
        logger.info(f'All images downloaded to {config.download_folder}')
    else:
        print(
            '\n'.join(
                tid.get_urls(
                    user=args.user,
                    tweet_type=args.tweet_type,
                    save_file=None)))


if __name__ == '__main__':
    main()
