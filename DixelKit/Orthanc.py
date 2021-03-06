import requests
from requests import ConnectionError
from hashlib import sha1
from pprint import pformat
from Dixel import *
from DixelStorage import *
import DixelTools
from Splunk import Splunk


class Orthanc(DixelStorage):

    def __init__(self,
                 host,
                 port=8042,
                 user=None,
                 password=None,
                 cache_policy=CachePolicy.NONE,
                 prefer_compressed=False,
                 peer_name=None,
                 **kwargs):
        self.session = requests.session()
        if user and password:
            self.session.auth = (user, password)
        self.url = "http://{host}:{port}".format(host=host, port=port)
        self.prefer_compressed = prefer_compressed
        self.peer_name = peer_name
        cache_pik = "{0}.pik".format(
                sha1("{0}:{1}@{2}".format(
                user, password, self.url)).hexdigest()[0:8])
        super(Orthanc, self).__init__(cache_pik=cache_pik, cache_policy=cache_policy)

    def statistics(self):
        url = "{0}/statistics".format(self.url)
        r = self.session.get(url)
        return r.json()

    def get(self, dixel, **kwargs):
        raise NotImplementedError

    def put(self, dixel):
        if dixel.level != DicomLevel.INSTANCES:
            raise NotImplementedError("Orthanc can only put dixel instances")

        headers = {'content-type': 'application/dicom'}
        url = "{0}/instances/".format(self.url)
        r = self.session.post(url, data=dixel.data['file'], headers=headers)

        if r.status_code == 200:
            self.logger.debug('Added {0} successfully!'.format(dixel))
        else:
            self.logger.warning('Could not add {0}!'.format(dixel))

        self.logger.debug(pformat(r.json()))

    def delete(self, dixel):
        url = "{}/{}/{}".format(self.url, str(dixel.level), dixel.id)
        r = self.session.delete(url)

        if r.status_code == 200:
            self.logger.debug('Removed {0} successfully!'.format(dixel))
        else:
            self.logger.warning('Could not delete {0}!'.format(dixel))

        self.logger.debug(pformat(r.json()))

    def update(self, dixel, **kwargs):

        meta = dixel.meta.copy()

        if dixel.level != "series":
            url = "{}/{}/{}/tags?simplify".format(self.url, str(dixel.level), dixel.id)
        else:
            url = "{}/{}/{}/shared-tags?simplify".format(self.url, str(dixel.level), dixel.id)
	    
        r = self.session.get(url)

        tags = r.json()
        tags = DixelTools.simplify_tags(tags)

        meta.update(tags)

        if dixel.level == "instance":
            url = "{}/{}/{}/metadata/TransferSyntaxUID".format(self.url, str(dixel.level), dixel.id)
            r = self.session.get(url)
            meta['TransferSyntaxUID'] = r.json()

            url = "{}/{}/{}/metadata/SopClassUid".format(self.url, str(dixel.level), dixel.id)
            r = self.session.get(url)
            meta['SOPClassUID'] = DixelTools.DICOM_SOPS.get(r.json(), r.json())  # Text or return val

        return Dixel(dixel.id, meta=meta, level=dixel.level)


    def copy(self, dixel, dest):
        # May have various tasks to do, like anonymize or compress

        if type(dest) == Orthanc:
            # Use push-to-peer
            url = "{0}/peers/{1}/store".format(self.url, dest.peer_name)
            self.session.post(url, data=dixel.id)

        elif type(dest) == Splunk:
            dixel = self.update(dixel)  # Add available data and meta data, parse
            dest.put(dixel)

        else:
            raise NotImplementedError(
                "{} doesn't know how to put dixel {} into {}".format(
                    self.__class__.__name__,
                    dixel.level,
                    dest.__class__.__name__))

    def initialize_inventory(self):
        res = set()
        r = self.session.get("{0}/instances".format(self.url)).json()
        for item in r:
            res.add(Dixel(id=item, level=DicomLevel.INSTANCES))

        # self.logger.debug(res)

        return res

    def exists(self, dixel):
        url = "{}/{}/{}".format(self.url,
                                str(dixel.level),
                                dixel.id)
        r = requests.get(url, auth=self.session.auth)
        # r = self.session.get(url)
        if r.status_code == 200:
            return True
        else:
            return False


