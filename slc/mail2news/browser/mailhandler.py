import email
import logging
import re
import six
from datetime import date

import zope.event
from Acquisition import aq_inner, aq_parent
from plone import api
from plone.app.textfield.value import RichTextValue
from plone.i18n.normalizer.interfaces import IUserPreferredURLNormalizer
from plone.namedfile import NamedBlobImage
from Products.CMFPlone.utils import safe_unicode
from Products.Five import BrowserView

try:
    from Products.Archetypes.config import RENAME_AFTER_CREATION_ATTEMPTS
    from Products.Archetypes.event import ObjectInitializedEvent

    HAVE_ARCHETYPES = True
except ImportError:
    RENAME_AFTER_CREATION_ATTEMPTS = 100
    HAVE_ARCHETYPES = False
try:
    import plone.app.contenttypes

    plone.app.contenttypes
    HAVE_PAC = True
except ImportError:
    HAVE_PAC = False

log = logging.getLogger("slc.mail2news")

# Simple return-Codes for web-callable-methods for the smtp2zope-gate
TRUE = "TRUE"
FALSE = "FALSE"

# mail-parameter in the smtp2http-request
MAIL_PARAMETER_NAME = "Mail"


def wrap_line(line):
    idx = line.rfind(" ", 0, 50)
    if idx < 0:
        return line
    return line[:idx] + "\n" + wrap_line(line[idx + 1 :])


class MailHandler(BrowserView):
    def __call__(self):
        """ Handles mail received in request
        """
        # TODO: add this, seems to make sense
        # if self.checkMail(self.request):
        #    return FALSE

        obj = self.addMail(self.getMailFromRequest(self.request))
        if obj:
            if HAVE_ARCHETYPES:
                event = ObjectInitializedEvent(obj, self.request)
                zope.event.notify(event)

            msg = "Created news item %s" % (
                "/".join([self.context.absolute_url(), obj.getId()])
            )
            log.info(msg)
            return msg

    def addMail(self, mailstring):
        """ Store mail as news item
            Returns created item
        """
        pw = self.context.portal_workflow

        if six.PY3 and isinstance(mailstring, bytes):
            parser = email.parser.BytesFeedParser()
        else:
            parser = email.parser.FeedParser()
        parser.feed(mailstring)
        msg = parser.close()

        # FLOW-555
        ignore = msg.get("x-mailin-ignore", "false")
        if ignore == "true":
            log.info("X-mailin-ignore header detected, ignoring email")
            return

        (TextBody, ContentType, HtmlBody, Attachments) = unpackMail(msg)

        # Test Zeitangabe hinter Subject
        today = date.today()
        mydate = today.strftime("%d.%m.%Y")

        # let's create the news item

        raw_subject = msg.get("subject", "No Subject")
        subject_parts = email.header.decode_header(raw_subject)
        if six.PY3:
            separator = ""
        else:
            # Bit weird: on python 2, spaces between the parts seem to vanish
            separator = " "
        subject = separator.join(
            [
                safe_unicode(subject_part, encoding=subject_charset or "utf-8")
                for subject_part, subject_charset in subject_parts
            ]
        )

        sender = msg.get("from", "No From")
        title = "%s" % (subject)

        new_id = IUserPreferredURLNormalizer(self.request).normalize(title)
        id = self._findUniqueId(new_id)
        # ContentType is only set for the TextBody
        if ContentType:
            body = TextBody
        else:
            body = self.HtmlToText(HtmlBody)

        # XXX als vorlaeufige Loesung
        plone_view = api.content.get_view(
            context=self.context, request=self.request, name="plone"
        )
        desc = plone_view.cropText(body, 60)
        body = "\n".join([wrap_line(line) for line in body.splitlines()])
        uni_aktuell_body = (
            "<p><strong>%s: %s</strong></p> "
            "<p>&nbsp;</p><pre>%s</pre>" % (mydate, sender, body)
        )
        if HAVE_PAC:
            uni_aktuell_body = RichTextValue(uni_aktuell_body)

        objid = self.context.invokeFactory(
            "News Item", id=id, title=title, text=uni_aktuell_body, description=desc
        )

        mailObject = getattr(self.context, objid)
        images = [
            att for att in Attachments if att["maintype"] == "image" and att["filename"]
        ]
        if images:
            image = images[0]
            if hasattr(mailObject, "image"):
                mailObject.image = NamedBlobImage(
                    filename=safe_unicode(image["filename"]), data=image["filebody"]
                )
            elif hasattr(mailObject, "setImage"):
                mailObject.setImage(image["filebody"], filename=image["filename"])
        try:
            pw.doActionFor(mailObject, "publish")
        except Exception as e:
            log.exception(e)
        return mailObject

    def _findUniqueId(self, id):
        """Find a unique id in the parent folder, based on the given id, by
        appending -n, where n is a number between 1 and the constant
        RENAME_AFTER_CREATION_ATTEMPTS, set in config.py. If no id can be
        found, return None.
        """
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


def unpackMail(msg):
    """ returns body, content-type, html-body and attachments for mail.
    """
    attachments = []
    textBody = htmlBody = contentType = ""

    name = msg.get_filename

    if not name:
        # Check for disposition header (RFC:1806)
        disposition = msg.getheader("Content-Disposition")
        if disposition:
            matchObj = re.search(r'(?i)filename="*(?P<filename>[^\s"]*)"*', disposition)
            if matchObj:
                name = matchObj.group("filename")

    # Iterate over all nested multiparts
    for part in msg.walk():
        if part.is_multipart():
            continue

        name = part.get_filename()
        decode = part.get("Content-Transfer-Encoding") in ["quoted-printable", "base64"]
        payload = part.get_payload(decode=decode)
        part_encoding = part.get_content_charset() or "utf-8"

        # Get plain text
        if part.get_content_type() == "text/plain" and not name and not textBody:
            textBody = safe_unicode(payload, encoding=part_encoding)
            # Return ContentType only for the plain-body of a mail
            contentType = part.get_content_type()
        else:
            maintype = part.get_content_maintype()
            subtype = part.get_content_subtype()
            # No name? This should be the html-body...
            if not name:
                name = "%s.%s" % (maintype, subtype)
                htmlBody = safe_unicode(payload, encoding=part_encoding)

            attachments.append(
                {
                    "filename": name,
                    "filebody": payload,
                    "maintype": maintype,
                    "subtype": subtype,
                }
            )

    return (textBody, contentType, htmlBody, attachments)
