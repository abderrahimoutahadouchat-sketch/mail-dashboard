# Tableau de bord de suivi des emails

Mini-projet Python – Séance 10 : Automatisation des emails + Tableaux de bord interactifs (Dash).

## Fonctionnalités

- Suivi des emails entrants et sortants (stockés dans `data/emails.csv`)
- Envoi d'un email personnalisé (nom, prénom, message, pièce jointe)
- Affichage des 5 derniers emails reçus
- Graphique du nombre d'emails par jour ou par heure
- Classification des emails par expressions régulières (factures, projets, etudes, promotions, personnel, autres)
- Filtrage avancé : type, catégorie, non lus, recherche par regex
- Archivage par catégorie dans `Archive/<categorie>` (copy + \Deleted + expunge)
- Système d'alerte : un email est envoyé quand un email reçu contient un mot-clé

## Structure

```
mail_dashboard/
├── app.py              # application Dash (layout + callbacks)
├── mail_functions.py   # smtplib, imaplib, email : envoi, réception, alertes, archivage
├── config.py           # serveurs, compte, mots-clés, catégories
├── demo.py             # données de test
├── assets/style.css
├── data/               # emails.csv, alertes.csv
└── requirements.txt
```

## Lancement

```
python -m venv venv
venv\Scripts\activate        (Windows)
pip install -r requirements.txt
python app.py
```

Puis ouvrir http://127.0.0.1:8050

Remplir `sender_email` et `sender_password` dans `config.py` (pour Gmail : mot de passe d'application).
Sans compte, le bouton « Données de test » permet de voir le tableau de bord avec des emails fictifs.
