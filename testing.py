import logging
from DixelKit.DixelStorage import CachePolicy
from DixelKit.FileStorage import FileStorage
from DixelKit.Orthanc import Orthanc, OrthancProxy
from DixelKit.Montage import Montage
from DixelKit.Splunk import Splunk
from DixelKit import DixelTools

def test_mirror():

    # Caches by default
    file_dir = FileStorage("/users/derek/Desktop/Protect3/80", cache_policy=CachePolicy.USE_CACHE)
    assert( len(file_dir.inventory) == 118 )

    # No caching by default
    orthanc = Orthanc('localhost', 8042)
    orthanc.delete_inventory()
    assert( len(orthanc.inventory) == 0)

    # Upload whatever is missing
    copied = file_dir.copy_inventory(orthanc)
    logging.debug(copied)
    assert( copied == 118 )

    # Upload whatever is missing
    copied = file_dir.copy_inventory(orthanc, lazy=True)
    logging.debug(copied)
    assert( copied == 0 )

    # At this point, the original attachment is MOOT, I believe


def test_pacs_lookup():

    splunk = Splunk()
    archive = Orthanc()
    proxy = OrthancProxy('localhost', 8042, remote="remote_aet")
    dest = Orthanc('localhost', 8042)
    montage = Montage()

    # No AccessionNumber yet, so we have to uniquify by mrn+time
    worklist = DixelTools.load_csv(csv_file="/Users/derek/Desktop/elvos3.csv",
                                   secondary_id="Treatment Time")

    splunk.update_worklist(worklist)       # Find indexed studies on source, update id's
    archive.copy_worklist(dest, worklist)

    proxy.update_worklist(worklist)        # Find other studies on PACS, update id's
    proxy.copy_worklist(worklist, dest)

    # worklist.update(montage)

    DixelTools.save_csv(csv_file="/Users/derek/Desktop/elvos3-out.csv")


if __name__=="__main__":

    logging.basicConfig(level=logging.DEBUG)

    test_mirror()
    # test_pacs_lookup()
