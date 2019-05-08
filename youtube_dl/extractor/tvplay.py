# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import (
    compat_HTTPError,
    compat_str,
    compat_urlparse,
)
from ..utils import (
    determine_ext,
    ExtractorError,
    int_or_none,
    parse_iso8601,
    qualities,
    smuggle_url,
    try_get,
    unsmuggle_url,
    update_url_query,
    url_or_none,
)


class TVPlayIE(InfoExtractor):
    IE_NAME = 'mtg'
    IE_DESC = 'MTG services'
    _VALID_URL = r'''(?x)
                    (?:
                        mtg:|
                        https?://
                            (?:www\.)?
                            (?:
                                tvplay(?:\.skaties)?\.lv(?:/parraides)?|
                                (?:tv3play|play\.tv3)\.lt(?:/programos)?|
                                tv3play(?:\.tv3)?\.ee/sisu|
                                (?:tv(?:3|6|8|10)play|viafree)\.se/program|
                                (?:(?:tv3play|viasat4play|tv6play|viafree)\.no|(?:tv3play|viafree)\.dk)/programmer|
                                play\.nova(?:tv)?\.bg/programi
                            )
                            /(?:[^/]+/)+
                        )
                        (?P<id>\d+)
                    '''
    _TESTS = [
        {
            'url': 'http://www.tvplay.lv/parraides/vinas-melo-labak/418113?autostart=true',
            'md5': '31d1b748174f65c3d294721df890f402',
            'info_dict': {
                'id': '418113',
                'ext': 'mp4',
                'title': 'Kādi ir īri? - Viņas melo labāk',
                'description': 'Baiba apsmej īrus, kādi tie ir un ko viņi dara.',
                'series': 'Viņas melo labāk',
                'season': '2.sezona',
                'season_number': 2,
                'duration': 25,
                'timestamp': 1406097056,
                'upload_date': '20140723',
            },
        },
        {
            'url': 'http://play.tv3.lt/programos/moterys-meluoja-geriau/409229?autostart=true',
            'info_dict': {
                'id': '409229',
                'ext': 'flv',
                'title': 'Moterys meluoja geriau',
                'description': 'md5:9aec0fc68e2cbc992d2a140bd41fa89e',
                'series': 'Moterys meluoja geriau',
                'episode_number': 47,
                'season': '1 sezonas',
                'season_number': 1,
                'duration': 1330,
                'timestamp': 1403769181,
                'upload_date': '20140626',
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.tv8play.se/program/antikjakten/282756?autostart=true',
            'info_dict': {
                'id': '282756',
                'ext': 'mp4',
                'title': 'Antikjakten S01E10',
                'description': 'md5:1b201169beabd97e20c5ad0ad67b13b8',
                'duration': 2646,
                'timestamp': 1348575868,
                'upload_date': '20120925',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://www.viasat4play.no/programmer/budbringerne/21873?autostart=true',
            'info_dict': {
                'id': '21873',
                'ext': 'mp4',
                'title': 'Budbringerne program 10',
                'description': 'md5:4db78dc4ec8a85bb04fd322a3ee5092d',
                'duration': 1297,
                'timestamp': 1254205102,
                'upload_date': '20090929',
            },
            'params': {
                'skip_download': True,
            },
        },
        {
            'url': 'http://play.novatv.bg/programi/zdravei-bulgariya/624952?autostart=true',
            'info_dict': {
                'id': '624952',
                'ext': 'mp4',
                'title': 'Здравей, България (12.06.2015 г.) ',
                'description': 'md5:99f3700451ac5bb71a260268b8daefd7',
                'duration': 8838,
                'timestamp': 1434100372,
                'upload_date': '20150612',
            },
            'params': {
                # rtmp download
                'skip_download': True,
            },
        },
        {
            'url': 'https://play.nova.bg/programi/zdravei-bulgariya/764300?autostart=true',
            'only_matching': True,
        },
        {
            'url': 'http://tvplay.skaties.lv/parraides/vinas-melo-labak/418113?autostart=true',
            'only_matching': True,
        },
        {
            'url': 'https://tvplay.skaties.lv/vinas-melo-labak/418113/?autostart=true',
            'only_matching': True,
        },
        {
            # views is null
            'url': 'http://tvplay.skaties.lv/parraides/tv3-zinas/760183',
            'only_matching': True,
        },
        {
            'url': 'http://tv3play.tv3.ee/sisu/kodu-keset-linna/238551?autostart=true',
            'only_matching': True,
        },
        {
            'url': 'http://www.viafree.se/program/underhallning/i-like-radio-live/sasong-1/676869',
            'only_matching': True,
        },
        {
            'url': 'mtg:418113',
            'only_matching': True,
        }
    ]

    def _real_extract(self, url):
        url, smuggled_data = unsmuggle_url(url, {})
        self._initialize_geo_bypass({
            'countries': smuggled_data.get('geo_countries'),
        })

        video_id = self._match_id(url)
        geo_country = self._search_regex(
            r'https?://[^/]+\.([a-z]{2})', url,
            'geo country', default=None)
        if geo_country:
            self._initialize_geo_bypass({'countries': [geo_country.upper()]})
        video = self._download_json(
            'http://playapi.mtgx.tv/v3/videos/%s' % video_id, video_id, 'Downloading video JSON')

        title = video['title']

        try:
            streams = self._download_json(
                'http://playapi.mtgx.tv/v3/videos/stream/%s' % video_id,
                video_id, 'Downloading streams JSON')
        except ExtractorError as e:
            if isinstance(e.cause, compat_HTTPError) and e.cause.code == 403:
                msg = self._parse_json(e.cause.read().decode('utf-8'), video_id)
                raise ExtractorError(msg['msg'], expected=True)
            raise

        quality = qualities(['hls', 'medium', 'high'])
        formats = []
        for format_id, video_url in streams.get('streams', {}).items():
            video_url = url_or_none(video_url)
            if not video_url:
                continue
            ext = determine_ext(video_url)
            if ext == 'f4m':
                formats.extend(self._extract_f4m_formats(
                    update_url_query(video_url, {
                        'hdcore': '3.5.0',
                        'plugin': 'aasp-3.5.0.151.81'
                    }), video_id, f4m_id='hds', fatal=False))
            elif ext == 'm3u8':
                formats.extend(self._extract_m3u8_formats(
                    video_url, video_id, 'mp4', 'm3u8_native',
                    m3u8_id='hls', fatal=False))
            else:
                fmt = {
                    'format_id': format_id,
                    'quality': quality(format_id),
                    'ext': ext,
                }
                if video_url.startswith('rtmp'):
                    if smuggled_data.get('skip_rtmp'):
                        continue
                    m = re.search(
                        r'^(?P<url>rtmp://[^/]+/(?P<app>[^/]+))/(?P<playpath>.+)$', video_url)
                    if not m:
                        continue
                    fmt.update({
                        'ext': 'flv',
                        'url': m.group('url'),
                        'app': m.group('app'),
                        'play_path': m.group('playpath'),
                        'preference': -1,
                    })
                else:
                    fmt.update({
                        'url': video_url,
                    })
                formats.append(fmt)

        if not formats and video.get('is_geo_blocked'):
            self.raise_geo_restricted(
                'This content might not be available in your country due to copyright reasons')

        self._sort_formats(formats)

        # TODO: webvtt in m3u8
        subtitles = {}
        sami_path = video.get('sami_path')
        if sami_path:
            lang = self._search_regex(
                r'_([a-z]{2})\.xml', sami_path, 'lang',
                default=compat_urlparse.urlparse(url).netloc.rsplit('.', 1)[-1])
            subtitles[lang] = [{
                'url': sami_path,
            }]

        series = video.get('format_title')
        episode_number = int_or_none(video.get('format_position', {}).get('episode'))
        season = video.get('_embedded', {}).get('season', {}).get('title')
        season_number = int_or_none(video.get('format_position', {}).get('season'))

        return {
            'id': video_id,
            'title': title,
            'description': video.get('description'),
            'series': series,
            'episode_number': episode_number,
            'season': season,
            'season_number': season_number,
            'duration': int_or_none(video.get('duration')),
            'timestamp': parse_iso8601(video.get('created_at')),
            'view_count': try_get(video, lambda x: x['views']['total'], int),
            'age_limit': int_or_none(video.get('age_limit', 0)),
            'formats': formats,
            'subtitles': subtitles,
        }


class ViafreeIE(InfoExtractor):
    _VALID_URL = r'''(?x)
                    https?://
                        (?:www\.)?
                        viafree\.
                        (?:
                            (?:dk|no)/programmer|
                            se/program
                        )
                        /(?:[^/]+/)+(?P<id>[^/?#&]+)
                    '''
    _TESTS = [{
        'url': 'http://www.viafree.se/program/livsstil/husraddarna/sasong-2/avsnitt-2',
        'info_dict': {
            'id': '395375',
            'ext': 'mp4',
            'title': 'Husräddarna S02E02',
            'description': 'md5:4db5c933e37db629b5a2f75dfb34829e',
            'series': 'Husräddarna',
            'season': 'Säsong 2',
            'season_number': 2,
            'duration': 2576,
            'timestamp': 1400596321,
            'upload_date': '20140520',
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [TVPlayIE.ie_key()],
    }, {
        # with relatedClips
        'url': 'http://www.viafree.se/program/reality/sommaren-med-youtube-stjarnorna/sasong-1/avsnitt-1',
        'info_dict': {
            'id': '758770',
            'ext': 'mp4',
            'title': 'Sommaren med YouTube-stjärnorna S01E01',
            'description': 'md5:2bc69dce2c4bb48391e858539bbb0e3f',
            'series': 'Sommaren med YouTube-stjärnorna',
            'season': 'Säsong 1',
            'season_number': 1,
            'duration': 1326,
            'timestamp': 1470905572,
            'upload_date': '20160811',
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [TVPlayIE.ie_key()],
    }, {
        # Different og:image URL schema
        'url': 'http://www.viafree.se/program/reality/sommaren-med-youtube-stjarnorna/sasong-1/avsnitt-2',
        'only_matching': True,
    }, {
        'url': 'http://www.viafree.no/programmer/underholdning/det-beste-vorspielet/sesong-2/episode-1',
        'only_matching': True,
    }, {
        'url': 'http://www.viafree.dk/programmer/reality/paradise-hotel/saeson-7/episode-5',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return False if TVPlayIE.suitable(url) else super(ViafreeIE, cls).suitable(url)

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        data = self._parse_json(
            self._search_regex(
                r'(?s)window\.App\s*=\s*({.+?});\s*window\.',
                webpage, 'data', default='{}'),
            video_id, transform_source=lambda x: re.sub(
                r'(?s)(?<=":)function.+?}(?=,")',
                'null', x), fatal=False)

        video_id = None

        if data:
            video_id = try_get(
                data, lambda x: x['context']['dispatcher']['stores'][
                    'ContentPageProgramStore']['currentVideo']['id'],
                compat_str)

        # Fallback #1 (extract from og:image URL schema)
        if not video_id:
            thumbnail = self._og_search_thumbnail(webpage, default=None)
            if thumbnail:
                video_id = self._search_regex(
                    # Patterns seen:
                    #  http://cdn.playapi.mtgx.tv/imagecache/600x315/cloud/content-images/inbox/765166/a2e95e5f1d735bab9f309fa345cc3f25.jpg
                    #  http://cdn.playapi.mtgx.tv/imagecache/600x315/cloud/content-images/seasons/15204/758770/4a5ba509ca8bc043e1ebd1a76131cdf2.jpg
                    r'https?://[^/]+/imagecache/(?:[^/]+/)+(\d{6,})/',
                    thumbnail, 'video id', default=None)

        # Fallback #2. Extract from raw JSON string.
        # May extract wrong video id if relatedClips is present.
        if not video_id:
            video_id = self._search_regex(
                r'currentVideo["\']\s*:\s*.+?["\']id["\']\s*:\s*["\'](\d{6,})',
                webpage, 'video id')

        return self.url_result(
            smuggle_url(
                'mtg:%s' % video_id,
                {
                    'geo_countries': [
                        compat_urlparse.urlparse(url).netloc.rsplit('.', 1)[-1]],
                    # rtmp host mtgfs.fplive.net for viafree is unresolvable
                    'skip_rtmp': True,
                }),
            ie=TVPlayIE.ie_key(), video_id=video_id)


class TVPlayHomeIE(InfoExtractor):
    _VALID_URL = r'https?://tvplay\.(?:tv3\.lt|skaties\.lv|tv3\.ee)/[^/]+/[^/?#&]+-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://tvplay.tv3.lt/aferistai-n-7/aferistai-10047125/',
        'info_dict': {
            'id': '366367',
            'ext': 'mp4',
            'title': 'Aferistai',
            'description': 'Aferistai. Kalėdinė pasaka.',
            'series': 'Aferistai [N-7]',
            'season': '1 sezonas',
            'season_number': 1,
            'duration': 464,
            'timestamp': 1394209658,
            'upload_date': '20140307',
            'age_limit': 18,
        },
        'params': {
            'skip_download': True,
        },
        'add_ie': [TVPlayIE.ie_key()],
    }, {
        'url': 'https://tvplay.skaties.lv/vinas-melo-labak/vinas-melo-labak-10280317/',
        'only_matching': True,
    }, {
        'url': 'https://tvplay.tv3.ee/cool-d-ga-mehhikosse/cool-d-ga-mehhikosse-10044354/',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage = self._download_webpage(url, video_id)

        video_id = self._search_regex(
            r'data-asset-id\s*=\s*["\'](\d{5,})\b', webpage, 'video id')

        if len(video_id) < 8:
            return self.url_result(
                'mtg:%s' % video_id, ie=TVPlayIE.ie_key(), video_id=video_id)

        m3u8_url = self._search_regex(
            r'data-file\s*=\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage,
            'm3u8 url', group='url')

        formats = self._extract_m3u8_formats(
            m3u8_url, video_id, 'mp4', entry_protocol='m3u8_native',
            m3u8_id='hls')
        self._sort_formats(formats)

        title = self._search_regex(
            r'data-title\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1', webpage,
            'title', default=None, group='value') or self._html_search_meta(
            'title', webpage, default=None) or self._og_search_title(
            webpage)

        description = self._html_search_meta(
            'description', webpage,
            default=None) or self._og_search_description(webpage)

        thumbnail = self._search_regex(
            r'data-image\s*=\s*(["\'])(?P<url>(?:(?!\1).)+)\1', webpage,
            'thumbnail', default=None, group='url') or self._html_search_meta(
            'thumbnail', webpage, default=None) or self._og_search_thumbnail(
            webpage)

        duration = int_or_none(self._search_regex(
            r'data-duration\s*=\s*["\'](\d+)', webpage, 'duration',
            fatal=False))

        season = self._search_regex(
            (r'data-series-title\s*=\s*(["\'])[^/]+/(?P<value>(?:(?!\1).)+)\1',
             r'\bseason\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1'), webpage,
            'season', default=None, group='value')
        season_number = int_or_none(self._search_regex(
            r'(\d+)(?:[.\s]+sezona|\s+HOOAEG)', season or '', 'season number',
            default=None))
        episode = self._search_regex(
            (r'\bepisode\s*:\s*(["\'])(?P<value>(?:(?!\1).)+)\1',
             r'data-subtitle\s*=\s*(["\'])(?P<value>(?:(?!\1).)+)\1'), webpage,
            'episode', default=None, group='value')
        episode_number = int_or_none(self._search_regex(
            r'(?:S[eē]rija|Osa)\s+(\d+)', episode or '', 'episode number',
            default=None))

        return {
            'id': video_id,
            'title': title,
            'description': description,
            'thumbnail': thumbnail,
            'duration': duration,
            'season': season,
            'season_number': season_number,
            'episode': episode,
            'episode_number': episode_number,
            'formats': formats,
        }
