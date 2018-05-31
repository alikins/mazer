import logging

from ansible_galaxy import display
from ansible_galaxy import exceptions
from ansible_galaxy.utils.yaml_parse import yaml_parse

# FIXME: get rid of flat_rest_api
from ansible_galaxy.flat_rest_api.content import GalaxyContent

log = logging.getLogger(__name__)


def raise_without_ignore(ignore_errors, msg=None, rc=1):
    """
    Exits with the specified return code unless the
    option --ignore-errors was specified
    """
    ignore_error_blurb = '- you can use --ignore-errors to skip failed roles and finish processing the list.'
    if not ignore_errors:
        message = ignore_error_blurb
        if msg:
            message = '%s:\n%s' % (msg, ignore_error_blurb)
        # TODO: some sort of ignoreable exception
        raise exceptions.GalaxyError(message)


# FIXME: install_content_type is wrong, should be option to GalaxyContent.install()?
def _build_content_set(content_specs, install_content_type, galaxy_context):
    # TODO: split this into methods that build GalaxyContent items from the content_specs
    #       and another that installs a set of GalaxyContents
    # roles were specified directly, so we'll just go out grab them
    # (and their dependencies, unless the user doesn't want us to).

    # FIXME: could be a generator...
    content_left = []

    for content_spec in content_specs:
        galaxy_content = yaml_parse(content_spec.strip())

        # FIXME: this is a InstallOption
        galaxy_content["type"] = install_content_type

        log.info('content install galaxy_content: %s', galaxy_content)

        content_left.append(GalaxyContent(galaxy_context, **galaxy_content))

    return content_left


# pass a list of content_spec objects
def install_content_specs(galaxy_context, content_specs, install_content_type,
                          display_callback=None,
                          # TODO: error handling callback ?
                          ignore_errors=False,
                          no_deps=False,
                          force_overwrite=False):
    log.debug('contents: %s', content_specs)
    log.debug('install_content_type: %s', install_content_type)

    requested_contents = _build_content_set(content_specs=content_specs,
                                            install_content_type=install_content_type,
                                            galaxy_context=galaxy_context)

    return install_contents(galaxy_context, requested_contents, install_content_type,
                            display_callback=display_callback,
                            ignore_errors=ignore_errors,
                            no_deps=no_deps,
                            force_overwrite=force_overwrite)


def install_contents(galaxy_context, requested_contents, install_content_type,
                     display_callback=None,
                     # TODO: error handling callback ?
                     ignore_errors=False,
                     no_deps=False,
                     force_overwrite=False):

    display_callback = display_callback or display.display_callback
    log.debug('requested_contents: %s', requested_contents)
    log.debug('install_content_type: %s', install_content_type)
    log.debug('no_deps: %s', no_deps)
    log.debug('force_overwrite: %s', force_overwrite)

    # FIXME - Need to handle role files here for backwards compat

    # TODO: this should be adding the content/self.args/content_left to
    #       a list of needed deps

    # FIXME: should be while? or some more func style processing
    #        iterating until there is nothing left
    for content in requested_contents:
        # only process roles in roles files when names matches if given

        # FIXME - not sure how to handle this scenario for ansible galaxy files
        #         here or if we even want to handle that scenario because of
        #         the galaxy content allowing blank repos to be inspected
        #
        #         maybe we want this but only for role types for backwards
        #         compat
        #
        # if role_file and self.args and role.name not in self.args:
        #    display.vvv('Skipping role %s' % role.name)
        #    continue

        log.debug('Processing %s as %s', content.name, content.content_type)

        # FIXME - Unsure if we want to handle the install info for all galaxy
        #         content. Skipping for non-role types for now.
        if content.content_type == "role":
            if content.install_info is not None:
                if content.install_info['version'] != content.version or force_overwrite:
                    if force_overwrite:
                        display_callback('- changing role %s from %s to %s' %
                                         (content.name, content.install_info['version'], content.version or "unspecified"))
                        content.remove()
                    else:
                        log.warn('- %s (%s) is already installed - use --force to change version to %s',
                                 content.name, content.install_info['version'], content.version or "unspecified")
                        continue
                else:
                    if not force_overwrite:
                        display_callback('- %s is already installed, skipping.' % str(content))
                        continue

        try:
            installed = content.install(force_overwrite=force_overwrite)
        except exceptions.GalaxyError as e:
            log.warning("- %s was NOT installed successfully: %s ", content.name, str(e))
            raise_without_ignore(e)
            continue

        if not installed:
            log.warning("- %s was NOT installed successfully.", content.name)
            raise_without_ignore()

        if no_deps:
            log.warning('- %s was installed but any deps will not be installed because of no_deps',
                        content.name)

        # oh dear god, a dep solver...

        # FIXME: should install all of init 'deps', then build a list of new deps, and repeat

        # install dependencies, if we want them
        # FIXME - Galaxy Content Types handle dependencies in the GalaxyContent type itself because
        #         a content repo can contain many types and many of any single type and it's just
        #         easier to have that introspection there. In the future this should be more
        #         unified and have a clean API
        if content.content_type == "role":
            if not no_deps and installed:
                if not content.metadata:
                    log.warning("Meta file %s is empty. Skipping dependencies.", content.path)
                else:
                    role_dependencies = content.metadata.get('dependencies') or []
                    for dep in role_dependencies:
                        log.debug('Installing dep %s', dep)
                        dep_info = yaml_parse(dep)
                        dep_role = GalaxyContent(galaxy_context, **dep_info)
                        if '.' not in dep_role.name and '.' not in dep_role.src and dep_role.scm is None:
                            # we know we can skip this, as it's not going to
                            # be found on galaxy.ansible.com
                            continue
                        if dep_role.install_info is None:
                            if dep_role not in requested_contents:
                                display_callback('- adding dependency: %s' % str(dep_role))
                                requested_contents.append(dep_role)
                            else:
                                display_callback('- dependency %s already pending installation.' % dep_role.name)
                        else:
                            if dep_role.install_info['version'] != dep_role.version:
                                log.warning('- dependency %s from role %s differs from already installed version (%s), skipping',
                                            str(dep_role), content.name, dep_role.install_info['version'])
                            else:
                                display_callback('- dependency %s is already installed, skipping.' % dep_role.name)

    return 0
