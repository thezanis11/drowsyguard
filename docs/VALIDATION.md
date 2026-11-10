# Bilan de validation — 10 novembre 2026

Environnement réellement utilisé : Windows, Python 3.12 64 bits, MediaPipe 0.10.32, OpenCV contrib 4.12.0.88, NumPy 2.2.6. Exécution CPU. Versions transitives figées dans `requirements-lock.txt` ; `pip check` ne signale aucune incompatibilité.

## Exécuté

- **16 tests unitaires réussis** : logique temporelle et calibration, comportement aux cadences 10/30/60 images/s, interruptions, fraction de temps fermé, avertissement bouche, géométrie EAR et protection des exports.
- **Chargement réel du modèle** : empreinte vérifiée contre le manifeste local ; bundle officiel de 3 758 596 octets, SHA-256 `64184e229b263107bc2b804c6625db1341ff2bb731874b0bcc2fe6544e0bc9ff`. Le SHA est enregistré lors du téléchargement et permet de détecter une modification ultérieure ; ce n'est pas une signature indépendante d'authenticité.
- **Inférence sur portrait réel** : visage observable, EAR environ 0,204 et rapport d'ouverture de bouche environ 0,206. Ces valeurs ne sont pas une annotation de somnolence. Après onze images vides, absence de visage correctement signalée. Preuve : `reports/integration.json`.
- **Chaîne vidéo réelle** : fichier AVI construit en répétant le portrait, suivi d'images vides. 210 images traitées ; calibration terminée à 5 s ; aucune alerte sur ce scénario ; perte du visage à 6 s. Temps du dernier échantillon 6,9667 s, correspondant à 209/30. Preuve : `reports/video-check.json`.
- **Démo fabriquée de 30 s** : fermeture courte non alarmante, fermeture prolongée alarmante à 9,5 s, absence du visage à 12 s, avertissement bouche à 17 s, alerte sur fraction fermée lorsque la fenêtre est suffisamment couverte. Tous les signaux sont synthétiques. Preuves : `reports/synthetic-demo/metrics.csv`, `summary.json`, `report.html` et `demo-alert.png`.
- **Inspection visuelle** de la capture du tableau de bord générée par le véritable code de présentation.

La caméra et le microphone du PC n'ont pas été ouverts pendant ces essais. Aucun enregistrement personnel n'a été effectué. Le bip Windows est implémenté mais n'a pas été joué pour une vérification d'écoute dans ce chat.

## Non établi

- Aucun taux de précision, sensibilité ou spécificité sur la somnolence humaine.
- Aucun entraînement de réseau de neurones de somnolence : utilisation d'un modèle facial préentraîné et de règles temporelles.
- Aucun essai sur route, certification, diagnostic de fatigue ou preuve d'aptitude à conduire.
- Aucune restitution exacte des sources académiques de 2024 ; cette reconstruction date de novembre 2026.

## Essai manuel à faire à l'arrêt, sur une chaise

1. Lancer `Demarrer.bat`. Vérifier le choix de webcam ; essayer `Demarrer.bat --camera 1` si nécessaire.
2. Garder les yeux ouverts, regard face caméra, jusqu'à la fin de la calibration. Vérifier que l'EAR de référence est stable.
3. Cligner normalement : une brève fermeture ne doit pas produire l'alerte de fermeture prolongée.
4. Fermer volontairement les yeux pendant deux secondes, puis les rouvrir : observer le cadre rouge et vérifier le son. Cette manipulation teste une fermeture volontaire, pas la détection d'un véritable endormissement.
5. Sortir du cadre, couvrir les yeux, tourner la tête et diminuer l'éclairage : le système doit, lorsque ses contrôles détectent l'échec, signaler qu'il n'est pas observable. Certaines occultations peuvent malgré tout produire des repères erronés : documenter les détections manquées.
6. Ouvrir la bouche puis parler : vérifier la différence entre avertissement bouche et alerte yeux ; relever les faux avertissements.
7. Tester les touches C, M et Q, puis vérifier qu'une autre application peut rouvrir la caméra après fermeture.

Noter matériel, éclairage, lunettes, cadence, cas testés et erreurs. Pour une évaluation de recherche, il faut un jeu annoté avec séparation des personnes entre réglage et test, des métriques par événement et une analyse des erreurs ; les séquences synthétiques fournies ne le remplacent pas.

