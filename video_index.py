
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

import os
import os.path
import json
import subprocess
from time import sleep

class VideoIndexEntry(object):
	
	def __init__(self, directory, meta):
		
		self.directory = directory
		
		# IMPORTANT NOTE: changing anyone of these attributes does NOT
		# change the meta JSON file. Possible TODO.
		self.title = meta.get("title", "")
		self.description = meta.get("description", "")
		self.category = meta.get("category", "")
		self.tags = meta.get("tags", [])
		self.uri = meta["uri"]
		self.id = meta["id"]
	
	def _has_media(self):
		
		for path in os.listdir(self.directory):
			
			if (path == "media" and
					os.path.isfile(os.path.join(self.directory, path))):
				return True
				
		return False
			
	has_media = property(_has_media)
	
	def fetch_media(self, fmt):

		exec_ = "clive -f {2} --output-file='{0}' {1}".format(
					os.path.join(self.directory, "media"),
					self.uri,
					fmt)
		subprocess.Popen(exec_, shell=True,).wait()

	def play(self):
		
		exec_ = "mplayer {0}".format(
					os.path.join(self.directory, "media"),
					)
		subprocess.Popen(exec_, shell=True,).wait()
			
class VideoIndex(object):
	
	# TODO: Implement some kind of caching for the video index. Often
	# the index will remain unchanged between each invocation, yet it
	# still has to be rebuilt. This is suboptimal. DO SOME PROFILING
	# to see wether it can be optmised by loading from disk, instead of
	# doing a rebuild.
	
	def __init__(self, directory):
		"""
			Represents a local video index.
			
				`directory` - the path to the directory which should be
							indexed. If does not exist, will attempt
							to crate.
		"""
		
		self.videos = {}
		
		self.directory = str(directory)
		if not os.path.isdir(self.directory):
			print "'{0}' does not exist, creating it ...".format(self.directory)
			os.mkdir(self.directory)
	
	def __getitem__(self, name):
		return self.videos[name]
	
	def __len__(self):
		return len(self.videos)
	
	def __iter__(self):
		return self.videos.iteritems()
	
	def add(self, meta):
		"""
			Creates a directory to house a new video, as defined by `meta`.
			Does *NOT* not create an entry in `videos`, you must sync.
		"""
		
		dir_name = os.path.join(self.directory, meta["id"])
		if not os.path.exists(dir_name):
			os.mkdir(dir_name)
			json.dump(meta, open(os.path.join(dir_name, "meta"), "w"), indent=4)
	
	# TODO: allow sync() to take an argument which specifies a specific
	# directory to be syncronised. Saves having to do a complete resync
	# everytime one video is added.
	def sync(self):
		
		# Profiles of sync appear to show some low-level caching going on
		# which is causing the performance of posix.stat and file.read
		# to fluxuate depending on whether they were recently invoked.
		# This *may* also affect posix.listdir, but the time spent in 
		# listdir is neglible anyway.
		
		# Taken from a profile that compelted in 9.917s (742 enteries):
		# 740    1.759    0.002    1.759    0.002 {method 'read' of 'file' objects}
		# 1484    6.308    0.004    6.308    0.004 {posix.stat}
		
		# ... and from one completed in 2.087:
		# 740    0.099    0.000    0.099    0.000 {method 'read' of 'file' objects}
		# 1484    0.064    0.000    0.064    0.000 {posix.stat}

		print "Syncronising video index ...",
		
		for vid in os.listdir(self.directory):
			
			try:
				if os.path.isdir(os.path.join(self.directory, vid)):
					if os.path.isfile(os.path.join(self.directory, vid, "meta")):
						
						with open(os.path.join(self.directory, vid, "meta"), "r") as file_:
							entry = VideoIndexEntry(
										os.path.join(self.directory, vid),
												json.loads(file_.read()))
							self.videos[entry.id] = entry
							
			except ValueError as e:
				print yellow("Corrupted entry for '{0}'!".format(vid))
				
		print "Done!"
	
	def search(self, query, threshold=0.25, limit=None):
		"""
			... Returns a generator. 
		
				`query` - a string of search terms. May include special
							directives in the form 'key:value'.
							
				`threshold` - percentage of the highest *weight* that a
							a result must reach in order to be included
							in the results.
							
				`limit` - maximum numbers of results to return.
		"""
		
		# This search sucks ... possibly. Options to consider:
		# 	- Keep the base concept (applying weight to a result), but
		#		make use of NLTK to 'enhance' it. Apply special weights
		#		for acronyms, names, and ignore all non-nouns, for example.
		#	- Apache Lucene via PyLucene.
		
		if limit == 0:
			limit = None
		
		results = []
		qsplit = [chunk.lower().strip() for chunk in query.split(" ") if len(chunk) > 2]
		
		for video in self.videos.itervalues():
			
			weight = 0
			
			weight += 0.1 * len(set(qsplit).intersection(set([tag.lower() for tag in video.tags])))
			weight += 0.15 * len(set(qsplit).intersection(set([video.category.lower()])))
			weight += 0.25 * len(set(qsplit).intersection(set([chunk.lower() for chunk in video.description.split(" ")])))
			weight += 0.35 * len(set(qsplit).intersection(set([chunk.lower() for chunk in video.title.split(" ")])))
			
			results.append((weight, video))
		
		results.sort(key=lambda result: result[0])
		
		result_count = 0
		for result in results[::-1]:
			if result[0] >= (results[-1][0] * threshold):
				if result_count < limit or limit is None:
					yield result[1]
					result_count += 1
