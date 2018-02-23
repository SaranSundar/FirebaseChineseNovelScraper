#!/usr/bin/python3
# Libraries
import email
import smtplib
from subprocess import call
from subprocess import check_output
from timeit import default_timer as timer

import firebase_admin
import google as google
from firebase_admin import credentials, firestore
from lxml import html
from pyfcm import FCMNotification

links = {}

cred = credentials.Certificate("./serviceAccountKey.json")
default_app = firebase_admin.initialize_app(cred)
db = firestore.client()
docs = db.collection(u"Links")
doc_ref = docs.document(u"links")

# This registration token comes from the client FCM SDKs.
registration_token = 'cDW-iYnBvnc:APA91bFKKqcvaJn4uA4-Jy3FkJEOPkT445bB-NKagl-V6YnNLH12wEsQev6Pyv_IQ0O7LZSQCPuGLQNa0rgTOefgirwvPQS5XKf_RUIMnfzx9BawvZL77vxOry4SsqdJvM-q_lVAuJ0U'

# Send to single device.
push_service = FCMNotification(
    api_key="AAAADRm-nuw:APA91bG-_D6l6ASne2zMqTmPrwuRYUrFHu_I_EOlOV4a5GIH084SUGBvqJEAz3DnR9EzkARaNLlL63OYaERLPwFEoxfbtgjMagwnB5gr0iMtKK0xeG_53aFzq3E2ch8q2Oz4qp7CEz1e")


# Download html pages to process later
def downloadsLinks():
    global links
    # print(links)
    call(["./updater.sh"])
    startIndex = len("https://www.novelupdates.com/series/")
    for i in range(len(links)):
        if i > 0:
            url = "websites/index.html." + str(i)
        else:
            url = "websites/index.html"
        with open(url, "r") as f:
            page = f.read()
            f.close()
        tree = html.fromstring(page)
        link_name = links[i][1]
        chapter_name = str(tree.xpath('//*[@id="myTable"]/tbody/tr[1]/td[3]/a[2]/text()'))[2:-2]
        # print(link_name)
        link_name = link_name[startIndex:-1]
        link_name = link_name.replace("-", "_")
        link_name = link_name.replace("/", "_")
        links[i] = (chapter_name, link_name.capitalize())
        # print(chapter_name)
        # Compare chapters to the ones in database, add to list to email if newer and update database


def compareChapters():
    global links
    chapters_ref = db.collection(u"Links").document(u"latest_chapters")
    try:
        chapters = chapters_ref.get()
        chapters = chapters.to_dict()
        updateChapters(old_chapters=chapters, chapters_ref=chapters_ref)
    except google.cloud.exceptions.NotFound:
        print(u'Creating document')
        chapters = {}
        updateChapters(old_chapters=chapters, chapters_ref=chapters_ref)


def updateChapters(old_chapters, chapters_ref):
    new_chapters = {}
    for items in links:
        # Checks if book link is in old list of books
        if not items[1] in old_chapters:
            new_chapters[items[1]] = items[0]
        # Checks if chapter of book in old list is same as in new list
        elif old_chapters[items[1]] != items[0]:
            new_chapters[items[1]] = items[0]
    new_chapters_count = len(new_chapters)
    if new_chapters_count > 0:
        status_updated = emailUpdatedChapters(new_chapters)
        if status_updated:
            chapters_ref.update(new_chapters, firestore.firestore.CreateIfMissingOption(True))
            print(str(new_chapters_count) + " New Chapters!")
            message_title = "New Chapters!"
            message_body = "You have " + str(new_chapters_count) + " new chapters available"
            # result = push_service.notify_single_device(registration_id=registration_token, message_title=message_title,
            # message_body=message_body, low_priority=False)
            # print("Push Notification " + str(result))
        else:
            print("Did not update DB because email failed...")
    else:
        print("No New Chapters")


