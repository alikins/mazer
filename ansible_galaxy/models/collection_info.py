from __future__ import print_function

import json
import logging
import os
import re

import prettyprinter
import attr
import semver

log = logging.getLogger(__name__)

TAG_REGEXP = re.compile('^[a-z0-9]+$')

# see https://github.com/ansible/galaxy/issues/957


def load_spdx_licenses():
    cwd = os.path.dirname(os.path.abspath(__file__))
    license_path = os.path.join(cwd, '..', 'data', 'spdx_licenses.json')

    log.info('loading %s as json', license_path)
    licenses = {}

    license_data = json.load(open(license_path, 'r'))
    for lic in license_data['licenses']:
        lid = lic['licenseId']
        licenses[lid] = {'deprecated': lic['isDeprecatedLicenseId']}
    return licenses

licenses = load_spdx_licenses()


@attr.s(frozen=True)
class CollectionInfo(object):
    name = attr.ib(default=None)
    version = attr.ib(default=None)
    authors = attr.ib(default=[])
    license = attr.ib(default=None)
    description = attr.ib(default=None)
    keywords = attr.ib(default=[])
    readme = attr.ib(default='README.md')

    # Note galaxy.yml 'dependencies' field is what mazer and ansible
    # consider 'requirements'. ie, install time requirements.
    dependencies = attr.ib(default=[])

    # log.info('valid: %s', valid)
    # log.info('deprecated: %s', deprecated)
    prettyprinter.pprint(licenses)

    @property
    def licenses(self):
        return licenses

    @property
    def namespace(self):
        return self.name.split('.', 1)[0]

    @staticmethod
    def value_error(msg):
        raise ValueError("Invalid collection metadata. %s" % msg)

    @name.validator
    @version.validator
    @license.validator
    @description.validator
    def _check_required(self, attribute, value):
        if value is None:
            self.value_error("'%s' is required" % attribute.name)

    @version.validator
    def _check_version_format(self, _attribute, value):
        try:
            semver.parse_version_info(value)
        except ValueError:
            self.value_error("Expecting 'version' to be in semantic version format, "
                             "instead found '%s'." % value)

    @license.validator
    def _check_license(self, _attribute, value):
        valid = self.licenses.get(value, {})
        if not valid:
            self.value_error("Expecting 'license' to be a valid SPDX license ID, instead found '%s'. "
                             "For more info, visit https://spdx.org" % value)

        if valid.get('deprecated', False):
            print('License %s is deprecated' % value)

    @authors.validator
    @keywords.validator
    @dependencies.validator
    def _check_list_type(self, attribute, value):
        if not isinstance(value, list):
            self.value_error("Expecting '%s' to be a list" % attribute.name)

    @keywords.validator
    def _check_keywords(self, _attribute, value):
        for k in value:
            if not re.match(TAG_REGEXP, k):
                self.value_error("Expecting keywords to contain alphanumeric characters only, "
                                 "instead found '%s'." % k)

    @name.validator
    def _check_name(self, _attribute, value):
        if len(value.split('.', 1)) != 2:
            self.value_error("Expecting 'name' to be in Galaxy name format, <namespace>.<collection_name>, "
                             "instead found '%s'." % value)
