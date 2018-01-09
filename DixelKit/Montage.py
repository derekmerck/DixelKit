import requests
from pprint import pformat
from Dixel import *
from DixelStorage import *


class Montage(DixelStorage):

    def __init__(self, host, port=80, user=None, password=None):

        self.session = requests.session()
        if user and password:
            self.session.auth = (user, password)
        self.url = "http://{host}:{port}/api/v1".format(host=host, port=port)
        super(Montage, self).__init__()

        indices = self.session.get("{0}/index".format(self.url))
        self.logger.debug(indices.json())

    def query(self, qdict, index="rad"):
        url = "{0}/index/{1}/search".format(self.url, index)
        r = self.session.get(url, params=qdict)

        self.logger.debug(pformat(r))
        return r.json()["objects"]

    def update(self, dixel):
        pass
        # Make a qdict for this dixel

    def make_worklist(self, qdict):
        # Return a set of predixel results
        r = self.query(qdict)
        logging.debug(pformat(r))

        res = set()

        for item in r:

            meta = {
                'AccessionNumber': item[0]["accession_number"],
                'mid'            : item[0]["id"],                # Montage ID
                'ReportText'     : item[0]['text'],
                'ExamType'       : item[0]['exam_type']['code']  # IMG code
            }
            res.add(
                Dixel( id=meta['AccessionNumber'], meta=meta, level=DicomLevel.STUDIES )
            )

        return res

def test_montage():

    montage = Montage('montage', 80, 'm_user', 'passw0rd')

    qdict = { "q":          "cta",
              "modality":   4,
              "exam_type":  [8683, 7713, 8766],
              "start_date": "2016-11-17",
              "end_date":   "2016-11-19"}

    worklist = montage.make_worklist(qdict)
