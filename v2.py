class Pathname():
     def __init__ (self, path, parent=None):
         self.path = path
         self.parent = parent
         self.analyze()
