import os.path
import sys, getopt
import mimetypes 
import re
import fnmatch
from optparse import OptionParser
#import configparser

class SourceFile(object):
    ''' This class represents a file to be determinated. It requires a valid 
    pathname and an FilenameParser object '''

    def __init__(self, filename, fnparser):
        self.fnparser = fnparser
        self.filename = os.path.abspath(filename)
        self.type = mimetypes.guess_type(filename)
        if not self.type[0] or self.type[0].split('/')[0] not in ['audio', 'video']:
            raise IOError("Unsupported filetype in file '"+filename+"'")
        self.metadata = {'filename': os.path.basename(filename)} # It might be wise to have globally available metadata defined here, e.g. 'video_root' defining a base directory for all videos

    def getMetadata(self):
        ''' Extract metadata by calling FileParser.parse, and any other valid extraction method '''
        self.metadata.update( self.fnparser.parseFile(self) )
        if self.type[0] == 'audio/mpeg':
            print 'Extracting ID3 tags not implemented yet'

    def applyRules(self, rules):
        ''' Apply the provided set of rules to the file '''
        for rule in rules:
            target, operators = rule
            for operator in operators:
                if settings.no_linking and operator in 'Ll':
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
    def __init__(self, pattern_file):
        self.patterns = []
        self._loadPatterns(pattern_file)

    def _loadPatterns(self, pattern_file):
        file = open(pattern_file, 'r')
        for line in file:
            line = line.strip()
            if is_comment(line): continue
            self.patterns.append( self._parseLine(line) )

    def _parseLine(self, line):
        try: mime_pattern, regex = re.split('\t+', line)
        except: return None
        regex = regex.strip().replace('/',str(os.path.sep)[1:-1])
        return (mime_pattern, regex)

    def parseFile(self, sf):
        ''' Parse the given filename using filename patterns read in from rules file '''
        for pattern in self.patterns:
            if pattern and match_mime(pattern[0], sf.type):
                regex = re.compile(pattern[1])
                match = regex.search( sf.filename.replace(settings.root,'') )
                if match:
                    return match.groupdict()
        return {}

class RuleFinder(object):
    def __init__(self, filename):
        self.loadRules(filename)
        self.ruleSet = []

    def loadRules(self, filename)
        file = open(filename, 'r')
        n = 1
        for line in file:
            line = line.strip()
            if is_comment(line): 
                continue
            try: 
                mime_pattern, target, operators = re.split('\t\s*', line)
            except: 
                raise SyntaxError(filename+': Invalid target rule on line '+n)
            self.ruleSet.append( TargetRule(mime_pattern, target, operators) )
            n += 1
        
    def getRules(self, sf):
        ''' Find matching rules for the given metadata in the target rules file '''
        rules = []
        for rule in self.ruleSet:
            if rule.match(sf):
                rules.append(rule)
                if not rule.fallthrough: 
                    break
        return rules

class TargetRule(object):
    def __init__(self, mime_pattern, target, operators):
        self.mime_pattern = mime_pattern
        self.pattern = target
        self.operators = operators
        self.formatted = ''
        self.fallthrough = (operators.find('f') >= 0)

    def match(self, sf):
        if match_mime(self.mime_pattern, sf.type):
            try:
                self.formatted = self.pattern.format(**sf.metadata)
                return True
            except KeyError, IndexError: 
                return False
        
def match_mime(pattern, type):
    return bool( re.match( fnmatch.translate( pattern ), type[0] ) )

def is_comment(line):
    if line == '' or line[0] == '#': return True
    else: return False


def main():
    optparser = OptionParser()
    optparser.add_option("-r","--root", dest="root", metavar="DIR",
                         help="Specify a root component that will be removed from paths before pattern matching. Default action is to use the current working directory")
    optparser.add_option("-v","--verbose", dest="verbose", default=False, action='store_true',
                         help="Show lots of info about what is being done")
    optparser.add_option("-d","--debug", dest="debug", default=False, action='store_true',
                         help="Show debug info")

    global settings
    global args
    settings, args = optparser.parse_args()

    if os.name in ['nt', 'ce']:
        settings.no_linking = True

    if len(args) == 0:
        optparser.print_help();
        quit()

    if not settings.root:
        settings.root = os.getcwd()

    mimetypes.init(['mime.types'])
    fnparser = FilenameParser('filename-patterns.txt')
    rulefinder = RuleFinder('match-rules.txt')


    for filename in args:
        if not os.path.isfile(filename):
            raise IOError("Could not read file: '"+filename+"'")

    for filename in args:
        sourcefile = SourceFile(filename, fnparser)
        sourcefile.getMetadata()
        rules = rulefinder.getRules( sourcefile )
        sourcefile.applyRules( rules )

if __name__ == "__main__":
    main()
