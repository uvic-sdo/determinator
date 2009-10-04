import sys
from optparse import OptionParser
from ConfigParser import ConfigParser
import os
import os.path
import mimetypes 
import re
import fnmatch

class SourceFile(object):
    ''' This class represents a file to be determinated. It requires a valid 
    pathname and a FilenameParser object '''

    def __init__(self, filename, fnparser, metadata):
        self.fnparser = fnparser
        self.metadata = metadata
        self.filename = os.path.abspath(filename)
        self.type = mimetypes.guess_type(filename)
        if not self.type[0]:
            raise IOError("Unknown filetype for file '"+filename+"'")
        self.metadata['basename'] = os.path.basename(filename)
        self.linkable = (os.name not in ['nt','ce'])

    def getMetadata(self):
        ''' Extract metadata by calling FileParser.parseFile, and any 
        other valid extraction method '''
        self.metadata.update(self.fnparser.parseFile(self))
        if self.type[0] == 'audio/mpeg':
            print 'Extracting ID3 tags not implemented yet'

    def applyRules(self, rules):
        ''' Apply the provided set of rules to the file '''
        for rule in rules.sort():
            target = rule.format(self, True)
            for operator in rule.operators:
                if not self.linkable and operator in 'Ll':
                    print("Linking not possible on this platform")
                    continue

                if operator in 'MLS':
                    if not os.path.isdir(os.path.dirname(target)):
                        os.makedirs(os.path.dirname(target))

                if operator == 'M':
                    os.rename(self.filename, target)
                    self.filename = target
                elif operator == 'L':
                    try: os.link(self.filename, target)
                    except OSError: 
                        print("Creation of hardlink failed,",
                              "falling back to symlink")
                        operator = 'S'
                elif operator == 'S':
                    os.symlink(self.filename, target)

class RuleFinder(object):
    comment_regex = re.compile(r'\s*#|\s*$')
    def __init__(self, ruleclass):
        self.ruleclass = ruleclass
        self.ruleSet = []

    def loadRules(self, filename):
        ''' Scan a file for rules as defined by self.ruleclass '''
        with open(filename, 'r') as file:
            for n, line in enumerate(file, 1):
                line = line.strip()
                if self.is_comment(line): continue
                try:
                    rule = self.ruleclass(line)
                except ValueError: 
                    raise SyntaxError(filename + ':' + n
                                      + ': Invalid target rule: ' + line )
                self.ruleSet.append(rule)
        
    def is_comment(self, line):
        return bool(self.comment_regex.match(line))

    def getRules(self, sf):
        ''' Return a list of rules that apply to a given SourceFile 
        This will often return a list of a single item '''
        rules = []
        for rule in self.ruleSet:
            if rule.match(sf):
                rules.append(rule)
                if not (hasattr(rule, 'fallthrough') and rule.fallthrough): 
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

    def __eq__(self, other):
        return (self.fallthrough == other.fallthrough)

    def __gt__(self, other):
        return(other.fallthrough and not self.fallthrough)

def setup():
    optparser = OptionParser()
    optparser.usage = optparser.usage+' FILE [FILE FILE ...]'
    optparser.add_option("-r","--root", dest="root", metavar="DIR",
                         help="Specify a root component that will be removed \
                         from paths before pattern matching. Default action \
                         is to use the current working directory")
    optparser.add_option("-p","--patterns", dest="patterns", metavar="FILE",
                         help="Specify a file containing filename patterns \
                         for metadata extraction")
    optparser.add_option("-t","--targets", dest="targets", metavar="FILE",
                         help="Specify a file containing target patterns")
    optparser.add_option("-v","--verbose", dest="verbose", default=False, 
                         action='store_true',
                         help="Show lots of info about what is being done")
    optparser.add_option("-d","--debug", dest="debug", default=False,
                         action='store_true', help="Show debug info")

    options, filenames = optparser.parse_args()
    cfg = ConfigParser()
    cfg.read(os.path.expanduser('~/.config/determinator/determinator.rc'))

    if len(filenames) == 0:
        optparser.print_help();
        quit()

    if not options.root:
        try:
            options.root = cfg.get('Misc Options', 'root')
        finally:
            options.root = os.getcwd()

    mimetypes.init([os.path.dirname(__file__)+'/mime.types'])
    return options, filenames, cfg

def main():
    options, filenames, cfg = setup()
    fnparser = FilenameParser()
    targetfinder = RuleFinder(TargetRule)

    for filename in filenames:
        if not os.access(filename, os.F_OK & os.W_OK & os.R_OK):
            raise IOError("Insufficient permissions on file: '"+filename+"'")

    if options.patterns:
        fnparser.getRules(options.patterns)

    if options.targets:
        targetfinder.getRules(options.targets, gMetadata)

    for filename in cfg.get('Rule Files','targets').split(';'):
        targetfinder.getRules(filename)

    for filename in cfg.get('Rule Files','patterns').split(';'):
        fnparser.getRules(filename)

    static_metadata = {}
    for key in cfg.options('Global Metadata'):
        static_metadata[key] = cfg.get('Global Metadata', key)

    for filename in filenames:
        sourcefile = SourceFile(filename, fnparser, linking, static_metadata)
        sourcefile.getMetadata()
        targets = targetfinder.getRules(sourcefile)
        sourcefile.applyRules(targets)

if __name__ == "__main__":
    main()
