import argparse
import logging
import pickle
import time
from functools import partial

import requests as rq
from bs4 import BeautifulSoup as bs

import twitter as tw

logging.basicConfig(level=logging.WARN)
logger = logging.getLogger(__name__)


class TweetFetcher():
    """Fetch tweets from user and turn them into a list of img urls."""

    def __init__(self,
                 consumer_key=None,
                 consumer_secret=None,
                 access_token_key=None,
                 access_token_secret=None,
                 wait_time=5 * 60):
        self.consumer_key = consumer_key or \
            'qOaSbnyDJ4NXcYQ3kzH2Uje9B'
        self.consumer_secret = consumer_secret or \
            'tXeqtBbJ3c7ff8RZj7u4TvgvsziKNDGNB5bJ35xy7r9Q0fYP4N'
        self.access_token_key = access_token_key or \
            '58286498-1lBgZZyUpFmow3Hd2Kx3Eg1hvZ30EDakEHLCkdw7U'
        self.access_token_secret = access_token_secret or \
            'sbBpqW1mNwan1xXP8fnndegn4s5yiwIEZ1H4zdruLV4cw'
        self.api = tw.Api(
            consumer_key=self.consumer_key,
            consumer_secret=self.consumer_secret,
            access_token_key=self.access_token_key,
            access_token_secret=self.access_token_secret)
        logger.debug(self.api)
        logger.info(f'Logged in as {repr(self.api.VerifyCredentials())}')
        self.tweets = []
        self.last_tweet = 0
        self.wait_time = wait_time

    def fetch(self, user=None, timeline='home', delta=False):
        """Fetch tweets from specified timeline (home or favorites) and user (defaults to self). Delta option allows to only fetch new tweets."""
        response_total = []
        if delta:
            types = dict(
                home=partial(
                    self.api.GetHomeTimeline, since_id=self.last_tweet),
                favorites=partial(
                    self.api.GetFavorites,
                    since_id=self.last_tweet,
                    screen_name=user))
        else:
            types = dict(
                home=self.api.GetHomeTimeline,
                favorites=partial(self.api.GetFavorites, screen_name=user))
        try:
            res = types[timeline](count=200)
        except KeyError:
            logger.warning(
                f'Unsupported tweet type. Type should be one of: {types.keys()}'
            )
            res = None
        except tw.TwitterError as e:
            logger.warning(e)
            time.sleep(self.wait_time)
            self.fetch()
            return self
        while True:
            if res:
                response_total.extend(res)
            try:
                res = types[timeline](count=200, max_id=res[-1].id)
                res.pop(0)
            except IndexError:
                logger.info('No new tweets found.')
            except tw.TwitterError as e:
                logger.debug(e)
                logger.info('Encountered rate-limit, waiting')
                time.sleep(self.wait_time)
            logger.info(res)
            time.sleep(self.wait_time)
            if not res:
                break
        self.tweets = response_total
        self._update_last_tweet()
        return self

    def parse_image_urls(self):
        img_urls = set()
        for s in self.tweets:
            logger.debug(s)
            try:
                for m in s.media:
                    if m.type == 'photo':
                        url = m.media_url
                        img_urls.add(url)
            except TypeError:
                pass
        img_urls = self.remove_duplicates(img_urls)
        return img_urls

    def _update_last_tweet(self):
        logger.debug(self.last_tweet)
        try:
            if self.last_tweet < max(self.tweets, key=lambda x: x.id).id:
                self.last_tweet = max(self.tweets, key=lambda x: x.id).id
        except ValueError as e:
            logger.debug('last_tweet not updated')

    @staticmethod
    def remove_duplicates(old):
        """Remove duplicate items from a list."""
        return list(set(old))

    @staticmethod
    def output_to_file(inp, fname='img_urls.txt', mode='a'):
        """Output contents of a list to a file, one item per line."""
        with open(fname, mode) as f:
            f.write('\n'.join(list(inp)), mode)


def main():
    parser = argparse.ArgumentParser(
        description=
        """Download images from user's home timeline or likes on twitter""")
    parser.add_argument(
        '-u',
        '--user',
        default=None,
        help=
        'The username(screen name) of the user whose tweets or likes you want to get.'
    )
    parser.add_argument(
        '-t',
        '--tweet_type',
        default='home',
        help='Valid values are "home" or "favorites"')
    parser.add_argument(
        '-o',
        '--output',
        help='File to which urls will be appended. Defaults to stdout.')
    parser.add_argument(
        '-d',
        '--delta',
        action='store_true',
        help='Keep periodically fetching new tweets and outputting them')
    parser.add_argument(
        '-v', '--verbose', action='count', default=0, help='Verbosity level.')
    parser.add_argument('-ck', '--consumer_key', default=None)
    parser.add_argument('-cs', '--consumer_secret', default=None)
    parser.add_argument('-ak', '--access_token_key', default=None)
    parser.add_argument('-as', '--access_token_secret', default=None)
    args = parser.parse_args()
    logger.setLevel([logging.WARN, logging.INFO, logging.DEBUG][args.verbose])

    twf = TweetFetcher(
        consumer_key=args.consumer_key,
        consumer_secret=args.consumer_secret,
        access_token_key=args.access_token_key,
        access_token_secret=args.access_token_secret)
    urls = twf.fetch(
        user=args.user, timeline=args.tweet_type).parse_image_urls()
    if args.output:
        twf.output_to_file(urls, fname=args.output, mode='a')
    else:
        print('\n' + '\n'.join(urls))

    if args.delta:
        while True:
            time.sleep(60)
            urls = twf.fetch(
                user=args.user, timeline=args.tweet_type,
                delta=True).parse_image_urls()
            if args.output:
                twf.output_to_file(urls, fname=args.output, mode='a')
            else:
                print('\n' + '\n'.join(urls))


if __name__ == '__main__':
    main()
