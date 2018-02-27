# Copyright 2017 Shortest Track Company. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied. See the License for the specific language governing permissions and limitations under
# the License.

"""Implements HTTP client helper functionality."""
import datetime
import json
import logging
import sys
from st_library.dataprovider.utils.helpers.store import Store


log = logging.getLogger(__name__)


class RequestException(Exception):
    def __init__(self, status, content):
        self.status = status
        self.content = content
        self.message = 'HTTP request failed'
        # Try extract a message from the body; swallow possible resulting ValueErrors and KeyErrors.
        try:
            error = json.loads(content)['error']
            if 'errors' in error:
                error = error['errors'][0]
            self.message += ': ' + error['message']
        except Exception:
            lines = content.split('\n')
            if lines:
                self.message += ': ' + lines[0]

    def __str__(self):
        return self.message


class Http(object):
    """A helper class for making HTTP requests.
    """

    def __init__(self):
        pass

    @staticmethod
    def request(url, args=None, data=None, headers=None, method=None,
                credentials=None, raw_response=False, stats=None):
        """Issues HTTP requests.

        Args:
          url: the URL to request.
          args: optional query string arguments.
          data: optional data to be sent within the request.
          headers: optional headers to include in the request.
          method: optional HTTP method to use. If unspecified this is inferred
              (GET or POST) based on the existence of request data.
          credentials: optional set of credentials to authorize the request.
          raw_response: whether the raw response content should be returned as-is.
          stats: an optional dictionary that, if provided, will be populated with some
              useful info about the request, like 'duration' in seconds and 'data_size' in
              bytes. These may be useful optimizing the access to rate-limited APIs.
        Returns:
          The parsed response object.
        Raises:
          Exception when the HTTP request fails or the response cannot be processed.
        """
        if headers is None:
            headers = {}

        headers['user-agent'] = 'st-dataprovider/1.0'
        headers['Authorization'] = Store.token

        # Setup method to POST if unspecified, and appropriate request headers
        # if there is data to be sent within the request.
        if data is not None:
            if method is None:
                method = 'POST'

            if data != '':
                # If there is a content type specified, use it (and the data) as-is.
                # Otherwise, assume JSON, and serialize the data object.
                if 'Content-Type' not in headers:
                    data = json.dumps(data)
                    headers['Content-Type'] = 'application/json'
        else:
            if method == 'POST':
                headers['Content-Length'] = '0'

        # If the method is still unset, i.e. it was unspecified, and there
        # was no data to be POSTed, then default to GET request.
        if method is None:
            method = 'GET'
        'https://shortesttrack.com/api/metadata/matrices/62a9058c_07e8_4c61_8da0_0f822952447e'
        if stats is not None:
            stats['duration'] = datetime.datetime.utcnow()

        response = None
        try:
            log.debug('request: method[%(method)s], url[%(url)s], body[%(data)s]' % locals())
            status_code = None
            if sys.version > '3':
                import requests
                if method == 'POST':
                    response = requests.post(url=url, headers=headers, data=data)
                    content = response.text
                    status_code = response.status_code
                elif method == 'GET':
                    response = requests.get(url=url, headers=headers)
                    content = response.text
                    status_code = response.status_code
            else:
                import urllib2
                request = urllib2.Request(url, data, headers)
                try:
                    content = urllib2.urlopen(request).read()
                except urllib2.HTTPError as e:
                    status_code = e.code
                # ...
                except urllib2.URLError as e:
                    # Not an HTTP-specific error (e.g. connection refused)
                    # ...
                    status_code = e.code
                else:
                    # 200
                    status_code = 200

            if 200 <= status_code < 300:
                if raw_response:
                    return content
                if content.strip() == '':
                    return content
                elif type(content) == str:
                    return json.loads(content)
            else:
                raise RequestException(status_code, content)
        except ValueError:
            raise Exception('Failed to process HTTP response.')
        finally:
            if stats is not None:
                stats['data_size'] = len(data)
                stats['status'] = status_code
                stats['duration'] = (datetime.datetime.utcnow() - stats['duration']).total_seconds()
