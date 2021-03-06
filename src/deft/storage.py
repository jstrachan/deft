
import os
import shutil
from glob import iglob
import yaml


class StorageFormats(object):
    def save_yaml(self, relpath, obj):
        with self.open(relpath, "w") as output:
            yaml.dump(obj, output, default_flow_style=False)
    
    def load_yaml(self, relpath):
        with self.open(relpath) as input:
            return yaml.safe_load(input)
    
    def save_text(self, relpath, text):
        with self.open(relpath, "w") as output:
            output.write(text)
            
    def load_text(self, relpath):
        with self.open(relpath) as input:
            return input.read()


class FileStorage(StorageFormats):
    def __init__(self, basedir):
        self.basedir = basedir
    
    def abspath(self, relpath):
        return os.path.normpath(os.path.join(self.basedir, relpath))
    
    def exists(self, relpath):
        return os.path.exists(self.abspath(relpath))
    
    def open(self, relpath, mode="r"):
        if mode == "w":
            self.makedirs(os.path.dirname(relpath))
        
        return open(self.abspath(relpath), mode)
    
    def remove(self, relpath):
        path = self.abspath(relpath)
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.exists(path):
            os.remove(path)
    
    def list(self, relpattern):
        pattern = self.abspath(relpattern)
        return (os.path.relpath(match, start=self.basedir) for match in iglob(pattern))
    
    def makedirs(self, relpath):
        if relpath != "":
            dirpath = self.abspath(relpath)
            if not os.path.exists(dirpath):
                os.makedirs(dirpath)

