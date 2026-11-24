"""Genere des mails fictifs dans data/ pour tester le tableau de bord sans compte mail."""
import random
from datetime import datetime, timedelta
import pandas as pd

import config
from mail_functions import classer_email, chercher_mot_cle

recus = [
    ('service@iam.ma', 'Votre facture du mois', 'Le montant de votre facture est de 199 DH.'),
    ('noreply@jumia.ma', 'Soldes : -40% sur les ordinateurs', 'Profitez de notre offre.'),
    ('prof@enset-media.ac.ma', 'TD 3 Python', 'Le devoir est a rendre vendredi.'),
    ('scolarite@enset-media.ac.ma', 'Planning des examens', 'Le planning des examens est disponible.'),
    ('notifications@github.com', 'Nouvelle issue sur votre projet', 'Une issue a ete ouverte.'),
    ('mohamed@gmail.com', 'Reunion projet demain', 'On se voit a 10h pour le livrable.'),
    ('ahmed@gmail.com', 'Salut', 'On joue ce week-end ?'),
    ('admin@serveur.ma', 'Urgent : erreur sur le serveur', 'Le site ne repond plus.'),
    ('newsletter@medium.com', 'Votre newsletter', 'Les articles de la semaine.'),
    ('banque@cih.ma', 'Confirmation de paiement', 'Votre paiement a ete recu.'),
    ('rh@entreprise.ma', 'Important : documents de stage', 'Envoyez la convention avant la deadline.'),
]
envoyes = [
    ('prof@enset-media.ac.ma', 'Remise du TD 3', 'Bonjour, voici mon travail.'),
    ('mohamed@gmail.com', 'Re: Reunion projet demain', 'OK pour 10h.'),
    ('rh@entreprise.ma', 'Convention de stage', 'Ci-joint la convention.'),
]


def date_aleatoire():
    jour = datetime.now() - timedelta(days=random.randint(0, 6))
    heure = random.choice(list(range(8, 23)) * 3 + list(range(0, 8)))
    d = jour.replace(hour=heure, minute=random.randint(0, 59), second=0)
    if d > datetime.now():
        d -= timedelta(days=1)
    return d


def generer(nb_recus=70, nb_envoyes=25):
    lignes, alertes = [], []
    for i in range(nb_recus):
        exp, sujet, corps = random.choice(recus)
        d = date_aleatoire()
        lignes.append({'id': f'demo-r{i}', 'type': 'entrant', 'expediteur': exp,
                       'destinataire': config.sender_email, 'sujet': sujet, 'corps': corps,
                       'date': d.strftime('%Y-%m-%d %H:%M:%S'),
                       'categorie': classer_email(exp, sujet, corps),
                       'lu': int(random.random() > 0.3)})
        mot = chercher_mot_cle(sujet, corps)
        if mot:
            alertes.append({'date': d.strftime('%Y-%m-%d %H:%M'), 'mot_cle': mot,
                            'expediteur': exp, 'sujet': sujet})

    for i in range(nb_envoyes):
        dest, sujet, corps = random.choice(envoyes)
        lignes.append({'id': f'demo-e{i}', 'type': 'sortant', 'expediteur': config.sender_email,
                       'destinataire': dest, 'sujet': sujet, 'corps': corps,
                       'date': date_aleatoire().strftime('%Y-%m-%d %H:%M:%S'),
                       'categorie': classer_email('', sujet, corps), 'lu': 1})

    pd.DataFrame(lignes).to_csv(config.EMAILS_CSV, index=False)
    pd.DataFrame(alertes).to_csv(config.ALERTES_CSV, index=False)


if __name__ == '__main__':
    generer()
    print('Donnees de test creees dans data/')
