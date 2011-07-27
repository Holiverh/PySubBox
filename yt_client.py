
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

import time

import gdata.youtube
import gdata.youtube.service

class YouTubeClient(gdata.youtube.service.YouTubeService):
	
	@classmethod
	def Login(cls, username, password):
		"""
			Convenience method that creates a new YouTubeService
			instance and performs a log-in using the given credentials
			via YouTubeService.ClientLogin().
		"""
		
		client = cls(username, password)
		client.ClientLogin(username, password)
		
		return client
	
	def GetVideoMeta(self, uri=None, vid=None, entry=None):
		"""
			Wraps the returned value of YoutubeService.GetYouTubeVideoEntry
			into a dictioanry which can then be passed to the intialiser
			of video_index.VideoIndexEntry.
			
			The returned dictionary will contain the following keys and
			associated values:
			
				id				- String of the video ID (string)
				uri				- URI to watch page (string)
				description		- Video description (string)
				title			- Title of video (string)
				category		- Which category the video is filed under
								(string)
				tags			- List of strings containing the video's
								tags
				date_published	- The timestamp of the video's publication
									time in seconds since the epoch,
									represented as a float
			
			If `entry` is set to a YouTubeVideoEntry instance, it will be
			used for generating the dictionary, instead of fetching the
			meta via YoutubeService.GetYouTubeVideoEntry.
			
			In the event that the video isn't available to the user an
			AttributeError will be raised.
		"""
		
		# If no entry provided, fetch it ...
		if not entry:
			entry = self.GetYouTubeVideoEntry(uri, vid)
		
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
		
		# We ignore anything sub-second in resolution.
		meta["date_published"] = time.mktime(
									time.strptime(entry.published.text,
												"%Y-%m-%dT%H:%M:%S.000Z"))
												
		return meta
