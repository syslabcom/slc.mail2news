from Acquisition import aq_inner, aq_parent
from DateTime import DateTime
from Products.Archetypes.event import ObjectInitializedEvent
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView
from datetime import date
from plone.app.textfield.value import RichTextValue
from plone.i18n.normalizer.interfaces import IUserPreferredURLNormalizer
from plone.namedfile import NamedBlobImage
import StringIO, re, rfc822, mimetools, email, multifile
import logging
import zope.event

log = logging.getLogger('slc.mail2news')

conf_dict = { 'keepdate': 0 }

# Simple return-Codes for web-callable-methods for the smtp2zope-gate
TRUE = "TRUE"
FALSE = "FALSE"

# mail-parameter in the smtp2http-request
MAIL_PARAMETER_NAME = "Mail"


def wrap_line(line):
    idx = line.rfind(' ', 0, 50)
    if idx < 0:
        return line
    return line[:idx] + '\n' + wrap_line(line[idx+1:])


class MailHandler(BrowserView):

    def __call__(self):
        """ Handles mail received in request
        """
        #TODO: add this, seems to make sense
        #if self.checkMail(self.request):
        #    return FALSE

        obj = self.addMail(self.getMailFromRequest(self.request))
        event = ObjectInitializedEvent(obj, self.request)
        zope.event.notify(event)

        msg = 'Created news item %s' % ('/'.join([self.context.absolute_url(), obj.getId()]))
        log.info(msg)
        return msg

    def addMail(self, mailString):
        """ Store mail as news item
            Returns created item
        """

        pw = self.context.portal_workflow

        (header, body) = splitMail(mailString)

        # if 'keepdate' is set, get date from mail,
        # XXX 'time' is unused
        if self.getValueFor('keepdate'):
            timetuple = rfc822.parsedate_tz(header.get('date'))
            time = DateTime(rfc822.mktime_tz(timetuple))
        # ... take our own date, clients are always lying!
        else:
            time = DateTime()

        (TextBody, ContentType, HtmlBody, Attachments) = unpackMail(mailString)

        # Test Zeitangabe hinter Subject
        today = date.today()
        mydate = today.strftime("%d.%m.%Y")

        # let's create the news item

        subject = mime_decode_header(header.get('subject', 'No Subject'))
        sender = mime_decode_header(header.get('from', 'No From'))
        title = "%s" % (subject)

        new_id = IUserPreferredURLNormalizer(self.request).normalize(title)
        id = self._findUniqueId(new_id)
        # ContentType is only set for the TextBody
        if ContentType:
            body = TextBody
        else:
            body = self.HtmlToText(HtmlBody)

        # XXX als vorlaeufige Loesung
        desc = "%s..." % (body[:60])
        body = '\n'.join([wrap_line(line) for line in body.splitlines()])
        uni_aktuell_body = ("<p><strong>%s: %s</strong></p> "
                            "<p>&nbsp;</p><pre>%s</pre>" % (
                                mydate, sender, body))

        objid = self.context.invokeFactory(
            'News Item',
            id=id,
            title=title,
            text=RichTextValue(uni_aktuell_body),
            description=desc,
        )

        mailObject = getattr(self.context, objid)
        images = [att for att in Attachments
                  if att['maintype'] == 'image' and att['filename']]
        if images and hasattr(mailObject, 'image'):
            image = Attachments[0]
            mailObject.image = NamedBlobImage(
                filename=safe_unicode(image['filename']),
                data=image['filebody'],
            )
        try:
            pw.doActionFor(mailObject, 'publish')
        except Exception as e:
            log.exception(e)
        return mailObject

    def _findUniqueId(self, id):
        """Find a unique id in the parent folder, based on the given id, by
        appending -n, where n is a number between 1 and the constant
        RENAME_AFTER_CREATION_ATTEMPTS, set in config.py. If no id can be
        found, return None.
        """
        from Products.Archetypes.config import RENAME_AFTER_CREATION_ATTEMPTS
        parent = aq_parent(aq_inner(self))
        parent_ids = parent.objectIds()

        def check_id(id, required):
            return id in parent_ids

        invalid_id = check_id(id, required=1)
        if not invalid_id:
            return id

        idx = 1
        while idx <= RENAME_AFTER_CREATION_ATTEMPTS:
            new_id = "%s-%d" % (id, idx)
            if not check_id(new_id, required=1):
                return new_id
            idx += 1

        return None

    def getMailFromRequest(self, REQUEST):
        # returns the Mail from the REQUEST-object as string

        return str(REQUEST[MAIL_PARAMETER_NAME])

    def getValueFor(self, key):
        return conf_dict[key]


