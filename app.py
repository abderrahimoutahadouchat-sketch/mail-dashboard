import re
import base64

import dash
from dash import dcc, html, Input, Output, State
import plotly.express as px

import config
import mail_functions as mf
import demo

app = dash.Dash(__name__)
app.title = 'Suivi des emails'

couleurs = {'entrant': '#2563eb', 'sortant': '#f59e0b'}


def tableau(df, colonnes, noms):
    entete = html.Tr([html.Th(n) for n in noms])
    lignes = [html.Tr([html.Td(str(ligne[c])) for c in colonnes]) for _, ligne in df.iterrows()]
    return html.Table([html.Thead(entete), html.Tbody(lignes)], className='tableau')


def carte(titre, valeur_id):
    return html.Div([html.P(titre), html.H2(id=valeur_id)], className='carte')


# ---------------- Layout ----------------

app.layout = html.Div([
    dcc.Store(id='maj', data=0),

    html.Div([
        html.H1('Tableau de bord des emails'),
        html.Div([
            html.Button('Synchroniser', id='btn-sync'),
            html.Button('Données de test', id='btn-demo', className='secondaire'),
        ]),
    ], className='entete'),
    html.Div(id='statut', className='statut'),

    dcc.Tabs([
        dcc.Tab(label='Tableau de bord', children=[
            html.Div([
                carte('Mails reçus', 'nb-recus'),
                carte('Mails envoyés', 'nb-envoyes'),
                carte('Non lus', 'nb-non-lus'),
                carte('Alertes', 'nb-alertes'),
            ], className='cartes'),

            html.Div([
                html.H3('Nombre de mails'),
                dcc.RadioItems(id='periode', options=[{'label': ' Par jour', 'value': 'jour'},
                                                      {'label': ' Par heure', 'value': 'heure'}],
                               value='jour', inline=True),
                dcc.Graph(id='graph-activite'),
            ], className='bloc'),

            html.Div([
                html.Div([html.H3('5 derniers mails reçus'), html.Div(id='derniers-mails')],
                         className='bloc large'),
                html.Div([html.H3('Classification'), dcc.Graph(id='graph-categories')],
                         className='bloc'),
            ], className='ligne'),
        ]),

        dcc.Tab(label='Boîte mail', children=[
            html.Div([
                dcc.Dropdown(id='filtre-type', options=['entrant', 'sortant'], placeholder='Type'),
                dcc.Dropdown(id='filtre-categorie', multi=True, placeholder='Catégorie'),
                dcc.Input(id='filtre-texte', type='text', debounce=True,
                          placeholder='Recherche (expéditeur, sujet, corps) - regex possible'),
                dcc.Checklist(id='filtre-non-lus', options=[{'label': ' Non lus', 'value': 'oui'}]),
            ], className='filtres'),
            html.Div(id='resultat-filtre', className='bloc'),

            html.Div([
                html.H3('Archiver une catégorie'),
                dcc.Dropdown(id='archive-categorie', placeholder='Catégorie'),
                html.Button('Archiver', id='btn-archive'),
                html.Div(id='archive-statut'),
            ], className='bloc'),
        ]),

        dcc.Tab(label='Envoyer un mail', children=[
            html.Div([
                dcc.Input(id='prenom', placeholder='Prénom'),
                dcc.Input(id='nom', placeholder='Nom'),
                dcc.Input(id='destinataire', type='email', placeholder='Adresse email'),
                dcc.Input(id='sujet', placeholder='Sujet'),
                dcc.Textarea(id='message', placeholder='Message'),
                dcc.Upload(id='piece-jointe', children=html.Div('Glisser un fichier ou cliquer pour joindre'),
                           className='upload'),
                html.Div(id='nom-fichier'),
                html.Button('Envoyer', id='btn-envoyer'),
                html.Div(id='envoi-statut'),
            ], className='bloc formulaire'),
        ]),

        dcc.Tab(label='Alertes', children=[
            html.Div([
                html.P('Une alerte est envoyée à ' + config.alert_email +
                       ' quand un mail reçu contient : ' + ', '.join(config.mots_cles_alerte)),
                dcc.Graph(id='graph-alertes'),
                html.Div(id='liste-alertes'),
            ], className='bloc'),
        ]),
    ]),
], className='page')


# ---------------- Callbacks ----------------

@app.callback(
    Output('statut', 'children'),
    Output('maj', 'data'),
    Input('btn-sync', 'n_clicks'),
    Input('btn-demo', 'n_clicks'),
    State('maj', 'data'),
    prevent_initial_call=True,
)
def synchroniser(n_sync, n_demo, maj):
    if dash.ctx.triggered_id == 'btn-demo':
        demo.generer()
        return 'Données de test chargées.', maj + 1
    try:
        nouveaux, alertes = mf.recevoir_emails()
        return f'{nouveaux} nouveau(x) mail(s), {alertes} alerte(s) envoyée(s).', maj + 1
    except Exception as e:
        return f'Erreur de connexion : {e}', maj


