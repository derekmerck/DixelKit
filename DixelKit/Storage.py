import pickle
import os
import logging
from Dixel import *


class CachePolicy(IntEnum):
    NONE = 0
    USE_CACHE = 1
    CLEAR_AND_USE_CACHE = 2


class DixelStore(object):
    # A collection of Dixels on disk, in Orthanc, on a PACS, in Splunk...

    def __init__(self,
                 cache_pik=None,
                 cache_policy=CachePolicy.NONE):
        self.logger = logging.getLogger()
        self.cache = {}
        self.cache_pik = cache_pik
        self.cache_policy = cache_policy

        if cache_pik and cache_policy == CachePolicy.CLEAR_AND_USE_CACHE:
            if os.path.exists(self.cache_pik):
                os.remove(self.cache_pik)

    # Abstract methods -- implement these to extend
    def put(self, dixel):
        raise NotImplementedError

    def get(self, dixel):
        raise NotImplementedError

    def delete(self, dixel):
        raise NotImplementedError

    def copy(self, dixel, destination):
        raise NotImplementedError

    def update(self, dixel):
        raise NotImplementedError

    # Anything that you want to cache can be accessed with a "var" property
    # and an "initialize_var()" method that _returns_ an appropriate value
    @property
    def inventory(self):
        return self.check_cache('inventory')

    def initialize_inventory(self):
        # Return the completed inventory
        raise NotImplementedError

    # Generic functions
    def update_worklist(self, worklist):
        res = set()
        for dixel in worklist:
            u = self.update(dixel)
            if u:
                res.add(u)
        return res


    def check_cache(self, item):

        # Uninitialized cache
        if not self.cache:
            self.load_cache()

        # Uninitialized item
        if not self.cache.get(item):
            self.cache[item] = self.initialize_cache(item)
            self.save_cache()

        return self.cache.get(item)

    def initialize_cache(self, item):
        method_name = 'initialize_{0}'.format(item)
        # self.logger.debug('Calling method {}'.format(method_name))
        try:
            method = getattr(self, method_name)
        except AttributeError:
            raise NotImplementedError(
                "Class `{}` does not implement `{}`".format(self.__class__.__name__, method_name))
        return method()

    # File inventories in particular can be expensive to compute
    def save_cache(self):
        if self.cache_policy > 0 and self.cache_pik:
            with open(self.cache_pik, 'wb') as f:
                pickle.dump(self.cache, f)

    def load_cache(self):
        if self.cache_policy > 0 and self.cache_pik and os.path.exists(self.cache_pik):
            with open(self.cache_pik, 'rb') as f:
                self.cache = pickle.load(f)

    def view_inventory(self):
        logging.info(sorted(self.inventory))

    def copy_inventory(self, dest, lazy=False):
        worklist = self.inventory
        self.copy_worklist(dest, worklist, lazy)

    def copy_worklist(self, dest, worklist, lazy=False):

        if lazy:
            logging.debug("All:  {0} dixels\n   {1}".format(len(worklist), sorted(worklist)))
            worklist = worklist - dest.inventory
            logging.debug("Lazy: {0} dixels\n   {1}".format(len(worklist), sorted(worklist)))

        for dixel in worklist:
            self.copy(dixel, dest)