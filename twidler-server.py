from flask import Flask
from flask import g, session, flash, render_template
from flask import url_for, request, redirect
from flask_oauthlib.client import OAuth
import twidler2 as tdl

app = Flask(__name__)

app.secret_key = 'supah-secret'
app.debug = True

oauth = OAuth(app)

CONSUMER_KEY = 'qOaSbnyDJ4NXcYQ3kzH2Uje9B'
CONSUMER_SECRET = 'tXeqtBbJ3c7ff8RZj7u4TvgvsziKNDGNB5bJ35xy7r9Q0fYP4N'

twitter = oauth.remote_app(
    'twitter',
    consumer_key=CONSUMER_KEY,
    consumer_secret=CONSUMER_SECRET,
    base_url='https://api.twitter.com/1/',
    request_token_url='https://api.twitter.com/oauth/request_token',
    access_token_url='https://api.twitter.com/oauth/access_token',
    authorize_url='https://api.twitter.com/oauth/authorize', )


@twitter.tokengetter
def get_twitter_token():
    if 'twitter_oauth' in session:
        resp = session['twitter_oauth']
    return (resp['oauth_token'], resp['oauth_token_secret'])


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/url-fetch', methods=['POST'])
def url_fetch():
    user = request.form['screen_name'] or session['twitter_oauth']['screen_name']
    # get_favs = bool(request.form.get('favs')) or False
    # if get_favs:
    #     tweet_type = 'likes'
    # else:
    #     tweet_type = 'tweets'
    tweet_type = request.form.get('tweet-type')
    print(user, tweet_type)
    tweetfetcher = tdl.TweetFetcher(
        consumer_key=CONSUMER_KEY,
        consumer_secret=CONSUMER_SECRET,
        access_token_key=session['twitter_oauth']['oauth_token'],
        access_token_secret=session['twitter_oauth']['oauth_token_secret'])
    print(tweetfetcher)
    urls = '\n'.join(
        tweetfetcher.fetch(user=user, timeline=tweet_type).parse_image_urls())
    return render_template('result.html', urls=urls)


@app.route('/clear')
def clearsession():
    session.clear()
    return redirect(url_for('index'))


@app.before_request
def before_request():
    g.user = None
    if 'twitter_oauth' in session:
        g.user = session['twitter_oauth']


@app.route('/login')
def login():
    callback_url = url_for('oauthorized', next=request.args.get('next'))
    return twitter.authorize(callback=callback_url or request.referrer or None)


@app.route('/logout')
def logout():
    session.pop('twitter_oauth', None)
    return redirect(url_for('index'))


@app.route('/oauthorized')
def oauthorized():
    resp = twitter.authorized_response()
    if resp is None:
        flash('You denied the request to sign in.')
    else:
        flash(f'Authorization completed with: {resp["screen_name"]}')
        session['twitter_oauth'] = resp
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run()
