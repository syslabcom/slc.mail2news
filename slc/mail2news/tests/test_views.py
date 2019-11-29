import unittest
from plone import api
from plone.app.testing import helpers, SITE_OWNER_NAME
from slc.mail2news.testing import INTEGRATION_TESTING
from slc.mail2news.testing import load_mail


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

    def test_mail_handler_plain(self):
        mail = load_mail("mail_plain.txt")

        request = self.request.clone()
        request["Mail"] = mail
        helpers.login(self.layer["app"], SITE_OWNER_NAME)
        view = api.content.get_view(
            context=self.portal, request=request, name="mail_handler"
        )
        msg = view()
        self.assertIn("Created news item ", msg)
        path = msg.replace('Created news item http://nohost', '')
        obj = self.portal.unrestrictedTraverse(path)

        text = self.get_text(obj)
        self.assertIn("Test\n*31*", text)
        self.assertNotIn("Message-ID:", text)

    def test_mail_handler_plain_with_image(self):
        mail = load_mail("mail_plain_with_image.txt")

        request = self.request.clone()
        request["Mail"] = mail
        helpers.login(self.layer["app"], SITE_OWNER_NAME)
        view = api.content.get_view(
            context=self.portal, request=request, name="mail_handler"
        )
        msg = view()
        self.assertIn("Created news item ", msg)
        path = msg.replace('Created news item http://nohost', '')
        obj = self.portal.unrestrictedTraverse(path)

        text = self.get_text(obj)
        self.assertIn("This is a test with an image", text)
        self.assertNotIn("Message-ID:", text)

        image = self.get_image(obj)
        self.assertEqual(image.filename, "pixel.png")
        self.assertIn("PNG", image.data[:4])
