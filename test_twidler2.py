from twidler2 import TweetFetcher
from unittest.mock import Mock


def test_parse_image_urls():
    twf = TweetFetcher()
    media = Mock(type='photo', media_url='asd')
    tweet = Mock(media=[media, ])
    twf.tweets = [tweet, tweet, ]
    assert tweet.media[0].type
    assert len(twf.parse_image_urls()) == 1


def test_update_last_tweet():
    twf = TweetFetcher()
    tweet = Mock(id=10)
    twf.last_tweet = 0
    twf.tweets = [tweet, ]
    twf._update_last_tweet()
    assert twf.last_tweet == 10


def test_fetch():
    twf = TweetFetcher()
    tweet = Mock(id=10)
    twf.api = Mock()
    twf.api.GetHomeTimeline = Mock(return_value=[tweet, ])
    twf.fetch()
    assert twf.tweets
    assert twf.last_tweet == 10
