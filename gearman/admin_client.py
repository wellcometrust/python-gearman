import logging

from gearman import util

from gearman.connection_manager import GearmanConnectionManager
from gearman.admin_client_handler import GearmanAdminClientCommandHandler
from gearman.errors import InvalidAdminClientState
from gearman.protocol import GEARMAN_SERVER_COMMAND_STATUS, GEARMAN_SERVER_COMMAND_VERSION, GEARMAN_SERVER_COMMAND_WORKERS, GEARMAN_SERVER_COMMAND_MAXQUEUE, GEARMAN_SERVER_COMMAND_SHUTDOWN

gearman_logger = logging.getLogger(__name__)

class GearmanAdminClient(GearmanConnectionManager):
    """Connects to a single server and sends TEXT based administrative commands.
    This client acts as a BLOCKING client and each call will poll until it receives a satisfactory server response

    http://gearman.org/index.php?id=protocol
    See section 'Administrative Protocol'
    """
    command_handler_class = GearmanAdminClientCommandHandler

    def __init__(self, host_list=None, admin_client_timeout=5.0):
        super(GearmanAdminClient, self).__init__(host_list=host_list)
        self.admin_client_timeout = admin_client_timeout

        self.current_connection = util.unlist(self.connection_list)
        self.current_handler = util.unlist(self.handler_to_connection_map.keys())

    def send_maxqueue(self, task, max_size):
        self.current_connection.connect()

        self.current_handler.send_text_command('%s %s %s' % (GEARMAN_SERVER_COMMAND_MAXQUEUE, task, max_size))
        return self.wait_until_server_responds(GEARMAN_SERVER_COMMAND_MAXQUEUE)

    def send_shutdown(self, graceful=True):
        self.current_connection.connect()

        actual_command = GEARMAN_SERVER_COMMAND_SHUTDOWN
        if graceful:
            actual_command += ' graceful'

        self.current_handler.send_text_command(actual_command)
        return self.wait_until_server_responds(GEARMAN_SERVER_COMMAND_SHUTDOWN)

    def get_status(self):
        self.current_connection.connect()

        self.current_handler.send_text_command(GEARMAN_SERVER_COMMAND_STATUS)
        return self.wait_until_server_responds(GEARMAN_SERVER_COMMAND_STATUS)

    def get_version(self):
        self.current_connection.connect()

        self.current_handler.send_text_command(GEARMAN_SERVER_COMMAND_VERSION)
        return self.wait_until_server_responds(GEARMAN_SERVER_COMMAND_VERSION)

    def get_workers(self):
        self.current_connection.connect()

        self.current_handler.send_text_command(GEARMAN_SERVER_COMMAND_WORKERS)
        return self.wait_until_server_responds(GEARMAN_SERVER_COMMAND_WORKERS)

    def wait_until_server_responds(self, expected_type):
        current_handler = self.current_handler
        def continue_while_no_response(any_activity):
            return (not current_handler.has_response())

        self.poll_connections_until_stopped([self.current_connection], continue_while_no_response, timeout=self.admin_client_timeout)
        if not current_connection.has_response():
            raise InvalidAdminClientState('Admin client timed out after %f second(s)' % self.admin_client_timeout)

        cmd_type, cmd_resp = self.current_handler.pop_response()
        if cmd_type != expected_type:
            raise InvalidAdminClientState('Received an unexpected response... got command %r, expecting command %r' % (cmd_type, expected_type))

        return cmd_resp