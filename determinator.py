import os.path
import mimetypes
mimetypes.init()
mimetypes.add_type('audio/flac','.flac')
mimetypes.add_type('video/matroska','.mkv')
mimetypes.add_type('video/avi','.xvid')

class Pathname():
     def __init__ (self, path, parent=None):
         self.path = path
         self.parent = parent
         self.analyze()
