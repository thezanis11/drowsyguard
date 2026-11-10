# Présenter cette reconstruction en entretien

## Présentation courte

« J'avais un projet académique de détection de somnolence dont les sources ont été perdues. J'en ai fait reconstruire une nouvelle version en novembre 2026 avec assistance IA. Elle utilise un modèle facial préentraîné pour mesurer l'ouverture des yeux, une calibration et des règles temporelles. Le travail distingue clairement les pertes de suivi, les alertes heuristiques et les limites de validation. »

Adapter la contribution personnelle à ce que vous avez réellement compris, modifié et exécuté. Ne pas affirmer avoir entraîné MediaPipe, rédigé seul l'ensemble de cette reconstruction ou réalisé une validation clinique.

## Points à savoir expliquer

- Pourquoi utiliser des durées plutôt qu'un nombre fixe d'images ? Une caméra à 10 images/s et une caméra à 60 images/s doivent déclencher pour une durée comparable.
- Pourquoi calculer les distances en pixels ? Les coordonnées MediaPipe sont normalisées séparément par largeur et hauteur : calculer directement les rapports sur ces coordonnées déforme les distances sur une image non carrée.
- Pourquoi calibrer ? La morphologie, l'angle et les lunettes changent les valeurs de référence. La calibration ne résout pas tous les problèmes et suppose que les yeux restent ouverts.
- Pourquoi ne pas compter un visage absent comme « yeux ouverts » ? Cela réduirait artificiellement la fraction fermée et pourrait donner une impression de bon état alors que le système ne mesure rien.
- Pourquoi une bouche ouverte n'est pas un bâillement prouvé ? La parole et d'autres mouvements peuvent produire le même rapport géométrique.
- Où est l'apprentissage automatique ? Dans le modèle facial préentraîné. Les décisions d'alerte de cette version sont des règles explicites, pas un classificateur de somnolence entraîné.

## Exercices pour s'approprier le projet

1. Modifier `closure_seconds`, prédire l'effet sur le scénario synthétique, puis vérifier dans le CSV.
2. Ajouter un test qui masque le visage entre deux fermetures : elles ne doivent pas s'additionner en une fermeture continue.
3. Comparer les valeurs EAR avec et sans lunettes, en restant assis et sans enregistrer d'images ; consigner les limites.
4. Présenter un échec observé et une amélioration possible : filtres de qualité, données annotées, cadence ou gestion de la pose.

