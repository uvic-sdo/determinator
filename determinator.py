import os.path
import sys
import getopt
import mimetypes 
import re
import fnmatch
from optparse import OptionParser
from ConfigParser import ConfigParser

class SourceFile(object):
    ''' This class represents a file to be determinated. It requires a valid 
    pathname and a FilenameParser object '''

    def __init__(self, filename, fnparser):
        self.fnparser = fnparser
        self.filename = os.path.abspath(filename)
        self.type = mimetypes.guess_type(filename)
        if not self.type[0] or self.type[0].split('/')[0] not in ['audio', 'video']:
            raise IOError("Unsupported filetype in file '"+filename+"'")
        self.metadata = {'basename': os.path.basename(filename)} 
        for option in CONFIG.options('Global Metadata'):
            self.metadata[option] = CONFIG.get('Global Metadata', option)

    def getMetadata(self):
        ''' Extract metadata by calling FileParser.parseFile, and any 
        other valid extraction method '''
        self.metadata.update(self.fnparser.parseFile(self))
        if self.type[0] == 'audio/mpeg':
            print 'Extracting ID3 tags not implemented yet'

    def applyRules(self, rules):
        ''' Apply the provided set of rules to the file '''
        for rule in rules:
            target = rule.format(self, True)
            for operator in rule.operators:
                if OPTIONS.no_linking and operator in 'Ll':
                    print("Linking not possible on this platform")
                    continue

                if operator in 'MLS':
                    if not os.path.isdir(os.path.dirname(target)):
                        os.makedirs(os.path.dirname(target))

                if operator == 'M':
                    os.rename(self.filename, target)
                    self.filename = target
                elif operator == 'L':
                    # FIXME - Check filename and target are on same filesystem
                    try: os.link(self.filename, target)
                    except OSError: 
                        print("Creation of cross-device hardlink failed,",
                              "falling back to symlink")
                        operator = 'S'
                elif operator == 'S':
                    os.symlink(self.filename, target)

class RuleFinder(object):
    def __init__(self, ruleclass):
        self.ruleclass = ruleclass
        self.ruleSet = []

    def loadRules(self, filename):
        with open(filename, 'r') as file:
            n = 1
            for line in file:
                line = line.strip()
                if self.is_comment(line): continue
                try:
                    rule = self.ruleclass(line)
                except ValueError: 
                    raise SyntaxError(filename + ':' + n
                                      + ': Invalid target rule: ' + line )
                self.ruleSet.append(rule)
                n += 1
        
    def is_comment(self, line):
        regex = re.compile(r'\s*#|\s*$')
        return bool(regex.match(line))

    def getRules(self, sf):
        ''' Return a list of rules that apply to a given SourceFile 
        This will often return a list of a single item '''
        rules = []
        for rule in self.ruleSet:
            if rule.match(sf):
                rules.append(rule)
                if not hasattr(rule, 'fallthrough') or not rule.fallthrough: 
                    break
        return rules

class FilenameParser(RuleFinder):
    def __init__(self):
        RuleFinder.__init__(self, FilenameParseRule)

    def parseFile(self, sf):
        ''' Parse the filename of the provided SourceFile '''
        for rule in self.getRules(sf):
            sf.metadata.update(rule.parse(sf))
        return {}

class MimeRule(object):
    def match(self, sf):
        if self.match_mime(self.mime_pattern, sf):
            if hasattr(self, 'match_rule'):
                return self.match_rule(sf)
            else:
                return True
        else:
            return False

    def match_mime(self, pattern, sf):
        return bool(re.match(fnmatch.translate(pattern), sf.type[0]))

class FilenameParseRule(MimeRule):
    def __init__(self, line):
        self.mime_pattern, regex = re.split('\t\s*', line)
        self.regex = re.compile(regex.replace('/',str(os.path.sep)[1:-1]))

    def match_rule(self, sf):
        return bool(self.regex.search(sf.filename))

    def parse(self, sf):
        return self.regex.search(sf.filename).groupdict()
        
class TargetRule(MimeRule):
    def __init__(self, line):
        self.mime_pattern, self.target, self.operators = re.split('\t\s*', line)
        self.fallthrough = (self.operators.find('f') >= 0)

    def format(self, sf, force=False):
        return self.target.format(**sf.metadata)

    def match_rule(self, sf):
        try:
            self.target.format(**sf.metadata)
            return True
        except KeyError, IndexError: 
            return False

def get_options():
    global OPTIONS
    global ARGS
    global CONFIG
    optparser = OptionParser()
    optparser.usage = optparser.usage+' FILE [FILE FILE ...]'
    optparser.add_option("-r","--root", dest="root", metavar="DIR",
                         help="Specify a root component that will be removed from paths before pattern matching. Default action is to use the current working directory")
    optparser.add_option("-p","--patterns", dest="patterns", metavar="FILE",
                         help="Specify a file containing filename patterns for metadata matching")
    optparser.add_option("-t","--targets", dest="targets", metavar="FILE",
                         help="Specify a file containing target patterns")
    optparser.add_option("-v","--verbose", dest="verbose", default=False, action='store_true',
                         help="Show lots of info about what is being done")
    optparser.add_option("-d","--debug", dest="debug", default=False, action='store_true',
                         help="Show debug info")

    OPTIONS, ARGS = optparser.parse_args()

    CONFIG = ConfigParser()
    CONFIG.read(os.path.expanduser('~/.config/determinator/determinator.rc'))

    OPTIONS.no_linking = (os.name in ['nt', 'ce'])

    if len(ARGS) == 0:
        optparser.print_help();
        quit()

    if not OPTIONS.root:
        try:
            OPTIONS.root = CONFIG.get('Misc Options', 'root')
        except:
            OPTIONS.root = os.getcwd()



def main():
    get_options()
    mimetypes.init([os.path.dirname(__file__)+'/mime.types'])
    fnparser = FilenameParser()
    targetfinder = RuleFinder(TargetRule)

    for filename in ARGS:
        if not os.access(filename, os.F_OK & os.W_OK & os.R_OK):
            raise IOError("Insufficient permissions on file: '"+filename+"'")

    if OPTIONS.patterns:
        fnparser.getRules(OPTIONS.patterns)

    if OPTIONS.targets:
        targetfinder.getRules(OPTIONS.targets)

    for filename in CONFIG.get('Rule Files','targets').split(';'):
        targetfinder.getRules(filename)

    for filename in CONFIG.get('Rule Files','patterns').split(';'):
        fnparser.getRules(filename)

    for filename in ARGS:
        sourcefile = SourceFile(filename, fnparser)
        sourcefile.getMetadata()
        rules = targetfinder.getRules(sourcefile)
        sourcefile.applyRules(rules)

if __name__ == "__main__":
    main()
