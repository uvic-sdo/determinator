import os.path
import mimetypes
mimetypes.init()
mimetypes.add_type('audio/flac','.flac')
mimetypes.add_type('video/matroska','.mkv')
mimetypes.add_type('video/avi','.xvid')

class SourceFile():
    def __init__(self, path, root):
        path = path.replace(root+'/','')
        self.fullpath = path
        self.path = path.split('/')
        self.filename = path.split('/').pop()
        self.guessType()
        if self.type[0] == 'audio':
            self.file = AudioSource(path)
        elif self.type[0] == 'video':
            self.file = VideoSource(path)
        
    def guessType(self):
        g = mimetypes.guess_type(self.path)[0]
        if g[0:5] in ['audio','video']:
            return g.split('/')

class AudioSource():
    patterns = {
      'year': re.compile(r'(\d{4}(?: - | |-))'),
      'track': re.compile(r'(\d+(?: - | |-))'),
    }

    def __init__(self, path):
        parent_dir = path[len(path) - 1]
        artist, album, title = path[0], path[1], path[2]
        del(path)
        title = title[0:title.rfind('.')]
        # Check for year in album 
        if self.patterns['year'].match(album):
            year = self.patterns['year'].findall(album)[0]
            album = album[len(year):]
            year = year[0:3]
        # Check for track number in title 
        if self.patterns['track'].match(title):
            track = self.patterns['track'].findall(title)[0]
            title = title[len(track):]
            track = track.replace(' ','').replace('-','')
        self.data = locals()
        del(self.data['self'])
        del(self.data['root'])

