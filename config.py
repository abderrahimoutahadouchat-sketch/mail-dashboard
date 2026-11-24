# Configuration du serveur SMTP (envoi)
smtp_server = 'smtp.gmail.com'
smtp_port = 587

# Configuration du serveur IMAP (reception)
imap_server = 'imap.gmail.com'

# Compte mail (pour Gmail : mot de passe d'application)
sender_email = 'abderrahimoutahadouchat@gmail.com'
sender_password = 'votre_mot_de_passe'

# Adresse qui recoit les alertes
alert_email = 'abderrahimoutahadouchat@gmail.com'

# Fichiers de donnees
EMAILS_CSV = 'data/emails.csv'
ALERTES_CSV = 'data/alertes.csv'

# Mots-cles qui declenchent une alerte
mots_cles_alerte = ['urgent', 'important', 'deadline', 'paiement', 'erreur']

# Categories : chaque categorie a une liste d'expressions regulieres
categories = {
    'factures': [r'facture', r'invoice', r'paiement', r'montant'],
    'projets': [r'projet', r'r[ée]union', r'livrable', r'github'],
    'etudes': [r'cours', r'examen', r'\btd\b', r'devoir', r'\.ac\.ma'],
    'promotions': [r'promo', r'offre', r'newsletter', r'soldes', r'-\d+ ?%'],
    'personnel': [r'salut', r'famille', r'anniversaire', r'week-?end'],
}
