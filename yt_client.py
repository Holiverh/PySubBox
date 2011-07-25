
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
	
	def GetVideoMeta(self, uri=None, vid=None):
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
		"""
		
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
