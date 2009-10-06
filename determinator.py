#/usr/bin/env python
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

    def __init__(self, filename, fnparser=None, metadata={}):
        if fnparser:
            self.fnparser = fnparser
        else:
            self.fnparser = FilenameParser();
        self.metadata = metadata
        self.filename = os.path.abspath(filename)
        self.type = mimetypes.guess_type(filename)
        if not self.type[0]:
            raise IOError("Unknown filetype for file '"+filename+"'")
        self.metadata['basename'] = os.path.basename(filename)
        self.linkable = (os.name not in ['nt','ce'])

    def get_metadata(self):
        ''' Extract metadata by calling FileParser.parse_file, and any 
        other valid extraction method '''
        self.metadata.update(self.fnparser.parse_file(self))
        if self.type[0] == 'audio/mpeg':
            print 'Extracting ID3 tags not implemented yet'

    def apply_rules(self, rules):
        ''' Apply the provided set of rules to the file '''
        symlinks = []
        for rule in rules:
            target = rule.format(self, True)
            for operator in rule.operators:
                if not self.linkable and operator in 'Ll':
                    print("Linking not possible on this platform")
                    continue

                if operator in 'MLS':
                    if not os.path.isdir(os.path.dirname(target)):
                        os.makedirs(os.path.dirname(target))

                if operator == 'L':
                    try: os.link(self.filename, target)
                    except OSError: 
                        print("Creation of hardlink failed,",
                              "falling back to symlink")
                        operator = 'S'
                elif operator == 'S':
                    os.symlink(self.filename, target)
                    symlinks.append(target)
                elif operator == 'M':
                    os.rename(self.filename, target)
                    self.filename = target
                    for sl in symlinks:
                        os.unlink(sl)
                        os.symlink(self.filename, sl)

class RuleFinder(object):
    comment_regex = re.compile(r'\s*#|\s*$')
    def __init__(self, rule_cls, rule_file=None):
        self.rule_cls = rule_cls
        self.rule_set = []
        if rule_file: self.add_rules(rule_file)

    def add_rules(self, files):
        ''' Scan a file (or list of files) for rules. Lines must have the 
        format required by self.rule_cls '''
        if type(files) == type(''): files = [files]
        for file in files:
            try:
                file = open(filename, 'r')
                for n, line in enumerate(file, 1):
                    line = line.strip()
                    if self.is_comment(line): continue
                    try:
                        rule = self.rule_cls(line)
                    except ValueError: 
                        raise SyntaxError(filename + ':' + n
                                          + ' - Invalid target rule: ' + line )
                    self.rule_set.append(rule)
            finally:
                file.close()
        
    def is_comment(self, line):
        return bool(self.comment_regex.match(line))

    def get_rules(self, sf):
        return RuleIter(self.rule_set, sf)

class RuleIter():
    def __init__(self, rules, sf):
        self.sf = sf
        self.rules = filter(self.check, rules)
        self.fallthrough = True

    def __iter__(self):
        return self

    def next(self):
        if not self.fallthrough:
            raise StopIteration
        rule = next(self.rules)
        self.fallthrough = (hasattr(rule, 'fallthrough') and rule.fallthrough) 
        return rule
        
    def check(self,rule):
        return rule.match(self.sf)
        

class FilenameParser(RuleFinder):
    def __init__(self, rule_file=None):
        RuleFinder.__init__(self, FilenameParseRule, rule_file)

    def parse_file(self, sf):
        ''' Parse the filename of the provided SourceFile '''
        for rule in self.get_rules(sf):
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
        self.mime_pattern, self.target, self.operators \
          = re.split('\t\s*', line)
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
                         help="Specify a file containing target rules")
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
    for filename in filenames:
        if not os.access(filename, os.F_OK & os.W_OK & os.R_OK):
            raise IOError("Insufficient permissions on file: '"+filename+"'")

    fnparser = FilenameParser()
    targetfinder = RuleFinder(TargetRule)

    if options.patterns:
        fnparser.get_rules(options.patterns.split(','))

    if options.targets:
        targetfinder.add_rules(options.targets.split(','))

    targetfinder.add_rules()
    fnparser.add_rules(cfg.get('Rule Files','patterns').split(','))

    static_metadata = {}
    for key in cfg.options('Global Metadata'):
        static_metadata[key] = cfg.get('Global Metadata', key)

    for filename in filenames:
        sourcefile = SourceFile(filename, fnparser, linking, static_metadata)
        sourcefile.getMetadata()
        targets = targetfinder.get_rules(sourcefile)
        sourcefile.apply_rules(targets)

if __name__ == "__main__":
    main()
