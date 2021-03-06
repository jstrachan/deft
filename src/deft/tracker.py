
import os
from glob import iglob
from deft.indexing import Bucket
from deft.storage import FileStorage

FormatVersion = '2.0'

ConfigDir = ".deft"
ConfigFile = os.path.join(ConfigDir, "config")
DefaultDataDir = os.path.join(ConfigDir, "data")

PropertiesSuffix = ".status"
DescriptionSuffix = ".description"

# Used to report user errors that have been explicitly detected
class UserError(Exception):
    pass


def default_config(datadir=DefaultDataDir, initial_status="new"):
    return {
        'format': FormatVersion,
        'datadir': datadir,
        'initial_status': initial_status}

def init_tracker(**config_overrides):
    return init_with_storage(FileStorage(os.getcwd()), config_overrides)


def tracker_storage():
    #TODO: find a tracker in the ancestor directories
    return FileStorage(os.getcwd())

def load_tracker():
    return load_with_storage(tracker_storage())

def init_with_storage(storage, config_overrides):
    if storage.exists(ConfigDir):
        raise UserError("tracker already initialised in directory " + ConfigDir)
    
    tracker = FeatureTracker(default_config(**config_overrides), storage)
    tracker.save_config()
    
    return tracker

def load_with_storage(storage):
    return FeatureTracker(load_config_with_storage(storage), storage)

def load_config_with_storage(storage):
    if not storage.exists(ConfigDir):
        raise UserError("tracker not initialised")
    
    return storage.load_yaml(ConfigFile)
    


class FeatureTracker(object):
    def __init__(self, config, storage):
        repo_format = config['format']
        if repo_format != FormatVersion:
            raise UserError("incompatible tracker: found data in format version %s, " \
                            "requires data in format version %s"%(repo_format, FormatVersion))
        
        self.config = config
        self.storage = storage
        self._init_empty_cache()
    
    def configure(self, **config):
        self.config.update(config)
        self.save_config()
    
    @property
    def initial_status(self):
        return self.config['initial_status']
    
    def save_config(self):
        self.storage.save_yaml(ConfigFile, self.config)
    
    def save(self):
        for feature in self._dirty:
            self._save_feature(feature)
        self._init_empty_cache()
    
    def _init_empty_cache(self):
        self._dirty = set()
        self._loaded = {}
    
    def create(self, name, status=None, description=""):
        if self._feature_exists_named(name):
            raise UserError("a feature already exists with name: " + name)
        
        if status is None:
            status = self.initial_status
        
        priority = len(self._load_features_with_status(status)) + 1
        
        feature = Feature(tracker=self, name=name, status=status, priority=priority)
        
        self._loaded[self._name_to_path(name)] = feature
        self._save_feature(feature)
        feature.write_description(description)
        
        return feature
    
    def feature_named(self, name):
        if self._feature_exists_named(name):
            return self._load_feature(self._name_to_path(name))
        else:
            raise UserError("no feature named " + name)
    
    def features_with_status(self, status):
        return Bucket(self._load_features_with_status(status))
    
    def all_features(self):
        return sorted(self._load_features(), key=lambda f: (f.status, f.priority))
    
    def purge(self, name):
        properties_path = self._name_to_path(name, PropertiesSuffix)
        description_path = self._name_to_path(name, DescriptionSuffix)
        
        feature = self._load_feature(properties_path)
        bucket = self.features_with_status(feature.status)
        
        bucket.remove(feature)
        
        del self._loaded[properties_path]
        self._dirty.discard(feature)
        
        self.storage.remove(properties_path)
        self.storage.remove(description_path)
    
    
    def change_status(self, feature, new_status):
        old_bucket = self.features_with_status(feature.status)
        new_bucket = self.features_with_status(new_status)
        
        old_bucket.remove(feature)
        new_bucket.append(feature)
        feature.status = new_status
    
    
    def change_priority(self, feature, new_priority):
        bucket = self.features_with_status(feature.status)
        bucket.change_priority(feature, new_priority)
    
    def _feature_exists_named(self, name):
        return self.storage.exists(self._name_to_path(name))
    
    def _load_features_with_status(self, status):
        return [f for f in self._load_features() if f.status == status]
    
    def _load_features(self):
        return [self._load_feature(f) for f in self.storage.list(self._name_to_path("*"))]
    
    def _load_feature(self, path):
        if path in self._loaded:
            return self._loaded[path]
        else:
            text = self.storage.load_text(path)
            priority = int(text[0:8])
            status = text[9:]
            feature = Feature(tracker=self, name=self._path_to_name(path), status=status, priority=priority)
            self._loaded[path] = feature
            return feature
    
    def _mark_dirty(self, feature):
        self._dirty.add(feature)
    
    def _save_feature(self, feature):
        self.storage.save_text(self._name_to_path(feature.name), 
                               _format_status(feature.status, feature.priority))
    
    def _name_to_path(self, name, suffix=PropertiesSuffix):
        return os.path.join(self.config["datadir"], name + suffix)
    
    def _path_to_name(self, path, suffix=PropertiesSuffix):
        return os.path.basename(path)[:-len(suffix)]
    
    def _name_to_real_path(self, name, suffix=PropertiesSuffix):
        return self.storage.abspath(self._name_to_path(name, suffix))


_format_status = "{1:>8} {0}".format


class Feature(object):
    def __init__(self, tracker, name, status, priority):
        self.name = name
        self.status = status
        self.priority = priority
        self._tracker = tracker
    
    def __setattr__(self, name, new_value):
        must_save = hasattr(self, '_tracker')
        object.__setattr__(self, name, new_value)
        if must_save:
            self._tracker._mark_dirty(self)
    
    @property
    def description_file(self):
        return self._tracker._name_to_real_path(self.name, DescriptionSuffix)
    
    def open_description(self, mode="r"):
        return self._tracker.storage.open(self._tracker._name_to_path(self.name, DescriptionSuffix), mode)
    
    def write_description(self, new_description):
        with self.open_description("w") as output:
            output.write(new_description)
    
    def __str__(self):
        return self.__str__()
    
    def __repr__(self):
        return self.__class__.__name__ + "(name=" + self.name + ")"



