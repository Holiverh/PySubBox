#!/usr/bin/env python

import sys
import os
import os.path
import optparse
from time import sleep

from video_index import VideoIndex

import gdata.youtube.service
import gdata.youtube

def login(user=None, password=None):
	
	if not user or not password:
		print "Error: Attempt to login failed due to no user or password being provided!"
		exit()
	
	print "Logging in ...",
	client = gdata.youtube.service.YouTubeService(options.username,
													options.password)
	try:
		client.ClientLogin(options.username, options.password)
		print "Okay!"
		return client
	except gdata.service.BadAuthentication:
		print "Error: Incorrect username or password!"
		exit()

if __name__ == '__main__':
	
	# Dependancies:
	#	python26
	# 	python-gdata
	#	clive
	#	mplayer
	
	# TODO: Have a global config file which may contain a defaults for
	# the CL arguments. Saves having to enter them over and over again.
	
	option_parser = optparse.OptionParser(usage="python %prog (update|search|(download|play videoID, ...)) [options]")
	option_parser.add_option("-u", "--username", action="store", type="string", dest="username", help="username/email you use to log into YouTube")
	option_parser.add_option("-p", "--password", action="store", type="string", dest="password", help="password you use to log into YouTube")
	option_parser.add_option("-q", "--query", action="store", type="string", dest="search_query", help="query used to search the video index")
	option_parser.add_option("--limit", action="store", type="int", dest="limit", default=0, help="if 'search', truncates the number of results, if 'update' limits the number of videos to fetch from the feed")
	option_parser.add_option("--threshold", action="store", type="float", dest="threshold", default=0.25, help="set the threshold, as a fraction in the range 0 <= x <= 1, for search results; higher = only the very best matches are printed")
	option_parser.add_option("--index-dir", action="store", type="string", dest="index_dir", default=os.path.join(os.path.expanduser("~"), "Videos", "Subscriptions"), help="the path to the directory which should be indexed; defaults to ~/Videos/YouTube")
	option_parser.add_option("--start-index", action="store", type="int", dest="start_index", default=1, help="when updating, where should the feed index start from; greater = older videos")
	option_parser.add_option("-r", "--resolution", action="store", type="string", dest="resolution", default="best", help="when downloading, determines the format to be requested, based on closest matched resolution; clive presets also accepted")
	
	action = sys.argv[1].lower()
	options, args = option_parser.parse_args(sys.argv[1:])
	
	valid_actions = ["update", "search", "download", "play"]
	if action not in valid_actions:
		print "Error: Expected '{0}' as first argument, got '{1}'.".format(
										"', '".join(valid_actions), action)
	
	videx = VideoIndex(options.index_dir)
	
	if action == "update":
		
		client = login(options.username, options.password)
		
		feed_fetch_attempts = 3
		while feed_fetch_attempts > 0:
			
			print "Fetching subscription feed ...",
			try:
				sub_feed = client.GetYouTubeSubscriptionFeed()
				if isinstance(sub_feed, gdata.youtube.YouTubeSubscriptionFeed):
					print "Okay!"
					feed_fetch_attempts = 0
					continue
			except gdata.service.RequestError:
				pass
			
			feed_fetch_attempts -= 1
			if feed_fetch_attempts == 0:
				print "Error: Can't seem to get ahold of the feed. Try again later."
				exit()
			else:
				print "Error: Failed! Trying again in 10 seconds."
				sleep(10)
		
		for sub_entry in sub_feed.entry:
			for link in sub_entry.feed_link:
				
				uri = "".join([link.href, "?", 
							"&".join(["max-results={0}".format(options.limit),
									"start-index={0}".format(options.start_index)])])
				
				try:
					feed = client.GetYouTubeVideoFeed(uri)
					print "Feed: {0}".format(link.href)
					
					for entry in feed.entry:
				
						meta = {}
						
						for category in entry.category:
							if category.label:
								meta["category"] = category.label

						# I found no garantuee in the docs that the end of the
						# "ID" URI won't have other parameters tacked on. Will
						# assume it's safe though.
						meta["id"] = entry.id.text.split("/")[-1]
						meta["uri"] = entry.media.player.url
						meta["description"] = entry.media.description.text
						meta["title"] = entry.media.title.text
						meta["tags"] = [tag.strip() for tag in 
									entry.media.keywords.text.split(",")]
						
						videx.add(meta)
					
				except gdata.service.RequestError as exce:
					# FIXME: The failed request is caused by being too
					# excessive with the number of requests. Find what 
					# the limit is and throttle accordingly.
					
						# ... actually it appears this may not be the
						# case. In the test environment, 403 is only
						# returned when accessing the 'totalhalibut'
						# feed. Will investigate further. 
					
							# Going to handle it as a regular unexpected
							# response, instead of a special case. At 
							# least until more is known.
					print "Error: Unexpected response to feed request!" \
													"{0}".format(exce)
				
				
	elif action == "search":
		
		if options.search_query or options.search_query == "":
			
			print "Search results for '{0}':".format(options.search_query)
			videx.sync()
													
			for video in videx.search(options.search_query,
										options.threshold,
										options.limit):
				if video.has_media:
					print " - {0} * {1}".format(video.id, video.title)
				else:
					print " - {0}   {1}".format(video.id, video.title)
					
		else:
			
			print "Error: -q or --query option must be set for searching!"
			
	elif action == "download":
		
		res_fmt_map = {
					(176, 144): "fmt17",
					(320, 180): "fmt34",
					(480, 360): "fmt18",
					(640, 380): "fmt35",
					(1280, 720): "fmt22",
					}
				
		# Check if a preset.
		if (options.resolution == "best" or options.resolution in 
						dict([(v, k) for k, v in res_fmt_map.iteritems()])):
			fmt = options.resolution
		else:
			rres = options.resolution
			rres = [int(v) for v in rres.split("x")[:2]]
			
			# Using a lowest average difference for each axis as the 
			# algorithm for determining best possible match for
			# resolution. TODO: Place emphasis on matching aspect ratio.
			
			best_match = None
			for fres in res_fmt_map:
				
				avg_diff = ((rres[0] - fres[0]) + (rres[1] - rres[1])) / 2
				
				if best_match:
					if avg_diff < best_match[0]:
						best_match = (avg_diff, fres)
				else:
					best_match = (avg_diff, fres)

			fmt = res_fmt_map[best_match[1]]
		
		videx.sync()
		
		if options.search_query or options.search_query == "":
			
			print "'Cliving' all those matching query '{0}' ...".format(
													options.search_query)
													
			for video in videx.search(options.search_query,
										options.sr_threshold,
										options.sr_limit):
				video.fetch_media(options.resolution)
				
		else:
			
			for vid in args[1:]:
				try:
					videx[vid].fetch_media(fmt)
				except KeyError:
					print "Error: {0} not in index!".format(vid)
					
	elif action == "play":
		
		videx.sync()
		
		try:
			try:
				for vid in args[1:]:
					videx[vid].play()
			except KeyError:
				print "Error: {0} not in index!".format(vid)
		except IndexError:
			print "Error: You need to provide a video ID to play."
		
		