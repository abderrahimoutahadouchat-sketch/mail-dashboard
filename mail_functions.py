import os
import re
import email
import imaplib
import smtplib
from datetime import datetime
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

import pandas as pd
import config

COLONNES = ['id', 'type', 'expediteur', 'destinataire', 'sujet', 'corps', 'date', 'categorie', 'lu']


# ---------------- Donnees (CSV) ----------------

def charger_emails():
    if os.path.exists(config.EMAILS_CSV):
        df = pd.read_csv(config.EMAILS_CSV)
    else:
        df = pd.DataFrame(columns=COLONNES)
    df['date'] = pd.to_datetime(df['date'])
    df['corps'] = df['corps'].fillna('')
    return df.sort_values('date', ascending=False)


def ajouter_email(ligne):
    df = charger_emails()
    if ligne['id'] in df['id'].values:
        return False
    df = pd.concat([df, pd.DataFrame([ligne])], ignore_index=True)
    df.to_csv(config.EMAILS_CSV, index=False)
    return True


def charger_alertes():
    if not os.path.exists(config.ALERTES_CSV):
        return pd.DataFrame(columns=['date', 'mot_cle', 'expediteur', 'sujet'])
    return pd.read_csv(config.ALERTES_CSV).sort_values('date', ascending=False)


def ajouter_alerte(mot_cle, expediteur, sujet):
    df = charger_alertes()
    ligne = {'date': datetime.now().strftime('%Y-%m-%d %H:%M'),
             'mot_cle': mot_cle, 'expediteur': expediteur, 'sujet': sujet}
    df = pd.concat([df, pd.DataFrame([ligne])], ignore_index=True)
    df.to_csv(config.ALERTES_CSV, index=False)


# ---------------- Classification ----------------

def classer_email(expediteur, sujet, corps):
    texte = f'{expediteur} {sujet} {corps}'.lower()
    meilleure, max_score = 'autres', 0
    for categorie, motifs in config.categories.items():
        score = 0
        for motif in motifs:
            score += len(re.findall(motif, texte))
        if score > max_score:
            meilleure, max_score = categorie, score
    return meilleure


def chercher_mot_cle(sujet, corps):
    texte = f'{sujet} {corps}'.lower()
    for mot in config.mots_cles_alerte:
        if re.search(r'\b' + mot + r'\b', texte):
            return mot
    return None


# ---------------- Envoi ----------------

def send_email(destinataire, sujet, contenu, fichier=None, nom_fichier=None, categorie=None):
    message = MIMEMultipart()
    message['From'] = config.sender_email
    message['To'] = destinataire
    message['Subject'] = sujet
    message.attach(MIMEText(contenu, 'plain'))

    # piece jointe
    if fichier:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(fichier)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename={nom_fichier}')
        message.attach(part)

    with smtplib.SMTP(config.smtp_server, config.smtp_port) as server:
        server.starttls()
        server.login(config.sender_email, config.sender_password)
        server.sendmail(config.sender_email, destinataire, message.as_string())

    maintenant = datetime.now()
    ajouter_email({
        'id': f'sortant-{maintenant.timestamp()}',
        'type': 'sortant',
        'expediteur': config.sender_email,
        'destinataire': destinataire,
        'sujet': sujet,
        'corps': contenu,
        'date': maintenant.strftime('%Y-%m-%d %H:%M:%S'),
        'categorie': categorie or classer_email('', sujet, contenu),
        'lu': 1,
    })


def envoyer_mail_personnalise(nom, prenom, destinataire, sujet, message, fichier=None, nom_fichier=None):
    contenu = f'Bonjour {prenom} {nom},\n\n{message}'
    send_email(destinataire, sujet, contenu, fichier, nom_fichier)


# ---------------- Systeme d'alerte ----------------

def alert_system(mot_cle, expediteur, sujet):
    texte = (f'Un nouveau mail contient le mot-clé "{mot_cle}".\n\n'
             f'Expéditeur : {expediteur}\nSujet : {sujet}')
    send_email(config.alert_email, f'Alerte : {sujet}', texte, categorie='alerte')
    ajouter_alerte(mot_cle, expediteur, sujet)


# ---------------- Reception ----------------

def decoder(valeur):
    if valeur is None:
        return ''
    texte, encodage = decode_header(valeur)[0]
    if isinstance(texte, bytes):
        return texte.decode(encodage or 'utf-8', errors='ignore')
    return texte


def lire_corps(msg):
    if msg.is_multipart():
        for part in msg.get_payload():
            content_disposition = str(part.get('Content-Disposition', ''))
            if part.get_content_type() == 'text/plain' and 'attachment' not in content_disposition:
                return part.get_payload(decode=True).decode(errors='ignore')
        return ''
    return msg.get_payload(decode=True).decode(errors='ignore')


def connexion_imap():
    mail = imaplib.IMAP4_SSL(config.imap_server)
    mail.login(config.sender_email, config.sender_password)
    return mail


def recevoir_emails(nombre=50):
    """Lit les derniers mails de la boite, les classe et les enregistre.
    Envoie une alerte si un nouveau mail contient un mot-cle."""
    mail = connexion_imap()
    mail.select('inbox')

    result, data = mail.search(None, 'ALL')
    email_ids = data[0].split()[-nombre:]
    result, data = mail.search(None, 'UNSEEN')
    non_lus = data[0].split()

    nouveaux, alertes = 0, 0
    for email_id in email_ids:
        result, msg_data = mail.fetch(email_id, '(BODY.PEEK[])')
        msg = email.message_from_bytes(msg_data[0][1])

        expediteur = decoder(msg['From'])
        sujet = decoder(msg['Subject'])
        corps = lire_corps(msg)
        date = pd.to_datetime(msg['Date'], utc=True, errors='coerce')
        date = datetime.now() if pd.isna(date) else date.tz_convert(None)

        ajoute = ajouter_email({
            'id': msg['Message-ID'] or email_id.decode(),
            'type': 'entrant',
            'expediteur': expediteur,
            'destinataire': config.sender_email,
            'sujet': sujet,
            'corps': corps[:2000],
            'date': date.strftime('%Y-%m-%d %H:%M:%S'),
            'categorie': classer_email(expediteur, sujet, corps),
            'lu': 0 if email_id in non_lus else 1,
        })
        if ajoute:
            nouveaux += 1
            mot = chercher_mot_cle(sujet, corps)
            if mot:
                alert_system(mot, expediteur, sujet)
                alertes += 1

    mail.logout()
    return nouveaux, alertes


# ---------------- Archivage par categorie ----------------

def archive_email(mail, email_id, dossier):
    mail.copy(email_id, dossier)
    mail.store(email_id, '+FLAGS', '\\Deleted')


def archiver_categorie(categorie):
    df = charger_emails()
    ids = df[(df['type'] == 'entrant') & (df['categorie'] == categorie)]['id'].tolist()

    mail = connexion_imap()
    dossier = f'Archive/{categorie}'
    mail.create(dossier)
    mail.select('inbox')

    total = 0
    for message_id in ids:
        result, data = mail.search(None, f'HEADER Message-ID "{message_id}"')
        for email_id in data[0].split():
            archive_email(mail, email_id, dossier)
            total += 1
    mail.expunge()
    mail.logout()
    return total
