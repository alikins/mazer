import mimetypes
import io
import uuid

from ansible_galaxy.utils.text import to_bytes


class MultiPartForm(object):
    """
    Accumulate the data to be used when posting a form.
    Borrowed from https://blog.thesparktree.com/the-unfortunately-long-story-dealing-with
    """

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = '--------------------------%s' % uuid.uuid4().hex
        return

    def __repr__(self):
        return 'MultiPartForm(form_fields=%s, files=%s, boundary="%s")' \
            % (self.form_fields, [f[0:2] for f in self.files], self.boundary)

    def linesgen(self, summarize=False):
        part_boundary = '--' + self.boundary
        part_boundary_end = '--' + self.boundary + '--'

        for name, value in self.form_fields:
            yield part_boundary
            yield 'Content-Disposition: form-data; name="%s"' % name
            yield value

        # TODO: we could potentially compute the content-length first, without
        #       creating the whole buffer and then stream the file bodies, if
        #       memory use becomes an issue.
        for field_name, filename, content_type, body in self.files:
            yield part_boundary
            yield 'Content-Disposition: file; name="%s"; filename="%s"' % (field_name, filename)
            yield 'Content-Type: %s' % content_type
            if summarize:
                yield '< the %s bytes body of %s here >' % (len(body), filename)
            else:
                yield body

        yield part_boundary_end

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, fileHandle, mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return

    def get_binary(self):
        """Return a binary buffer containing the form data, including attached files."""
        part_boundary = '--' + self.boundary

        binary = io.BytesIO()
        needsCLRF = False
        # Add the form fields
        for name, value in self.form_fields:
            if needsCLRF:
                binary.write(str.encode('\r\n', 'utf-8'))
            needsCLRF = True

            block = [part_boundary,
                     'Content-Disposition: form-data; name="%s"' % name,
                     '',
                     value
                     ]
            binary.write(str.encode('\r\n'.join(block), 'utf-8'))

        # Add the files to upload
        for field_name, filename, content_type, body in self.files:
            if needsCLRF:
                binary.write(str.encode('\r\n', 'utf-8'))
            needsCLRF = True

            block = [part_boundary,
                     str('Content-Disposition: file; name="%s"; filename="%s"' %
                         (field_name, filename)),
                     'Content-Type: %s' % content_type,
                     ''
                     ]
            binary.write(str.encode('\r\n'.join(block), 'utf-8'))
            binary.write(str.encode('\r\n', 'utf-8'))
            binary.write(body)

        # add closing boundary marker,
        binary.write(str.encode('\r\n--' + self.boundary + '--\r\n', 'utf-8'))
        return binary
