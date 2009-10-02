import os.path
import sys
import mimetypes
import re
import configparser
mimetypes.init('mime.types')

class SourceFile(object):
    ''' This class represents a file to be determinated. It requires a valid 
    pathname and an FilenameParser object '''
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
        ''' Extract metadata by calling FileParser.parse, and any other valid
        extraction method '''
        self.metadata = self.fparser.parse(filename)
        if self.type[0] == 'audio/mpeg':
            print 'Extracting ID3 tags not implemented yet'

    def applyRules(self, rules):
        ''' Apply the provided set of rules to the file '''
        for rule in rules:
            target, operators = rule
            for operator in operators:
                if linking_disabled and operator in 'Ll':
                    print("Linking not possible on this platform")
                    continue
                if operator in 'MLl':
                    os.makedirs( os.path.dirname(target) )
                if   operator == 'M':
                    os.rename(self.filename, target)
                    self.filename = target
                elif operator == 'L':
                    # FIXME - Add a check to ensure filename and target are on same filesystem
                    try: os.link(self.filename, target)
                    except OSError: 
                        print("Creation of cross-device hardlink failed, falling back to symlink")
                        operator = 'l'
                elif operator == 'l':
                    os.symlink(self.filename, target)

class FilenameParser(object,MimeChecker):
    def __init__(self, pattern_file, root=''):
        self.file = open(pattern_file, 'r')

    def parse(self, filename):
    ''' Parse the given filename using filename patterns read in from rules file '''
        metadata = {}
        self.file.seek(0)
        n = 1
        for line in self.file:
            line = line.strip()
            if line == '' or line[0] == '#': continue
            try:
                mime_pattern, regex = re.split('\t+', line)
            except:
                print("Line:", n, "- Ignoring invalid filename parse rule:", line)
            regex = regex.strip()
            if pattern.check_mime(type):
                regex = re.compile(regex)
                match = regex.search( filename.replace(root,'') )
                if match:
                    metadata = match.groupdict()
                    break
            n += 1
        return metadata

class TargetRuleSet(object,MimeChecker):
    def __init__(self, filename):
        self.file = open(filename, 'r')
        
    def getRules(self, metadata):
    ''' Find matching rules for the given metadata in the target rules file '''
        rules = []
        n = 1
        for line in self.file:
            line = line.strip()
            if line == '' or line[0] == '#': continue
            try:
                mime_pattern, target, operators = line.split('\t')
            except ValueError:
                print("Line:", n, "- Ignoring invalid target rule:", line)
                continue
            if match_mime(mime_pattern, type):
                try: target = target.format(**metadata)
                except KeyError, IndexError: continue
                rules.append((target, operators))
                if operators.find('f') < 0: break
            n += 1
        return rules

class MimeChecker(object):
''' Simple class used only to spread the check_mime method around '''
    def check_mime(self, pattern, type):
    ''' Checks to see if the provided pattern and type match '''
        pattern = pattern.split('/')
        type = type[0].split('/')
        for i in range( min( len(pattern), len(type) ) ):
            if pattern[i] == '*' or pattern[i] == type[i]: continue
            else: return False
        return True

if __name__ == "__main__":
    #FIXME - This will be a config variable later
    root = os.getcwd()

    try: filename = sys.argv[1]
    except:
        print("No filename provided")
        quit()

    fparser = FilenameParser('filename-patterns.txt', root)
    rules = TargetRuleSet('match-rules.txt')

    if os.name in ['nt', 'ce']:
        linking_disabled = True
    sourcefile = SourceFile(filename, fparser)
    sourcefile.getMetadata()
    sourcefile.applyRules( rules.getRules( sourcefile.metadata ) )