class OrthancProxy(Orthanc):

    def __init__(self, *args, **kwargs):
        self.remote_aet = kwargs.get('remote_aet', None)
        super(OrthancProxy, self).__init__(*args, **kwargs)

    def get(self, dixel, **kwargs):

        def find_series(dixel):
            # Return an individual qid, aid

            dicom_level = "series"

            def qdict(dixel):
                qdict = {'PatientID': dixel.meta['PatientID'],
                         'StudyInstanceUID': '',
                         'SeriesInstanceUID': dixel.meta.get('SeriesInstanceUID'),
                         'SeriesDescription': '',
                         'SeriesNumber': '',
                         'StudyDate': '',
                         'StudyTime': '',
                         'AccessionNumber': dixel.meta['AccessionNumber']}
                # if dixel.level == DicomLevel.STUDIES:
                #     qdict['ModalitiesInStudy'] = 'CT'
                qdict.update(kwargs.get('qdict', {}))
                return qdict

            query = qdict(dixel)

            data = {'Level': dicom_level,
                    'Query': query}

            # self.logger.debug(pformat(data))

            url = '{0}/modalities/{1}/query'.format(self.url, self.remote_aet)
            self.logger.debug(url)

            headers = {"Accept-Encoding": "identity",
                       "Accept": "application/json"}

            # Does not like session.post for some reason!
            try:
                # r = self.session.post(url, json=data, headers=headers)
                r = requests.post(url, json=data, headers=headers, auth=self.session.auth)
                self.logger.debug(r.headers)
                self.logger.debug(r.content)
                dixel.meta['QID'] = r.json()["ID"]
            except ConnectionError as e:
                self.logger.error(e)
                self.logger.error(e.request.headers)
                self.logger.error(e.request.body)

            url = '{0}/queries/{1}/answers'.format(self.url, dixel.meta['QID'])
            r = self.session.get(url)

            answers = r.json()

            if len(answers)>1:
                self.logger.warn('Retrieve too many candidate responses, using LAST')

            for aid in answers:
                url = '{0}/queries/{1}/answers/{2}/content?simplify'.format(self.url, dixel.meta['QID'], aid)
                # r = self.session.get(url)
                r = requests.get(url, auth=self.session.auth)

                tags = r.json()
                logging.debug(pformat(tags))

                dixel.meta.update(tags)
                dixel.meta['AID'] = aid
                dixel.meta['OID'] = DixelTools.orthanc_id(tags['PatientID'],
                                            tags['StudyInstanceUID'],
                                            tags['SeriesInstanceUID'])

                # A proper series level ID
                dixel.id = dixel.meta['OID']

            return dixel

        def retrieve_series(dixel):
            if not kwargs.get('retrieve', False): return

            oid = DixelTools.orthanc_id(dixel.meta['PatientID'],
                                  dixel.meta['StudyInstanceUID'],
                                  dixel.meta['SeriesInstanceUID'])
            dixel.meta['oid'] = oid
            dixel.id = oid

            dixel.level = DicomLevel.SERIES

            self.logger.debug('Expecting oid: {}'.format(oid))

            if self.exists(dixel): return

            url = "{}/queries/{}/answers/{}/retrieve".format(
                self.url,
                dixel.meta['QID'],
                dixel.meta['AID'])
            r = requests.post(url, auth=self.session.auth, data="DEATHSTAR")
            self.logger.debug(r.content)

            if not self.exists(dixel):
                raise Exception("Failed to c-move dixel w accession {}".format(dixel.meta['AccessionNumber']))

            return dixel

        # Check and see if you already have it in inventory
        if self.exists(dixel):
            return Orthanc.update(self, dixel)

        # if not dixel.meta.get('QID') or not dixel.meta.get('AID'):
        dixel = find_series(dixel)

        if kwargs.get('retrieve'):
            dixel = retrieve_series(dixel)

        return dixel

    def copy(self, dixel, dest):
        # Must _retrieve_ first
        self.get(dixel, retrieve=True)
        Orthanc.copy(self, dixel, dest)
        self.delete(dixel)

    def update(self, dixel, **kwargs):

        if dixel.meta.get('AccessionNumber') and\
                not dixel.meta.get("RetrieveAETitle"):
            # run a PACS search for this study
            d = self.get(dixel, **kwargs)
        else:
            d = dixel

        return d



