# DixelKit
#
# Derek Merck, Winter 2018
#
# DICOM image objects may be represented in _many_ different ways across DIANA:
# as .dcm files, as URLs in Orthanc, as tag data in Splunk.  A range of metadata
# including text reports or procedure variables may be associated with studies. And
# study data may be built incrementally from multiple sources.
#
# Thus, a more generic and accessible toolkit for working with collections of medical
# imaging related data was required.
#
# Dixel is a portmanteau for a "DICOM element" (or "DIANA element", a la pixel or voxel.)
#
# A DixelStore is an inventory of dixels that supports CRUD access.

from DixelKit.FileStorage import FileDirectory





def test_mirror():

    # Caches by default
    file_dir = FileDirectory("/users/derek/Desktop/Protect3/80")

    # No caching by default
    orthanc = Orthanc('localhost', 8042)

    # Upload whatever is missing
    file_dir.copy_inventory(orthanc, lazy=True)

    # At this point, the original attachment is MOOT, I believe


def test_pacs_lookup():

    splunk = DixelStore()
    archive = Orthanc()
    proxy = OrthancProxy('localhost', 8042, remote="remote_aet")
    dest = Orthanc('localhost', 8042)
    montage = DixelStore()

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
