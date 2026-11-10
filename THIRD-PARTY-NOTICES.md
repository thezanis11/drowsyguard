# Éléments tiers

- MediaPipe 0.10.32 : Google / MediaPipe Authors, Apache-2.0. [Source et licence](https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE).
- Face Landmarker : bundle préentraîné téléchargé depuis le stockage officiel Google, version 1, selon la documentation MediaPipe. URL et SHA-256 dans `models/provenance.json`. Le modèle est **exclu de l'archive source et de Git** ; ne pas déduire de la licence de la documentation une autorisation de redistribution de tout modèle. Consulter les conditions et la fiche du modèle avant toute redistribution.
- OpenCV contrib Python : distribution des composants OpenCV, Apache-2.0 et licences des éléments tiers fournies dans le paquet. [Licences](https://github.com/opencv/opencv/blob/4.12.0/LICENSE).
- NumPy : BSD-3-Clause ; Matplotlib : licence Matplotlib et licences de ses dépendances. Les textes sont installés dans l'environnement Python.
- Portrait d'intégration : fixture `portrait.jpg` hébergée par Google MediaPipe. Téléchargement facultatif dans `data/`, non redistribué. Utilisé pour un essai de présence d'un visage, pas pour entraîner ou évaluer un modèle de somnolence.
- Autres dépendances : noms et versions exactes dans `requirements-lock.txt`, notices dans `.venv/Lib/site-packages/*dist-info`.

Aucun code d'un projet de somnolence tiers n'a été repris. L'EAR est une construction géométrique attribuée dans le README ; le moteur temporel, l'interface et les tests ont été développés pour cette reconstruction avec assistance IA.

