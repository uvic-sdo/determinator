import os.path
import sys
import mimetypes
import re
mimetypes.init()
mimetypes.add_type('audio/flac','.flac')
mimetypes.add_type('video/matroska','.mkv')
mimetypes.add_type('video/avi','.xvid')
mimetypes.add_type('video/wmv','.wmv')

def match_mime(pattern, type):
    pattern = pattern.split('/')
    type = type[0].split('/')
    for i in range( min( len(pattern), len(type) ) ):
        if pattern[i] == '*' or pattern[i] == type[i]:
            continue
        else:
            return False
    return True

try:
    filename = sys.argv[1]
except:
    print("No filename provided")
    quit()

if os.path.isfile(filename): filename = os.path.abspath(filename)

#FIXME - This will be a config variable later
root = os.getcwd()

type = mimetypes.guess_type(filename)
if not type[0] or type[0].split('/')[0] not in ['audio', 'video']:
    print("Unsupported file type")
    quit()

fh = open('filename-patterns.txt')
metadata = {}
for line in fh:
    if line[0] == '#' or line == '\n':
        continue
    try:
        mime_pattern, regex = line.split('\t')
        regex = regex.strip()
    except ValueError:
        print("Invalid filename pattern line:", line)
        quit()
    if match_mime(mime_pattern, type):
        regex = re.compile(regex)
        match = regex.search( filename.replace(root,'') )
        if match:
            metadata = match.groupdict()
            break

print(filename, metadata)
