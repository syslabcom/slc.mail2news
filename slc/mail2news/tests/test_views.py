import unittest
from plone import api
from plone.app.testing import helpers, SITE_OWNER_NAME
from slc.mail2news.browser.mailhandler import unpackMail
from slc.mail2news.testing import INTEGRATION_TESTING
from slc.mail2news.testing import load_mail_msg
from slc.mail2news.testing import load_mail_str


class TestMailHandler(unittest.TestCase):
    layer = INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer["portal"]
        self.request = self.layer["request"]

    def get_text(self, obj):
        if hasattr(obj, "text"):
            return obj.text.output
        else:
            return obj.getText()

    def get_image(self, obj):
        if hasattr(obj, "image"):
            return obj.image
        else:
            return obj.getImage()

    def test_mail_handler_ignore(self):
        mail = load_mail_str("mail_plain_ignore.txt")
        request = self.request.clone()
        request["Mail"] = mail
        helpers.login(self.layer["app"], SITE_OWNER_NAME)
        view = api.content.get_view(
            context=self.portal, request=request, name="mail_handler"
        )
        msg = view()
        self.assertIsNone(msg)
        self.assertEquals(
            [
                obj
                for obj in view.context.objectValues()
                if obj.portal_type == "News Item"
            ],
            [],
        )

    def test_mail_handler_plain(self):
        mail = load_mail_str("mail_plain.txt")

        request = self.request.clone()
        request["Mail"] = mail
        helpers.login(self.layer["app"], SITE_OWNER_NAME)
        view = api.content.get_view(
            context=self.portal, request=request, name="mail_handler"
        )
        msg = view()
        self.assertIn("Created news item ", msg)
        path = msg.replace("Created news item http://nohost", "")
        obj = self.portal.unrestrictedTraverse(path)

        text = self.get_text(obj)
        self.assertIn("Test\n*31*", text)
        self.assertNotIn("Message-ID:", text)

    def test_mail_handler_plain_with_image(self):
        mail = load_mail_str("mail_plain_with_image.txt")

        request = self.request.clone()
        request["Mail"] = mail
        helpers.login(self.layer["app"], SITE_OWNER_NAME)
        view = api.content.get_view(
            context=self.portal, request=request, name="mail_handler"
        )
        msg = view()
        self.assertIn("Created news item ", msg)
        path = msg.replace("Created news item http://nohost", "")
        obj = self.portal.unrestrictedTraverse(path)

        text = self.get_text(obj)
        self.assertIn("This is a test with an image", text)
        self.assertNotIn("Message-ID:", text)

        image = self.get_image(obj)
        self.assertEqual(image.filename, "pixel.png")
        self.assertIn(b"PNG", image.data[:4])


class TestMailHandlerUnit(unittest.TestCase):
    def test_unpack_message_plain(self):
        mail = load_mail_msg("mail_plain.txt")
        text_body, content_type, html_body, attachments = unpackMail(mail)
        self.assertIn("Test *31*", text_body)
        self.assertIn("_bla bla_", text_body)
        self.assertEqual(content_type, "text/plain")
        self.assertEqual(html_body, "")
        self.assertEqual(attachments, [])

    def test_unpack_message_plain_with_image(self):
        mail = load_mail_msg("mail_plain_with_image.txt")
        text_body, content_type, html_body, attachments = unpackMail(mail)
        self.assertIn("This is a test with an image attached.", text_body)
        self.assertEqual(content_type, "text/plain")
        self.assertEqual(html_body, "")
        self.assertEqual(attachments[0]["filename"], "pixel.png")
        self.assertEqual(attachments[0]["maintype"], "image")
        self.assertEqual(attachments[0]["subtype"], "png")

    def test_unpack_message_mixed(self):
        mail = load_mail_msg("mail_mixed.txt")
        text_body, content_type, html_body, attachments = unpackMail(mail)
        self.assertIn("Test *31*", text_body)
        self.assertEqual(content_type, "text/plain")
        self.assertIn("Test <b>31</b>", html_body)
        images = [
            att for att in attachments if att["maintype"] == "image" and att["filename"]
        ]
        self.assertEqual(images[0]["filename"], "pixel.gif")
        self.assertEqual(images[0]["maintype"], "image")
        self.assertEqual(images[0]["subtype"], "gif")
