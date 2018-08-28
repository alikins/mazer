import logging

log = logging.getLogger(__name__)


VALID_ROLE_SPEC_KEYS = [
    'src',
    'version',
    'role',
    'name',
    'scm',
]

# Galaxy Content Constants
CONTENT_PLUGIN_TYPES = (
    'module',
    'module_util',
    'action_plugin',
    'apb',
    'filter_plugin',
    'connection_plugin',
    'inventory_plugin',
    'lookup_plugin',
    'shell_plugin',
    'strategy_plugin',
    'netconf_plugin',
    'callback_plugin',
)
CONTENT_TYPES = CONTENT_PLUGIN_TYPES + ('role',)
SUPPORTED_CONTENT_TYPES = ('role',)

CONTENT_TYPE_DIR_MAP = dict([(k, '%ss' % k) for k in CONTENT_TYPES])
CONTENT_TYPE_DIR_MAP['module'] = 'library'
TYPE_DIR_CONTENT_TYPE_MAP = dict([('%ss' % k, k) for k in CONTENT_TYPES])
TYPE_DIR_CONTENT_TYPE_MAP['library'] = 'module'
