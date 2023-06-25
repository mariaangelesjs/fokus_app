from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

def send_email(user, password, sendto_name, sendto_mail, subject, content):
    msg = MIMEMultipart()
    msg['From'] = 'Bas Analyse'
    msg['To'] = sendto_name
    msg['Subject'] = subject
    message = content
    msg.attach(MIMEText(message))
    mailserver = smtplib.SMTP('smtp.office365.com',587)
    # identify ourselves to smtp gmail client
    mailserver.ehlo()
    # secure our email with tls encryption
    mailserver.starttls()
    # re-identify ourselves as an encrypted connection
    mailserver.ehlo()
    mailserver.login(user, password)
    mailserver.sendmail(user,sendto_mail,msg.as_string())
    mailserver.quit()