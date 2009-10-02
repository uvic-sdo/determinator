import os.path
import sys
import mimetypes 
import re
import fnmatch
#import configparser

class SourceFile(object):
    ''' This class represents a file to be determinated. It requires a valid 
    pathname and an FilenameParser object '''

    def __init__(self, filename, fnparser):
        if not os.path.isfile(filename):
            raise IOError("Could not read file: '"+filename+"'")
        self.fnparser = fnparser
        self.filename = os.path.abspath(filename)
        self.type = mimetypes.guess_type(filename)
        if not self.type[0] or self.type[0].split('/')[0] not in ['audio', 'video']:
            raise IOError("Unsupported filetype in file '"+filename+"'")
        self.metadata = {'filename': os.path.basename(filename)} # It might be wise to have globally available metadata defined here, e.g. 'video_root' defining a base directory for all videos

    def getMetadata(self):
        ''' Extract metadata by calling FileParser.parse, and any other valid extraction method '''
        self.metadata.update( self.fnparser.parse(self) )
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
                if operator in 'MLS':
                    if not os.path.isdir( os.path.dirname(target) ):
                        os.makedirs( os.path.dirname(target) )
                if   operator == 'M':
                    os.rename(self.filename, target)
                    self.filename = target
                elif operator == 'L':
                    # FIXME - Add a check to ensure filename and target are on same filesystem
                    try: os.link(self.filename, target)
                    except OSError: 
                        print("Creation of cross-device hardlink failed, falling back to symlink")
                        operator = 'S'
                elif operator == 'S':
                    os.symlink(self.filename, target)

class FilenameParser(object):
    def __init__(self, pattern_file, root=None):
        self.file = open(pattern_file, 'r')
        self.root = root or ''

    def readline(self, line):
        try: mime_pattern, regex = re.split('\t+', line)
        except: return None
        regex = regex.strip().replace('/',os.path.sep)
        return (mime_pattern, regex)

    def parse(self, sf):
        ''' Parse the given filename using filename patterns read in from rules file '''
        self.file.seek(0)
        for line in self.file:
            if comment(line): continue
            line = self.readline(line)
            if line and match_mime(line[0], sf.type):
                regex = re.compile(line[1])
                match = regex.search( sf.filename.replace(self.root,'') )
                if match:
                    return match.groupdict()
        return {}

class TargetRuleSet(object):
    def __init__(self, filename):
        self.file = open(filename, 'r')
        
    def readline(self, line):
        try: mime_pattern, target, operators = re.split('\t\s*', line.strip())
        except: return None
        return (mime_pattern, target, operators)

    def getRules(self, sf):
        ''' Find matching rules for the given metadata in the target rules file '''
        self.file.seek(0)
        rules = []
        for line in self.file:
            if comment(line): continue
            line = self.readline(line)
            print line
            if line and match_mime(line[0], sf.type):
                print line[1], sf.metadata
                try: target = line[1].format(**sf.metadata)
                except KeyError, IndexError: continue
                rules.append((target, line[2]))
                if line[2].find('f') < 0: break
        return rules

def match_mime(pattern, type):
    return bool( re.match( fnmatch.translate( pattern ), type[0] ) )

def comment(line):
    line = line.strip()
    if line == '' or line[0] == '#': return True

if __name__ == "__main__":
    #FIXME - This will be a config variable later
    root = os.getcwd()

    try: filename = sys.argv[1]
    except:
        print("No filename provided")
        quit()

    mimetypes.init(['mime.types'])
    fnparser = FilenameParser('filename-patterns.txt', root)
    target_rules = TargetRuleSet('match-rules.txt')

    if os.name in ['nt', 'ce']:
        linking_disabled = True
    sourcefile = SourceFile(filename, fnparser)
    sourcefile.getMetadata()
    rules = target_rules.getRules( sourcefile )
    print rules
    sourcefile.applyRules( rules )