def emailUpdatedChapters(chapters):
    print("Sending email...")
    try:
        curatedChapters = ""
        for key, value in chapters.items():
            linkKey = key.replace("_", "-")
            curatedChapters += "<a href=\"https://www.novelupdates.com/series/" + linkKey + "\"><h5>" + key + " " + value + "</h5></a>" + ""
        email_content = """
              <html>
              <head>

             <title>New Chapters</title>
             <style type="text/css">
              a {color: #d80a3e;}
            body, #header h1, #header h2, p {margin: 0; padding: 0;}
            #main {border: 1px solid #cfcece;}
            img {display: block;}
            #top-message p, #bottom p {color: #3f4042; font-size: 12px; font-family: Arial, Helvetica, sans-serif; }
            #header h1 {color: #ffffff !important; font-family: "Lucida Grande", sans-serif; font-size: 24px; margin-bottom: 0!important; padding-bottom: 0; }
            #header p {color: #ffffff !important; font-family: "Lucida Grande", "Lucida Sans", "Lucida Sans Unicode", sans-serif; font-size: 12px;  }
            h5 {margin: 0 0 0.8em 0;}
              h5 {font-size: 15px; color: #0CAFF1 !important; font-family: Arial, Helvetica, sans-serif; }
            p {font-size: 12px; color: #444444 !important; font-family: "Lucida Grande", "Lucida Sans", "Lucida Sans Unicode", sans-serif; line-height: 1.5;}
             </style>
              </head>
              <body>
              <table id="main" width="600" align="center" cellpadding="0" cellspacing="15" bgcolor="ffffff">
              <tr>
                <td>
                  <table id="header" cellpadding="10" cellspacing="0" align="center" bgcolor="8fb3e9">
                    <tr>
                      <td width="570" align="center"  bgcolor="#d80a3e"><h1>New Chapters</h1></td>
                    </tr>
                    <tr>
                      <td width="570" align="right" bgcolor="#d80a3e"><p>2018</p></td>
                    </tr>
                  </table>
                </td>
              </tr>
              </table>
               """ + curatedChapters + """
              </body>
              </html>
              """
        fromAddr = 'saran@nilal.com'
        toAddrs = 'saran@nilal.com'

        msg = email.message.Message()
        date = check_output(["date"])
        msg['Subject'] = str(len(chapters)) + " New Chapters " + date.decode('utf-8')

        msg['From'] = fromAddr
        msg['To'] = toAddrs
        password = "password here"
        msg.add_header('Content-Type', 'text/html')
        msg.set_payload(email_content)

        s = smtplib.SMTP('smtp.gmail.com: 587')
        s.starttls()

        # Login Credentials for sending the mail
        s.login(msg['From'], password)

        s.sendmail(msg['From'], [msg['To']], msg.as_string())
        s.quit()

        print("Email sent!")
        return True
    except:
        print("Email failed to send...")
        return False

    # msg = MIMEMultipart('alternative')
    # msg['Subject'] = "New Chapter(s) Available " + '{0:%Y-%m-%d %I:%M:%S %p}'.format(datetime.datetime.now())
    # msg['From'] = "SaranFrom"  # like name
    # msg['To'] = "SaranTo"
    #
    # body = MIMEText(txt)
    # msg.attach(body)
    #
    # username = 'saran@nilal.com'
    # password = 'password here'
    # server = smtplib.SMTP_SSL('smtp.googlemail.com', 465)
    # server.login(username, password)
    # server.sendmail(fromAddr, toAddrs, msg.as_string())
    # server.quit()


def readLinksFromDB():
    global links
    # Then query for documents
    snapshot = doc_ref.get()
    snapshot = snapshot.to_dict()
    links = [(k, v) for k, v in snapshot.items()]
    links = sorted(links, key=lambda x: int(x[0]))
    with open('linksfromdb.txt', 'w') as f:
        for key, value in links:
            # print(key)
            f.write(value + "\n")
        f.close()
    # print(u'Document data: {}'.format(snapshot.to_dict()))


# Only to be called once, otherwise directly modify links in Firestore console
def pushLinksToDB():
    global links
    links = []
    with open('links.txt', 'r') as f:
        for line in f:
            links.append(line.strip())
        f.close()
    links = {str(ind): link for ind, link in enumerate(links)}
    doc_ref.set(links)
    print("Successfully Written")


def main():
    # pushLinksToDB()
    start = timer()
    readLinksFromDB()
    downloadsLinks()
    compareChapters()
    end = timer()
    print(str(end - start) + "seconds to execute all code")


main()
