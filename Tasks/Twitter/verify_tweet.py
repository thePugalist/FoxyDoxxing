from __future__ import absolute_import

from vars import CELERY_STUB as celery_app

@celery_app.task
def verify_tweet(uv_task):
	task_tag = "TWEETER: VERIFYING TWEET"

	print "verifying tweet at %s" % uv_task.doc_id
	print "\n\n************** %s [START] ******************\n" % task_tag
	uv_task.setStatus(302)

	# look up tweet by id in url
	from lib.Worker.Models.dl_FD_mention import FoxyDoxxingMention

	mention = FoxyDoxxingMention(_id=uv_task.doc_id)
	if not hasattr(mention, 'url'):
		error_msg = "no url for this tweet"

		print error_msg
		print "\n\n************** %s [ERROR] ******************\n" % task_tag
		
		uv_task.fail(status=412, message=error_msg)
		return
	
	# if doesn't exist, fail
	import requests
	from conf import DEBUG

	try:
		r = requests.get(mention.url)
	except Exception as e:
		error_msg = e

		print error_msg
		print "\n\n************** %s [ERROR] ******************\n" % task_tag
		
		uv_task.fail(status=412, message=error_msg)
		return

	if r.status_code != 200:
		error_msg = "Could not get url %s" % mention.url

		print error_msg
		print "\n\n************** %s [ERROR] ******************\n" % task_tag
		
		uv_task.fail(status=412, message=error_msg)
		return

	from bs4 import BeautifulSoup, element

	original_tweet = None
	original_tweet_div = None

	try:
		for div in BeautifulSoup(r.content).find_all('div'):
			if 'class' in div.attrs.keys() and 'js-original-tweet' in div.attrs['class']:
				original_tweet_div = div
				break
	except Exception as e:
		error_msg = e

		print error_msg
		print "\n\n************** %s [ERROR] ******************\n" % task_tag
		
		uv_task.fail(status=412, message=error_msg)
		return

	if original_tweet_div is None:
		error_msg = "Could not extract original tweet"

		print error_msg
		print "\n\n************** %s [ERROR] ******************\n" % task_tag
		
		uv_task.fail(status=412, message=error_msg)
		return

	mention.tweet_id = div.attrs['data-item-id']
	try:
		mention.tweet_text = mention.raw_request("statuses/show.json?id=%s" % mention.tweet_id)['text']
	except Exception as e:
		print "could not get original tweet text: %s" % e
		print "\n\n************** %s [WARN] ******************\n" % task_tag

	mention.save()

	mention.set_stats()

	mention.addCompletedTask(uv_task.task_path)

	# tweet is valid.  check its retweets every 10 minutes for 24 hours
	from time import time
	uv_task.set_recurring("Twitter.get_retweets.get_retweets", 15, time() + (24 * 60 * 60), salt="doc_id")

	uv_task.routeNext()

	print "\n\n************** %s [END] ******************\n" % task_tag
	uv_task.finish()