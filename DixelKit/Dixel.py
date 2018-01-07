from aenum import Enum, auto, IntEnum
class DicomLevel(Enum):
    INSTANCE = auto()
    SERIES = auto()
    STUDY = auto()
    PATIENT = auto()

    def __str__(self):
        return '{0}'.format(self.name.lower())


class Dixel(object):

    def __init__(self,  id,
                        tags = None,
                        meta = None,
                        data = None,
                        level = DicomLevel.INSTANCE):

        self.id    = id            # orthanc-type id
        self.tags  = tags or {}    # Simplified tags per orthanc
        self.meta  = meta or {}    # ParentID, file_uuid, path, ApproxDate, other info
        self.data  = data or {}    # Binary data, pixels, report text
        self.level = level
        self.parent = None         # Instances may have series parents, series may have study parents
        self.children = []         # Studies have series children, series have instance children


    # Helpers to make dixels printable, hashable, and sortable for set operations
    def __repr__(self):
        return self.id[0:4]

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return self.id == other.id

    def __lt__(self, other):
        return self.id < other.id
