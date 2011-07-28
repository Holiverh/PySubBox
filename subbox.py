#!/usr/bin/env python

# Copyright (C) 2011 by Oliver Ainsworth

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import sys
import os
import optparse
import json
import getpass
from time import sleep

import gdata.youtube.service
import gdata.youtube
# API Reference: http://gdata-python-client.googlecode.com/hg/pydocs/gdata.html

from video_index import VideoIndex
from yt_client import YouTubeClient

def login(user=None, password=None):
	
	if not user or not password:
		print "Error: Attempt to login failed due to no user or password being provided!"
		exit()
	
	print "Logging in ...",
	try:
		client = YouTubeClient.Login(user, password)
		print "Okay!"
		return client
	except gdata.service.BadAuthentication:
		print "Error: Incorrect username or password!"
		exit()

CONFIG_DIR_PATH = os.path.join(
					os.getenv("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
					, "pysubbox")
CONFIG_FILE_PATH = os.path.join(CONFIG_DIR_PATH, "config.json")

DEFAULT_CONFIG = {
				"username": "",
							
				"cmd": {
						"play": "mplayer {media_file}",
						"download": "clive -f {format} --output-file='{media_file}' {uri}",
						},
						
				"resolution": "best",
				
				"search_limit": 15, # 0 = all
				"feed_limit": 25, # 0 - 50
				
				"threshold": 0.33, # 0 - 1
				
				"index_dir": os.path.join(os.path.expanduser("~"),
											"Videos", "Subscriptions"),	
				}

if not os.path.isfile(CONFIG_FILE_PATH):
	print "Configuration file missing! Creating it '{0}' ...".format(CONFIG_FILE_PATH)
	
	if not os.path.isdir(CONFIG_DIR_PATH):
		os.mkdir(CONFIG_DIR_PATH)
		
	with open(CONFIG_FILE_PATH, "w") as config_file:
		json.dump(DEFAULT_CONFIG, config_file, sort_keys=True, indent=4)

with open(CONFIG_FILE_PATH, "r") as config_file:
	
	config = json.load(config_file)
	for key in DEFAULT_CONFIG:
		if key not in config:
			config[key] = DEFAULT_CONFIG[key]

if __name__ == '__main__':
	
	option_parser = optparse.OptionParser(usage="python %prog (update|search|(download|play|repair videoID, ...)) [options]")
	option_parser.add_option("-u", "--username", action="store", type="string", dest="username", default=config["username"], help="username/email you use to log into YouTube")
	option_parser.add_option("-p", "--password", action="store", type="string", dest="password", help="password you use to log into YouTube")
	option_parser.add_option("-q", "--query", action="store", type="string", dest="search_query", help="query used to search the video index")
	option_parser.add_option("--limit", action="store", type="int", dest="limit", default=-1, help="if 'search', truncates the number of results, if 'update' limits the number of videos to fetch from the feed")
	option_parser.add_option("--threshold", action="store", type="float", dest="threshold", default=config["threshold"], help="set the threshold, as a fraction in the range 0 <= x <= 1, for search results; higher = only the very best matches are printed")
	option_parser.add_option("--index-dir", action="store", type="string", dest="index_dir", default=config["index_dir"], help="the path to the directory which should be indexed; defaults to ~/Videos/YouTube")
	option_parser.add_option("--start-index", action="store", type="int", dest="start_index", default=1, help="when updating, where should the feed index start from; greater = older videos")
	option_parser.add_option("-r", "--resolution", action="store", type="string", dest="resolution", default=config["resolution"], help="when downloading, determines the format to be requested, based on closest matched resolution; clive presets also accepted")
	option_parser.add_option("-c", "--cmd", action="store", type="string", dest="cmd", default=None, help="command to be used when downloading/playing media, see the README for details")
	
	try:
		action = sys.argv[1].lower()
	except IndexError:
		option_parser.print_usage()
		exit()
		
	options, args = option_parser.parse_args(sys.argv[1:])
	
	if options.limit == -1:
		
		if action == "search":
			options.limit = config["search_limit"]
		elif action == "update":
			options.limit = config["feed_limit"]
	
	videx = VideoIndex(options.index_dir)
	
	# Shells which have a command history featuer may save previous commands to a
	# plain-text file. This means, any passwords used via the -p or --password
	# switch/flag/whatever will be exposed.
	if options.password is None:
		options.password = getpass.getpass("Password: ")
	else:
		print "Warning: Use of the -p or --password is discouraged as a potential" \
				" security vunerability!"

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
						try:
							videx.add(client.GetVideoMeta(entry=entry))
						except AttributeError:
							print "Error: Can't fetch video data for {0}".format(
														entry.id.text.split("/")[-1])
						
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
							
						# The RequestError is raised when accessing the
						# video's 'meta' data via YouTubeClient.GetVideoMeta.
						# So it's per-video request, not per-feed it appears.
					print "Error: Unexpected response to feed request!" \
													" {0}".format(exce)
				
				
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
		
		if not options.cmd:
			options.cmd = DEFAULT_CONFIG["cmd"]["download"]
		
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
				video.execute_command(options.cmd, format=fmt)
				
		else:
			
			for vid in args[1:]:
				try:
					videx[vid].execute_command(options.cmd, format=fmt)
				except KeyError:
					print "Error: {0} not in index!".format(vid)
					
	elif action == "play":
		
		if not options.cmd:
			options.cmd = DEFAULT_CONFIG["cmd"]["play"]
		
		videx.sync()
		
		try:
			try:
				for vid in args[1:]:
					videx[vid].execute_command(options.cmd)
			except KeyError:
				print "Error: {0} not in index!".format(vid)
		except IndexError:
			print "Error: You need to provide a video ID to play."
			
	elif action == "repair":
		
		client = login(options.username, options.password)
		
		for vid in args[1:]:
			
			print "Attempting to repair {0}".format(vid)
			
			try:
				videx.add(client.GetVideoMeta(vid=vid))
			except gdata.service.RequestError as exce:
				print "Error: Unexpected response to request!" \
													" {0}".format(exce)
			except AttributeError:
				print "Error: Can't fetch video data for {0}".format(
											entry.id.text.split("/")[-1])
			
	else:

		option_parser.print_usage()
		
		