def splitMail(mailString):
    """ returns (header,body) of a mail given as string
    """
    msg = mimetools.Message(StringIO.StringIO(str(mailString)))

    # Get headers
    mailHeader = {}
    for (key, value) in msg.items():
        mailHeader[key] = value

    # Get body
    msg.rewindbody()
    mailBody = msg.fp.read()

    return (mailHeader, mailBody)


def unpackMail(mailString):
    """ returns body, content-type, html-body and attachments for mail-string.
    """
    return unpackMultifile(multifile.MultiFile(StringIO.StringIO(mailString)))


def unpackMultifile(multifile, attachments=None):
    """ Unpack multifile into plainbody, content-type, htmlbody and
    attachments.
    """
    if attachments is None:
        attachments = []
    textBody = htmlBody = contentType = ''

    msg = mimetools.Message(multifile)
    maintype = msg.getmaintype()
    subtype = msg.getsubtype()

    name = msg.getparam('name')

    if not name:
        # Check for disposition header (RFC:1806)
        disposition = msg.getheader('Content-Disposition')
        if disposition:
            matchObj = re.search(r'(?i)filename="*(?P<filename>[^\s"]*)"*',
                                 disposition)
            if matchObj:
                name = matchObj.group('filename')

    # Recurse over all nested multiparts
    if maintype == 'multipart':
        multifile.push(msg.getparam('boundary'))
        multifile.readlines()
        while not multifile.last:
            multifile.next()

            (tmpTextBody, tmpContentType, tmpHtmlBody, tmpAttachments) = \
                unpackMultifile(multifile, attachments)

            # Return ContentType only for the plain-body of a mail
            if tmpContentType and not textBody:
                textBody = tmpTextBody
                contentType = tmpContentType

            if tmpHtmlBody:
                htmlBody = tmpHtmlBody

            if tmpAttachments:
                attachments = tmpAttachments

        multifile.pop()
        return (textBody, contentType, htmlBody, attachments)

    # Process MIME-encoded data
    plainfile = StringIO.StringIO()

    try:
        mimetools.decode(multifile, plainfile, msg.getencoding())
    # unknown or no encoding? 7bit, 8bit or whatever... copy literal
    except ValueError:
        mimetools.copyliteral(multifile, plainfile)

    body = plainfile.getvalue()
    plainfile.close()

    # Get plain text
    if maintype == 'text' and subtype == 'plain' and not name:
        textBody = body
        contentType = msg.get('content-type', 'text/plain')
    else:
        # No name? This should be the html-body...
        if not name:
            name = '%s.%s' % (maintype, subtype)
            htmlBody = body

        attachments.append({'filename': mime_decode_header(name),
                            'filebody': body,
                            'maintype': maintype,
                            'subtype': subtype})

    return (textBody, contentType, htmlBody, attachments)


def mime_decode_header(header):
    """ Returns the unfolded and undecoded header
    """
    # unfold the header
    header = re.sub(r'\r?\n\s+', ' ', header)

    # different naming between python 2.4 and 2.6?
    if hasattr(email, 'header'):
        header = email.header.decode_header(header)
    else:
        header = email.Header.decode_header(header)

    headerout = []
    for line in header:
        if line[1]:
            line = line[0].decode(line[1])
        else:
            line = line[0]
        headerout.append(line)
    return '\n'.join(headerout)