@app.callback(
    Output('nb-recus', 'children'),
    Output('nb-envoyes', 'children'),
    Output('nb-non-lus', 'children'),
    Output('nb-alertes', 'children'),
    Output('derniers-mails', 'children'),
    Output('graph-categories', 'figure'),
    Output('filtre-categorie', 'options'),
    Output('archive-categorie', 'options'),
    Input('maj', 'data'),
)
def maj_dashboard(maj):
    df = mf.charger_emails()
    recus = df[df['type'] == 'entrant']
    envoyes = df[df['type'] == 'sortant']
    alertes = mf.charger_alertes()

    derniers = recus.head(5).copy()
    derniers['date'] = derniers['date'].dt.strftime('%d/%m %H:%M')
    derniers['lu'] = derniers['lu'].map({1: 'lu', 0: 'non lu'})

    cat = recus['categorie'].value_counts().reset_index()
    cat.columns = ['categorie', 'nombre']
    fig = px.pie(cat, names='categorie', values='nombre', hole=0.4)
    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300)

    liste_cat = sorted(df['categorie'].unique()) if not df.empty else []

    return (len(recus), len(envoyes), int((recus['lu'] == 0).sum()), len(alertes),
            tableau(derniers, ['date', 'expediteur', 'sujet', 'categorie', 'lu'],
                    ['Date', 'Expéditeur', 'Sujet', 'Catégorie', 'Statut']),
            fig, liste_cat, liste_cat)


@app.callback(
    Output('graph-activite', 'figure'),
    Input('periode', 'value'),
    Input('maj', 'data'),
)
def graph_activite(periode, maj):
    df = mf.charger_emails()
    if periode == 'jour':
        df['periode'] = df['date'].dt.strftime('%Y-%m-%d')
    else:
        df['periode'] = df['date'].dt.hour

    groupes = df.groupby(['periode', 'type']).size().reset_index(name='nombre')

    if periode == 'jour':
        fig = px.bar(groupes, x='periode', y='nombre', color='type', barmode='group',
                     color_discrete_map=couleurs, labels={'periode': 'Jour', 'nombre': 'Mails'})
    else:
        fig = px.line(groupes, x='periode', y='nombre', color='type', markers=True,
                      color_discrete_map=couleurs, labels={'periode': 'Heure', 'nombre': 'Mails'})
        fig.update_xaxes(dtick=1, range=[0, 23])
    fig.update_layout(template='plotly_white', height=350, legend_title_text='',
                      margin=dict(t=20))
    return fig


@app.callback(
    Output('resultat-filtre', 'children'),
    Input('filtre-type', 'value'),
    Input('filtre-categorie', 'value'),
    Input('filtre-texte', 'value'),
    Input('filtre-non-lus', 'value'),
    Input('maj', 'data'),
)
def filtrer(type_mail, categories, texte, non_lus, maj):
    df = mf.charger_emails()

    if type_mail:
        df = df[df['type'] == type_mail]
    if categories:
        df = df[df['categorie'].isin(categories)]
    if non_lus:
        df = df[df['lu'] == 0]
    if texte:
        try:
            motif = re.compile(texte, re.IGNORECASE)
        except re.error:
            return html.P('Expression régulière invalide.')
        masque = df.apply(lambda m: bool(motif.search(f"{m['expediteur']} {m['sujet']} {m['corps']}")), axis=1)
        df = df[masque]

    df['date'] = df['date'].dt.strftime('%d/%m/%Y %H:%M')
    return [html.P(f'{len(df)} mail(s)'),
            tableau(df.head(50), ['date', 'type', 'expediteur', 'destinataire', 'sujet', 'categorie'],
                    ['Date', 'Type', 'De', 'À', 'Sujet', 'Catégorie'])]


@app.callback(
    Output('archive-statut', 'children'),
    Input('btn-archive', 'n_clicks'),
    State('archive-categorie', 'value'),
    prevent_initial_call=True,
)
def archiver(n, categorie):
    if not categorie:
        return 'Choisir une catégorie.'
    try:
        total = mf.archiver_categorie(categorie)
        return f'{total} mail(s) déplacé(s) vers Archive/{categorie}'
    except Exception as e:
        return f'Erreur : {e}'


@app.callback(
    Output('nom-fichier', 'children'),
    Input('piece-jointe', 'filename'),
)
def afficher_fichier(nom):
    return f'Fichier : {nom}' if nom else ''


@app.callback(
    Output('envoi-statut', 'children'),
    Output('maj', 'data', allow_duplicate=True),
    Input('btn-envoyer', 'n_clicks'),
    State('prenom', 'value'),
    State('nom', 'value'),
    State('destinataire', 'value'),
    State('sujet', 'value'),
    State('message', 'value'),
    State('piece-jointe', 'contents'),
    State('piece-jointe', 'filename'),
    State('maj', 'data'),
    prevent_initial_call=True,
)
def envoyer(n, prenom, nom, destinataire, sujet, message, contenu, nom_fichier, maj):
    if not destinataire or not re.match(r'^[\w.+-]+@[\w-]+\.[\w.]+$', destinataire):
        return 'Adresse email invalide.', maj
    if not sujet or not message:
        return 'Le sujet et le message sont obligatoires.', maj

    fichier = None
    if contenu:
        fichier = base64.b64decode(contenu.split(',')[1])

    try:
        mf.envoyer_mail_personnalise(nom or '', prenom or '', destinataire, sujet, message,
                                     fichier, nom_fichier)
        return f'Mail envoyé à {destinataire}.', maj + 1
    except Exception as e:
        return f'Erreur : {e}', maj


@app.callback(
    Output('graph-alertes', 'figure'),
    Output('liste-alertes', 'children'),
    Input('maj', 'data'),
)
def maj_alertes(maj):
    alertes = mf.charger_alertes()
    compte = alertes['mot_cle'].value_counts().reset_index()
    compte.columns = ['mot_cle', 'nombre']
    fig = px.bar(compte, x='mot_cle', y='nombre', labels={'mot_cle': 'Mot-clé', 'nombre': 'Alertes'})
    fig.update_layout(template='plotly_white', height=280, margin=dict(t=20))
    return fig, tableau(alertes, ['date', 'mot_cle', 'expediteur', 'sujet'],
                        ['Date', 'Mot-clé', 'Expéditeur', 'Sujet'])


if __name__ == '__main__':
    app.run(debug=True)
