
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
import json
import subprocess
from time import sleep
from shutil import rmtree

class VideoIndexEntry(object):
	
	# keys_map maps the key used in the meta dictionary to the name of
	# the attribute it bound do upon initialisation. The key is the 
	# name used in the meta file, the associated value is the attribute name.
	keys_map = {
				"title": "title",
				"description": "description",
				"category": "category",
				"tags": "tags",
				"uri": "uri",
				"id": "id",
				"date_published": "date_published",
				}
	
	def __init__(self, directory, meta):
		
		self.directory = str(directory)
		self.media_file = os.path.join(self.directory, "media")
		self.meta_file = os.path.join(self.directory, "meta")
		
		# Changing anyone of these attributes does NOT change the meta
		# JSON file; must call write_meta_file().
		self.date_published = float(meta.get("date_published", 0.0))
		self.title = str(meta.get("title", ""))
		self.description = str(meta.get("description", ""))
		self.category = str(meta.get("category", ""))
		self.tags = list(meta.get("tags", []))
		self.uri = str(meta["uri"])
		self.id = str(meta["id"])
	
	def execute_command(self, cmd, **kwargs):
		"""
			Executes `cmd` as a child process. Uses Python 2.6/PEP 3101
			string formatting, passing all attributes of `self` and 
			`kwargs` as arguments to the str.format() call.
			
			If there are any intersections between `self.__dict__` and
			`kwargs`, `kwargs`'s value take presedence.
		"""
		subprocess.Popen(str(cmd).format(
							**dict(self.__dict__, **kwargs)), shell=True)
	
	def delete(self):
		"""
			Removes the entry directory via shutil.rmtree. Anything 
			contained within the directory will get removed.
		"""
		rmtree(self.directory)
	
	def write_meta_file(self):
		
		with open(self.meta_file, "w") as meta_file:
			json.dump(self.meta, meta_file, indent=4)
						
	def _get_meta_dict(self):
		
		meta_dict = {}
		
		for key, attr_name in self.__class__.keys_map.iteritems():
			try:
				meta_dict[key] = self.__getattribute__(attr_name)
			except AttributeError:
				raise AttributeError(
					"can't build meta dict; '{0}' attribute missing".format(attr_name))
					
		return meta_dict
	
	def _has_media(self):
		
		for path in os.listdir(self.directory):
			
			if (path == "media" and
					os.path.isfile(os.path.join(self.directory, path))):
				return True
				
		return False
			
	has_media = property(_has_media)
	meta = property(_get_meta_dict)
	
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
							to create.
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
		
	def __contains__(self, obj):
		return obj in self.videos
	
	def add(self, meta):
		"""		
			Creates a VideoIndexEntry from `meta` and a directory to
			house it if one doesn't already exist. If it does, the meta
			file will be overwritten, and the media file, if it exists,
			deleted.
			
			The entry is added to the index. If the entry ID is already
			in the index, it's overidden.
		"""
		
		dir_name = os.path.join(self.directory, meta["id"])
		if not os.path.exists(dir_name):
			os.mkdir(dir_name)

		entry = VideoIndexEntry(dir_name, meta)
		entry.write_meta_file()
		
		self.videos[entry.id] = entry			
	
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

		print "Syncronising video index ..."
		
		for vid in os.listdir(self.directory):
			
			try:
				if os.path.isdir(os.path.join(self.directory, vid)):
					if os.path.isfile(os.path.join(self.directory, vid, "meta")):
						
						with open(os.path.join(self.directory, vid, "meta"), "r") as file_:
							entry = VideoIndexEntry(
										os.path.join(self.directory, vid),
												json.loads(file_.read()))
							self.videos[entry.id] = entry
					else:
						print "Error: Missing meta file for {0}".format(vid)
							
			except ValueError:
				print "Error: Corrupted entry for {0}".format(vid)
	
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
		
