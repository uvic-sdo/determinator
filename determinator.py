import os.path
import sys
import mimetypes
import re
mimetypes.init('mime.types')

if os.name in ['nt', 'ce']:
    linking_disabled = True

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
metadata = {} # It might be wise to have globally available metadata defined here, e.g. 'video_root' defining a base directory for all videos
for line in fh:
    line = line.strip()
    if line == '' or line[0] == '#':
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
fh.close()

if type[0] == 'audio/mpeg':
    print 'Extracting ID3 tags not implemented yet'

fh = open('match-rules.txt')
for line in fh:
    line = line.strip()
    if line == '' or line[0] == '#':
        continue
    try:
        mime_pattern, target, operators = line.split('\t')
    except ValueError:
        print("Invalid match rule:", line)
        quit()
    if match_mime(mime_pattern, type):
        try:
            target = target.format(**metadata)
        except KeyError, IndexError:
            continue

        fallthrough = False
        for operator in operators:
            if operator in 'MLl':
                os.makedirs( os.path.dirname(target) )
            if linking_disabled and operator in 'Ll':
                print("Linking not possible on this platform")
                continue
            if   operator == 'M':
                os.rename(filename, target)
                filename = target
            elif operator == 'L':
# FIXME - Add a check to ensure filename and target are on same filesystem
                os.link(filename, target)
            elif operator == 'l':
                os.symlink(filename, target)
            elif operator == 'f':
                fallthrough = True
        if fallthrough: break
