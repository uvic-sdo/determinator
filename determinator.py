import os.path
import sys
import mimetypes
import re
mimetypes.init()
mimetypes.add_type('audio/flac','.flac')
mimetypes.add_type('video/matroska','.mkv')
mimetypes.add_type('video/avi','.xvid')

def match_mime(pattern, type):
    pattern = pattern.split('/')
    type = type[0].split('/')
    for i in [1,2]:
        if pattern[i] == '*' or pattern[i] == type[i]:
            continue
        else:
            return False
    return True

try:
    filename = sys.argv[1]
except:
    print "No filename provided"
    return

if os.path.isfile(filename): filename = os.path.abspath(filename)

type = mimetypes.guess_type(filename)
if type[0].split('/')[0] not in ['audio', 'video']:
    print "Unsupported file type"
    return

fh = open('filename-patterns.txt')
for line in fh:
    mime_pattern, regex = line.split('\t')
    if match_mime(mime_pattern, regex):
        regex = re.compile(regex)
        match = regex.search(filename)
        if match:
            metadata = match.groupdict()
            break

print filename, metadata 
