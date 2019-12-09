import email
import os
from contextlib import contextmanager

from plone.app.testing import (
    PLONE_FIXTURE,
    FunctionalTesting,
    IntegrationTesting,
    PloneSandboxLayer,
    applyProfile,
)


@contextmanager
def open_mailfile(filename):
    testfolder = os.path.join(os.path.split(__file__)[0], "tests")
    path = os.path.join(testfolder, filename)
    fd = open(path)
    yield fd
    fd.close()


def load_mail_str(filename):
    with open_mailfile(filename) as fd:
        return fd.read()


def load_mail_msg(filename):
    with open_mailfile(filename) as fd:
        return email.message_from_file(fd)


class SlcMail2news(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        self.plone4 = False
        try:
            import plone.app.contenttypes
        except ImportError:
            self.plone4 = True
        if not self.plone4:
            self.loadZCML("configure.zcml", package=plone.app.contenttypes)
        import slc.mail2news

        self.loadZCML("configure.zcml", package=slc.mail2news)

    def setUpPloneSite(self, portal):
        if not self.plone4:
            applyProfile(portal, "plone.app.contenttypes:default")


SLC_MAIL2NEWS_FIXTURE = SlcMail2news()
INTEGRATION_TESTING = IntegrationTesting(
    bases=(SLC_MAIL2NEWS_FIXTURE,), name="SlcMail2news:Integration"
)
FUNCTIONAL_TESTING = FunctionalTesting(
    bases=(SLC_MAIL2NEWS_FIXTURE,), name="SlcMail2news:Functional"
)
