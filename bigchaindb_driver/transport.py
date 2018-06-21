from time import time

from requests.exceptions import ConnectionError

from .connection import Connection
from .exceptions import TimeoutError
from .pool import Pool


class Transport:
    """Transport class.

    """

    def __init__(self, *nodes, headers=None, timeout=None):
        """Initializes an instance of
        :class:`~bigchaindb_driver.transport.Transport`.

        Args:
            nodes: nodes
            headers (dict): Optional headers to pass to the
                :class:`~.connection.Connection` instances, which will
                add it to the headers to be sent with each request.
            timeout (int): Optional timeout in seconds.

        """
        self.nodes = nodes
        self.timeout = timeout
        self.connection_pool = Pool([Connection(node_url=node['endpoint'],
                                                headers=node['headers'])
                                     for node in nodes])

    def forward_request(self, method, path=None,
                        json=None, params=None, headers=None):
        """Makes HTTP requests to the configured nodes.

           Retries connection errors
           (e.g. DNS failures, refused connection, etc).
           A user may choose to retry other errors
           by catching the corresponding
           exceptions and retrying `forward_request`.

           Backoff time is tracked for every configured node.
           Exponential backoff thus
           works no matter how many times `forward_request` is called.

           Times out when `self.timeout` is expired, if not `None`.

        Args:
            method (str): HTTP method name (e.g.: ``'GET'``).
            path (str): Path to be appended to the base url of a node. E.g.:
                ``'/transactions'``).
            json (dict): Payload to be sent with the HTTP request.
            params (dict)): Dictionary of URL (query) parameters.
            headers (dict): Optional headers to pass to the request.

        Returns:
            dict: Result of :meth:`requests.models.Response.json`

        """
        error_trace = []
        timeout = self.timeout
        while timeout is None or timeout > 0:
            connection = self.connection_pool.get_connection()

            start = time()
            try:
                response = connection.request(
                    method=method,
                    path=path,
                    params=params,
                    json=json,
                    headers=headers,
                    timeout=timeout,
                )
            except ConnectionError as err:
                error_trace.append(err)
                continue
            else:
                return response.data
            finally:
                elapsed = time() - start
                if timeout is not None:
                    timeout -= elapsed

        raise TimeoutError(error_trace)
