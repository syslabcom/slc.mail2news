[![Build Status](https://travis-ci.org/syslabcom/slc.mail2news.svg?branch=master)](https://travis-ci.org/syslabcom/slc.mail2news)

Introduction
============

slc.mail2news is a simple way to convert emails to Plone News Items. The MailHandler browser view receives mails as formatted by smtp2zope.py and creates the item. 

Plone 4 is recommended for using this packages. For Plone 3, additional packages like collective.contentrules.mail might be required to use the full functionality.

Setup
=====

There are two ways to invoke the mail handler, as a browser view or as a console script:

As a browser view
-----------------

    cat testmail.txt | python smtp2zope.py "http://user:pass@localhost:8010/Plone/news/@@mail_handler"

To forward all emails sent to a certain address, create an alias for your mail program similar to this:

    foo: "| python smtp2zope.py http://user:pass@localhost:8010/Plone/news/@@mail_handler"

where foo@domain is the address the emails will be sent to.

Replace localhost:8010 with your server name and port and user:pass with the credentials of a Plone user with the permission to add portal content in the folder where mail_handler is called (here /Plone/news, but can be any folder in principle). Use http://localhost:8010/Plone/@@usergroup-userprefs to create a user and http://localhost:8010/Plone/news/@@sharing to set permissions.


As a console script
-------------------

In your buildout.cfg:

    [buildout]
    parts +=
        mail_handler

    [mail_handler]
    recipe = zc.recipe.egg
    eggs =
        ${instance:eggs}
        slc.mail2news
    scripts = mail_handler
    arguments = '${instance:location}/etc/zope.conf','admin',context_path=context_path
    initialization =
        import sys
        context_path = sys.argv[1]
        sys.argv = sys.argv[:1]

Replace 'admin' with a user that has permission to add portal content in the folder where mail_handler is going to be called.

Then call the script like this:

    cat testmail.txt | bin/mail_handler /Plone/news

The alias for your mail program then looks something like this:

    foo: "| bin/mail_handler /Plone/news

You may have to specify the full path to the script.


Notification
------------

To receive a notification whenever a mail is received and converted, first create a content rule (http://localhost:8010/Plone/@@rules-controlpanel) and choose "Object added to container" as the trigger event. After the rule has been created, edit it and add the action "Send email". Fill in subject, address and body. Add a condition and restrict content type to News Item, otherwise the notification will be active for everything you add to the site.
Then you can add the rule to the folder where your News Items will reside (http://localhost:8010/Plone/news/@@manage-content-rules). Remember to configure email in the portal setup if you haven't done so yet (http://localhost:8010/Plone/@@mail-controlpanel).


References and Acknowledgements
-------------------------------

slc.mail2news is based on MailBoxer http://iungo.org/products/MailBoxer

smtp2zope.py can be found at http://svn.plone.org/svn/collective/MailBoxerTempDev/trunk/smtp2zope.py
