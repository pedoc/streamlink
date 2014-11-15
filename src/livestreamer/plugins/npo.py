"""Plugin for NPO: Nederlandse Publieke Omroep

Supports:
   VODs: http://www.npo.nl/het-zandkasteel/POMS_S_NTR_059963
   Live: http://www.npo.nl/live/nederland-1
"""

import re
import json

from livestreamer.plugin import Plugin
from livestreamer.plugin.api import http
from livestreamer.stream import HTTPStream, HLSStream

_url_re = re.compile("http(s)?://(\w+\.)?npo.nl/")

class NPO(Plugin):
    @classmethod
    def can_handle_url(cls, url):
        return _url_re.match(url)

    def get_token(self):
        token = http.get('http://ida.omroep.nl/npoplayer/i.js').content
        return re.compile('token.*?"(.*?)"', re.DOTALL + re.IGNORECASE).search(token).group(1)

    def _get_vod_streams(self):
        url = 'http://ida.omroep.nl/odi/?prid={}&puboptions=adaptive,h264_bb,h264_std,h264_sb&adaptive=no&part=1&token={}'.format(self.npo_id, self.get_token())
        data = http.get(url).json()
        streams = {}
        stream = http.get(data['streams'][0].replace('jsonp', 'json')).json()
        streams['best'] = streams['high'] = HTTPStream(self.session, stream['url'])
        return streams

    def _get_live_streams(self):
        html = http.get('http://www.npo.nl/live/' + self.npo_id).content
        program_id = re.compile('data-prid="(.*?)"', re.DOTALL + re.IGNORECASE).search(html).group(1)
        meta = http.get('http://e.omroep.nl/metadata/' + program_id).content
        meta = re.compile('({.*})', re.DOTALL + re.IGNORECASE).search(meta).group(1)
        meta = json.loads(meta)
        stream = filter(lambda x: x['type'] == 'hls', meta['streams'])[0]['url']
        url = 'http://ida.omroep.nl/aapi/?type=jsonp&stream={}&token={}'.format(stream, self.get_token())
        streamdata = http.get(url).json()
        deeplink = http.get(streamdata['stream']).content
        deeplink = re.compile('"(.*?)"', re.DOTALL + re.IGNORECASE).search(deeplink).group(1)
        playlist_url = deeplink.replace("\\/", "/")
        return HLSStream.parse_variant_playlist(self.session, playlist_url)

    def _get_streams(self):
        urlparts = self.url.split('/')
        self.npo_id = urlparts[-1]

        if (urlparts[-2] == 'live'):
            return self._get_live_streams()
        else:
            return self._get_vod_streams()

__plugin__ = NPO
