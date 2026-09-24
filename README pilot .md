# Fourchette Pilot V2 — Safari / Mobile

Version conçue pour être utilisée depuis Safari sur iPhone.

## Ce qui change
- interface responsive et compacte ;
- navigation par onglets ;
- gros contrôles tactiles ;
- saisie rapide d'un service ;
- KPI adaptés au petit écran ;
- historique + export CSV ;
- recommandations locales ;
- analyse IA optionnelle.

## Déploiement web
Le projet est prêt pour un hébergement Streamlit.

1. Place les fichiers sur un dépôt GitHub privé/public selon ton choix.
2. Dans Streamlit Community Cloud, crée une app à partir du dépôt.
3. Fichier principal : `app.py`.
4. Si tu veux l'analyse IA, ajoute `OPENAI_API_KEY` dans les secrets du service d'hébergement.
5. Ouvre ensuite l'URL obtenue dans Safari.

## Ajouter à l'écran d'accueil de l'iPhone
Dans Safari : bouton Partager > Ajouter à l'écran d'accueil.

## Important sur la persistance
Sur certains hébergements gratuits, le disque local peut être réinitialisé. Pour un usage commercial réel,
la prochaine étape sera de connecter une base persistante (par exemple PostgreSQL/Supabase).
