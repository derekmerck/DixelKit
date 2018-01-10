# DixelKit

Derek Merck <derek_merck@brown.edu>  
Winter 2018

<https://www.github.com/derekmerck/DixelKit>

DICOM image objects may be represented in _many_ different ways across
[DIANA](https//www.github.com/derekmerck/DIANA)):  as `.dcm` files, as URLs 
in [Orthanc][], as tag data in [Splunk][].  A range of data and metadata, 
including pixels, text reports, and procedure variables may be associated
with studies. And study data may be built-up incrementally from multiple
sources, creating incomplete DICOM-like structures.

[Orthanc]: http://www.orthanc-server.com
[Splunk]:  http://www.splunk.com

DixelKit is a more generic and accessible toolkit for working with collections
of such medical imaging related data and metadata.

Dixel is a portmanteau for a "DICOM element" (or "DIANA element", a la pixel
or voxel.) Pre-dixels are incomplete dixels, usually without enough information
to assign a unique orthanc-style id.  

A DixelStorage is an inventory of dixels that supports CRUD access (put, 
read/get/copy, update, delete).  Implemented DixelStorages include: `.dcm` files,
Orthanc (open source PACS), Splunk (meta data index), and Montage (report text)


## Instalation

`$ pip install http://github.com/derekmerck/DixelKit`

or 

`$ git clone http://github.com/derekmerck/DixelKit`


### Python package requirements

- [pydicom](http://pydicom.readthedocs.io/en/stable/getting_started.html)
- [python-dateutil](https://dateutil.readthedocs.io/en/stable/)
- [pyyaml](https://pyyaml.org)
- [python-magic](https://github.com/ahupp/python-magic)
- [requests](http://docs.python-requests.org/en/master/)
- [splunk-sdk](http://dev.splunk.com/python)
- [aenum](https://bitbucket.org/stoneleaf/aenum)


### External requirements

- [Grassroots DICOM][] (`gdcm`) for DICOM file pixel compression  
  `brew install gdcm` on OSX  
  `apt-get install gcdm` on Debian **
- File magic (`libmagic`) for file typing  
  `brew install libmagic` on OSX  (typically pre-installed on Linux)

[Grassroots DICOM]: http://gdcm.sourceforge.net/wiki/index.php/Main_Page

## Usage

See `tests.py` for more examples.

### Lazy copy from FileStorage

```python
>>> file_dir = FileStorage( 'my/dicom/dir' )
>>> orthanc = Orthanc( 'localhost' )
>>> count = file_dir.copy_inventory(orthanc)
>>> assert( count > 0 )
>>> count = file_dir.copy_inventory(orthanc, lazy=True)
>>> assert( count == 0 )
```

### JPG2K compression on copy from FileStorage

```python
>>> file_dir = FileStorage( 'my/dicom/dir' )
>>> orthanc = Orthanc( 'localhost' )
>>> file_dir.copy_inventory(orthanc)
>>> size = orthanc.statistics()['DiskSizeMB']
>>> orthanc.remove_inventory()
>>> orthanc.prefer_compressed = True
>>> file_dir.copy_inventory(orthanc)
>>> size_z = orthanc.statistics()['DiskSizeMB']
>>> assert( size_z < size )
```

### Lazy upload metadata to Splunk from Orthanc

```python
>>> orthanc = Orthanc( 'localhost' )
>>> splunk = Splunk( 'localhost', 8089, 'user', 'passw0rd' )
>>> orthanc.copy_inventory( splunk, lazy=True )
```

### Lookup Studies and Create a Research Archive

```python
>>> csv_text = """
PatientID, DateOfService, Procedure
ABC,       01012000,      CT Angiogram"""
>>> worklist = DixelUtils.load_csv(csv_text)
>>> splunk.update(worklist)   # Get accession numbers, orthanc id's
>>> montage.update(worklist)  # Add report text
>>> DixelUtils.save_csv('my_project.csv')
>>> orthanc.copy(worklist, Orthanc('my_project_host') )
```

### Storage Instantiation with Text Secrets

```python
secret_yaml="""
host: localhost
port: 8042
user: username
password: passw0rd
"""
>>> credentials = yaml.load(secret_yaml)
>>> orthanc = Orthanc(credentials)
```


## License

MIT

---

** GDCM has no rpm available for RedHat 6, but can be compiled following <http://gdcm.sourceforge.net/wiki/index.php/Compilation> and <https://raw.githubusercontent.com/malaterre/GDCM/master/INSTALL.txt>
```bash
$ yum install cmake3 g++
$ git clone https://github.com/malaterre/GDCM
$ cd GDCM
$ mkdir build
$ cd build
$ cmake3 -D GDCM_BUILD_APPLICATIONS=true ..
$ make
$ make install
```

