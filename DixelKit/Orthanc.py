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
                 peer_name=None):
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

    def get(self, dixel):
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

    def update(self, dixel):

        meta = dixel.meta.copy()

        url = "{}/{}/{}/tags?simplify".format(self.url, str(dixel.level), dixel.id)
        r = self.session.get(url)

        tags = r.json()
        tags = DixelTools.simplify_tags(tags)

        meta.update(tags)

        url = "{}/{}/{}/metadata/TransferSyntaxUID".format(self.url, str(dixel.level), dixel.id)
        r = self.session.get(url)
        meta['TransferSyntaxUID'] = r.json()

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

        self.logger.debug(res)

        return res


class OrthancProxy(Orthanc):

    def __init__(self, *args, **kwargs):
        self.remote_aet = kwargs.get('remote_aet', None)
        super(OrthancProxy, self).__init__(*args, **kwargs)

    def get(self, dixel, **kwargs):

        dicom_level = str(dixel.level)

        if not dixel.meta.get('qid'):
            # TODO: Check if qid has expired?
            # Haven't found this on remote yet

            def qdict(dixel):
                qdict = {'PatientID': '',
                         'StudyInstanceUID': '',
                         'StudyDate': '',
                         'StudyTime': '',
                         'AccessionNumber': '',
                         'ModalitiesInStudy': 'CT'}
                qdict.update(dixel.meta)
                return qdict

            query = qdict(dixel)

            data = {'Level': dicom_level,
                    'Query': query}

            url = '{0}/modalities/{1}/query'.format(self.url, self.remote_aet)

            headers = {"Accept-Encoding": "identity",
                       "Accept": "application/json"}

            # This is a sketchy call to Orthanc, so we do some error catching for review
            try:
                r = self.session.post(url, data=data, headers=headers)
            except ConnectionError as e:
                self.logger.error(e)
                self.logger.error(e.request.headers)
                self.logger.error(e.request.body)

            qid = r.json()["ID"]

            url = '{0}/queries/{1}/answers'.format(self.url, qid)
            r = self.session.get(url)
            answers = r.json()

            for aid in answers:
                # Create children pre-dixels
                url = '{0}/queries/{1}/answers/{2}/content'.format(self.url, qid, aid)
                r = self.session.get(url)

                tags = r.json()
                logging.debug(tags)

                id = DixelTools.orthanc_id(tags['PatientID'], tags['StudyInstanceUID'])
                meta = {'qid': qid,
                        'aid': aid}

                dixel.children.append(Dixel(id, level=DicomLevel.STUDIES, meta=meta))

            dixel.meta['qid'] = qid

        else:
            qid = dixel.meta.get('qid')

        retrieve = kwargs.get('retrieve', False)
        if retrieve:
            url = "{0}/queries/answers/{1}/retrieve".format(qid, aid)
            r = self.session.get(url)
            dixel.id = r.json()['ID']

        return dixel

    def copy(self, dixel, dest):
        # Must _retrieve_ first
        self.get(dixel, retrieve=True)
        Orthanc.copy(self, dixel, dest)

    def update(self, dixel):
        # Must make request from PACS
        return self.get(dixel)

