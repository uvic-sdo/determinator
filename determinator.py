import os.path
import sys
import mimetypes
import re
#import configparser
mimetypes.init('mime.types')

class SourceFile(object):
    ''' This class represents a file to be determinated. It requires a valid 
    pathname and an FilenameParser object '''

    def __init__(self, filename, fnparser):
        '''
        '''        
        if not os.path.isfile(filename):
            raise IOError("Could not read file: '"+filename+"'")
        self.fnparser = fnparser
        self.filename = os.path.abspath(filename)
        self.type = mimetypes.guess_type(filename)
        if not self.type[0] or self.type[0].split('/')[0] not in ['audio', 'video']:
            raise IOError("Unsupported filetype in file '"+filename+"', type: '"+self.type[0]+"'")
        self.metadata = {} # It might be wise to have globally available metadata defined here, e.g. 'video_root' defining a base directory for all videos

    def getMetadata(self):
        ''' Extract metadata by calling FileParser.parse, and any other valid
        extraction method '''
        self.metadata = self.fnparser.parse(self)
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

class FilenameParser(object):
    def __init__(self, pattern_file, root=None):
        file = open(pattern_file, 'r')
        self.patterns = [self.readline(line) for line in real_lines(file) if line != None]
        file.close()
        self.root = root or ''

    def readline(self, line):
        try: mime_pattern, regex = re.split('\t+', line)
        except: return None
        regex = regex.strip()
        del line
        return locals()

    def parse(self, sf):
        ''' Parse the given filename using filename patterns read in from rules file '''
        for p in self.patterns:
            if mime_match(p['mime_pattern'],type):
                regex = re.compile(p['regex'])
                match = regex.search( sf.filename.replace(self.root,'') )
                if match:
                    return match.groupdict()
        return {}

class TargetRuleSet(object):
    def __init__(self, filename):
        file = open(filename, 'r')
        self.patterns = [self.readline(line) for line in real_lines(file) if line != None]
        file.close()
        
    def readline(self, line):
        try: mime_pattern, target, operators = re.split('\t\s*', line)
        except: return None
        del line
        return locals()

    def getRules(self, metadata):
        ''' Find matching rules for the given metadata in the target rules file '''
        rules = []
        for p in self.patterns:
            if match_mime(p['mime_pattern'], type):
                try: target = p['target'].format(**metadata)
                except KeyError, IndexError: continue
                rules.append((target, p['operators']))
                if p['operators'].find('f') < 0: break
        return rules

def match_mime(pattern, type):
    return bool( re.match(fnmatch.translate(pattern), type[0]))

def real_lines(list):
    return [line.strip() for line in list if not comment(line)]

def comment(line):
    if line == '' or line[0] == '#': return True

if __name__ == "__main__":
    #FIXME - This will be a config variable later
    root = os.getcwd()

    try: filename = sys.argv[1]
    except:
        print("No filename provided")
        quit()

    fnparser = FilenameParser('filename-patterns.txt', root)
    rules = TargetRuleSet('match-rules.txt')

    if os.name in ['nt', 'ce']:
        linking_disabled = True
    sourcefile = SourceFile(filename, fnparser)
    sourcefile.getMetadata()
    sourcefile.applyRules( rules.getRules( sourcefile.metadata ) )
