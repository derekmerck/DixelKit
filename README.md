# DixelKit


 DixelKit
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

J2K Transfer Syntax:  1.2.840.10008.1.2.4.90

``````
DIANA
 |-- Services
 |
 |-- Connect
 |
 |-- Manager
 |    |-- TrialFrontEnd (TFE)
 |
 |-- Apps
      |-- Rad_Rx
      |-- Inspector
```

