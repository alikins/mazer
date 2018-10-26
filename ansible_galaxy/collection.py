import logging
import os
import shutil

import yaml

from ansible_galaxy import collection_info
from ansible_galaxy import install_info
from ansible_galaxy import yaml_persist

from ansible_galaxy.models.content_spec import ContentSpec
from ansible_galaxy.models.collection import Collection

log = logging.getLogger(__name__)

# aka, persistence of ansible_galaxy.models.collection


def load(data_or_file_object):
    collection = yaml.safe_load(data_or_file_object)
    return collection


def load_from_name(content_dir, namespace, name, installed=True):
    # TODO: or artifact

    path_name = os.path.join(content_dir, namespace, name)

    if not os.path.isdir(path_name):
        return None

    # load galaxy.yml
    galaxy_filename = os.path.join(path_name, collection_info.COLLECTION_INFO_FILENAME)

    collection_info_data = None
    try:
        with open(galaxy_filename, 'r') as gfd:
            collection_info_data = collection_info.load(gfd)
    except Exception as e:
        log.exception(e)

    log.debug('collection_info_data: %s', collection_info_data)

    requirements_filename = os.path.join(path_name, 'requirements.yml')
    requirements_data = None

    try:
        with open(requirements_filename, 'r') as rfd:
            requirements_data = yaml.safe_load(rfd)
    except Exception as e:
        log.exception(e)

    log.debug('requirements_data: %s', requirements_data)

    install_info_filename = os.path.join(path_name, 'meta/.galaxy_install_info')
    with open(install_info_filename, 'r') as ifd:
        install_info_data = install_info.load(ifd)

    log.debug('install_info: %s', install_info_data)

    content_spec = ContentSpec(namespace=namespace,
                               name=name,
                               version=install_info_data.version)

    collection = Collection(content_spec=content_spec,
                            path=path_name,
                            installed=installed,
                            requirements=requirements_data,
                            dependencies=[])

    log.debug('collection: %s', collection)

    return collection


def remove(installed_collection):
    log.info("Removing installed collection: %s", installed_collection)
    try:
        shutil.rmtree(installed_collection.path)
        return True
    except EnvironmentError as e:
        log.warn('Unable to rm the directory "%s" while removing installed repo "%s": %s',
                 installed_collection.path,
                 installed_collection.label,
                 e)
        log.exception(e)
        raise
