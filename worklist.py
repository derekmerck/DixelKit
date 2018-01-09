"""
Given a worklist with PatientID and ReferenceTime:

1. Find ANs with thin data available in the CIRR
2. Find ANs with reports available in Montage
3. Find ANs with thick data available in the PACS
4. Update the worklist with "AccessionNumber", "Report", and "ID"
5. Copy thins if available, or thicks from CIRR or PACS to target repo
6. Anonymize if requested
"""

import csv
from DixelKit.DixelTools import daterange
import logging
from pprint import pformat

from api.Splunk import Splunk
from api.Orthanc import Orthanc
from api.Montage import Montage

class Worklist(object):

    def __init__(self,
                 fn=None,
                 delta=None):

        self.delta = delta

        # items is an array of dictionaries
        self.items = []
        if fn:
            # Populate self.items from csv file
            with open(fn, 'rU') as fp:
                items = csv.DictReader(fp)
                for item in items:
                    self.items.append(item)

        self.logger = logging.getLogger("Worklist")

    def output(self, fn):

        with open(fn, "w") as fp:

            fieldnames=set()
            for item in self.items:
                fieldnames.update(item.keys())

            writer = csv.DictWriter(fp,
                                    fieldnames=fieldnames,
                                    extrasaction='ignore')
            writer.writeheader()
            writer.writerows(self.items)


    def update(self, source, **kwargs):

        if type(source) == Orthanc and kwargs.get("remote"):
            # Proxy for a PACS search

            for item in self.items:
                remote = kwargs.get("remote")
                retrieve = kwargs.get('retrieve', False)

                if not item.get("OID"):
                    # run a PACS search for this study

                    study_date = kwargs.get('study_date', '')
                    study_time = kwargs.get('study_time', '')
                    modality = kwargs.get('modality', 'CT')
                    accession_number = kwargs.get('accession_number', '')
                    stuid = kwargs.get('stuid', '')

                    q = source.query_remote(remote, query={'StudyInstanceUID': stuid,
                                                           'StudyDate': study_date,
                                                           'StudyTime': study_time,
                                                           'AccessionNumber': accession_number,
                                                           'ModalitiesInStudy': modality})

                    return q

        if type(source) == Montage:

            qdict = kwargs.get("qdict", {})

            for item in self.items:

                patient_id = item['PatientID']
                earliest, latest = daterange(item['ReferenceTime'], self.delta)

                q = patient_id
                if item.get("AccessionNumber"):
                    q = q + "+" + item["AccessionNumber"]

                qdict["q"] = q
                qdict["start_date"] = earliest
                qdict["end_date"] = latest

                r = montage.query(qdict)

                if r:
                    self.logger.debug(pformat(r))
                    data = None

                    existing_an = item.get("AccessioNumber")
                    if existing_an:
                        # Check and see if there is a match in r
                        found = False
                        for r_item in r:
                            if r_item["accession_number"] == existing_an:
                                # Use this data
                                data = r_item
                                found = True
                                break
                        if found == False:
                            raise Exception("Can't find an {0} in results!".format(existing_an))
                    else:
                        data = r[0]
                        item["AccessionNumber"]=data["accession_number"]

                    item["MID"] = data["id"]                     # Montage ID
                    item["Report"] = data['text']                # Report text
                    item["ExamCode"] = data['exam_type']['code'] # IMG code


        if type(source) == Splunk:

            index = kwargs.get("index", "dicom_series")
            desc = kwargs.get("desc", "*")

            for item in self.items:
                logging.debug(item)

                patient_id = item['PatientID']
                earliest, latest = daterange(item['ReferenceTime'], self.delta)

                r = source.get_series(index,
                                      patient_id,
                                      desc,
                                      earliest,
                                      latest)

                # Consider only the FIRST match for now, should find best (latest?) of results somehow
                if r:
                    item['AccessionNumber'] = r[0]['AccessionNumber']
                    item['OID'] = r[0]['ID']
                    item['SeriesDescription'] = r[0]['SeriesDescription']


    def copy(self, source, peer):
        for item in self.items:
            logging.debug(item)
            id = item['ID']
            if id:
                source.send_item(peer, id)

import yaml

if __name__ == "__main__":

    logging.basicConfig(level=logging.DEBUG)
    with open("secrets.yml", 'r') as f:
        secrets = yaml.load(f)

    splunk =  Splunk(**secrets['services']['splunk'])
    montage = Montage(**secrets['services']['montage'])
    archive = Orthanc(**secrets['services']['cirr1'])
    proxy =   Orthanc(**secrets['services']['deathstar'])

    exit()


    # worklist = Worklist(fn="/Users/derek/Desktop/elvos.csv", delta="-1d")
    # worklist.update(splunk, desc="*cta*")
    # worklist.output("/Users/derek/Desktop/elvos2.csv")

    # worklist = Worklist(fn="/Users/derek/Desktop/elvos2.csv", delta="-1d")
    # qdict = {"exam_type": [8683, 8766]}  # No modality or "*cta*" needed b/c exam type
    # worklist.update(montage, qdict=qdict)
    # worklist.output("/Users/derek/Desktop/elvos3.csv")

    worklist = Worklist(fn="/Users/derek/Desktop/elvos3.csv", delta="-1d")
    worklist.update(proxy, remote="gepacs")

    # worklist.copy(archive, "hounsfield-elvo")  # Copy anything on worklist with an OID


