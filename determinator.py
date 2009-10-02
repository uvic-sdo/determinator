import os.path
import sys
import mimetypes
import re
mimetypes.init('mime.types')


class SourceFile(object):
    def __init__(self, pathname, fparser):
        if not os.path.isfile(filename):
            print("given path is not a file")
            quit()
        self.fparser = fparser
        self.filename = os.path.abspath(filename)
        self.type = mimetypes.guess_type(filename)
        if not self.type[0] or self.type[0].split('/')[0] not in ['audio', 'video']:
            print("Unsupported file type")
            quit()
        self.metadata = {} # It might be wise to have globally available metadata defined here, e.g. 'video_root' defining a base directory for all videos

    def getMetadata(self):
        self.metadata = self.fparser.parse(filename)
        if type[0] == 'audio/mpeg':
            print 'Extracting ID3 tags not implemented yet'


class FilenameParser(object,MimeChecker):
    def __init__(self, pattern_file):
        self.pattern_file = pattern_file
        self.file = open(self.pattern_file, 'r')

    def parse(self, filename):
        metadata = {} # It might be wise to have globally available metadata defined here, e.g. 'video_root' defining a base directory for all videos
        self.file.seek(0)
        for line in self.file:
            line = line.strip()
            if line == '' or line[0] == '#':
                continue
            mime_pattern, regex = re.split('\t+', line)
            regex = regex.strip()
            if pattern.check_mime(type):
                regex = re.compile(regex)
                match = regex.search( filename.replace(root,'') )
                if match:
                    metadata = match.groupdict()
                    break
        return metadata

class TargetMatcher(object,MimeChecker):
    def __init__(self, line):
        self.mime_pattern, self.target, self.operators = re.split('\t+', line)

def check_mime(self, type):
    pattern = self.mime_pattern.split('/')
    type = type[0].split('/')
    for i in range( min( len(pattern), len(type) ) ):
        if pattern[i] == '*' or pattern[i] == type[i]:
            continue
        else:
            return False
    return True

if os.name in ['nt', 'ce']:
    linking_disabled = True

try:
    filename = sys.argv[1]
except:
    print("No filename provided")
    quit()


#FIXME - This will be a config variable later
root = os.getcwd()

fparser = FilenameParser('filename-patterns.txt')
fmover = FileMover('match-rules.txt')
sourcefile = SourceFile(filename, fparser, fmover)
sourcefile.getMetadata()
sourcefile.move()



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
