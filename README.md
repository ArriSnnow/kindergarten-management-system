# Système de gestion scolaire — Maternelle

Application web de gestion interne pour une école maternelle.  
Développée avec Python, Django et PostgreSQL.

---

## Objectif

Remplacer les processus papier par un système centralisé permettant à l'administrateur de gérer :

- Les dossiers des élèves et leurs numéros de dossier permanents
- Les parents, tuteurs et personnes autorisées à récupérer les élèves
- Les classes et les années scolaires
- La présence quotidienne
- La remise des élèves en fin de journée
- Les frais scolaires et les paiements
- Le personnel et les salaires
- Les évaluations et les bulletins
- Les annonces scolaires

Les parents ont accès à un portail en lecture seule pour consulter les informations de leurs enfants.

---

## Technologies

| Composant       | Technologie              |
|-----------------|--------------------------|
| Langage         | Python 3.12+             |
| Framework web   | Django 5.x               |
| Base de données | PostgreSQL               |
| Interface       | Django templates + Bootstrap 5 |
| Tests           | Django test framework    |
| Versionnement   | Git                      |

---

## Rôles utilisateurs

| Rôle              | Accès                                                                 |
|-------------------|-----------------------------------------------------------------------|
| **Administrateur** | Accès complet à toutes les fonctionnalités                           |
| **Parent**        | Lecture seule — uniquement les enfants liés à son compte             |

---

## Numéro de dossier permanent

Chaque élève reçoit un numéro de dossier permanent au moment de son inscription, selon le format :

```
YYYY-GG-NNN
```

| Partie | Description                              | Exemple |
|--------|------------------------------------------|---------|
| `YYYY` | Année scolaire d'admission               | `2025`  |
| `GG`   | Niveau au moment de l'inscription        | `PS`, `MS`, `GS` |
| `NNN`  | Numéro séquentiel dans l'ordre d'inscription | `001` à `999` |

**Exemples :** `2025-PS-001`, `2025-MS-014`, `2026-GS-003`

Ce numéro est :
- Généré automatiquement
- Unique et définitif
- Jamais modifié ni réutilisé, même si l'élève quitte l'école
- Lié au dossier physique de l'élève (armoire, tiroir, position)

---

## Niveaux scolaires

| Code | Niveau          |
|------|-----------------|
| PS   | Petite Section  |
| MS   | Moyenne Section |
| GS   | Grande Section  |

---

## Évaluations

Les évaluations peuvent utiliser :
- Une **échelle descriptive** : Excellent · Très bien · Bien · En développement · Besoin de soutien
- Une **note numérique** (facultatif)

---

## Règles fondamentales

- Les dossiers des élèves ne sont **jamais supprimés** — ils sont archivés.
- Le numéro de dossier permanent n'est **jamais modifié ni réattribué**.
- Les paiements enregistrés sont **immuables** — les corrections font l'objet d'un nouvel enregistrement avec trace d'audit.
- Les parents n'accèdent **qu'aux dossiers de leurs propres enfants**.
- Les informations salariales sont **réservées à l'administrateur**.
- Aucun secret n'est stocké dans le code source.

---

## Structure du projet (applications Django)

| Application      | Responsabilité                                      |
|------------------|-----------------------------------------------------|
| `accounts`       | Modèle utilisateur, authentification, rôles         |
| `audit`          | Journal immuable des actions administratives        |
| `students`       | Dossiers élèves, statuts, archivage                 |
| `guardians`      | Tuteurs, relations élève-tuteur, personnes autorisées |
| `academics`      | Années scolaires, classes, historique d'inscription |
| `attendance`     | Présence quotidienne                                |
| `pickups`        | Journal de remise des élèves                        |
| `payments`       | Frais scolaires, paiements, reçus                   |
| `staff`          | Profils du personnel, historique d'emploi           |
| `salaries`       | Paiements de salaires (accès restreint)             |
| `assessments`    | Évaluations, bulletins, commentaires                |
| `announcements`  | Annonces scolaires                                  |
| `reports`        | Rapports et exports CSV                             |

---

## Jalons de développement

| Jalon | Objectif                              | Statut      |
|-------|---------------------------------------|-------------|
| 0     | Confirmation des exigences            | ✅ Terminé  |
| 1     | Fondations du projet                  | ✅ Terminé  |
| 2     | Authentification et rôles             | En attente  |
| 3     | Élèves et tuteurs                     | En attente  |
| 4     | Numéros de dossier permanents         | En attente  |
| 5     | Années scolaires, classes, inscriptions | En attente |
| 6     | Présence quotidienne                  | En attente  |
| 7     | Remise autorisée des élèves           | En attente  |
| 8     | Frais et paiements                    | En attente  |
| 9     | Personnel et salaires                 | En attente  |
| 10    | Évaluations                           | En attente  |
| 11    | Portail parents                       | En attente  |
| 12    | Rapports et exports                   | En attente  |
| 13    | Préparation au déploiement            | En attente  |
| 14    | Transfert et formation                | En attente  |

---

## Installation (développement)

Prérequis : Python 3.12+, PostgreSQL 16+ installés localement.

```bash
# Cloner le dépôt
git clone <url-du-depot>
cd kindergarten-management-system

# Créer l'environnement virtuel
python3.12 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Configurer les variables d'environnement
cp .env.example .env
# Modifier .env avec vos paramètres locaux (base de données, clé secrète)

# Créer la base de données PostgreSQL (si elle n'existe pas déjà)
createdb kindergarten_dev
createuser -s kindergarten_admin

# Appliquer les migrations
python manage.py migrate

# Lancer le serveur de développement
python manage.py runserver
```

---

## Variables d'environnement

Copier `.env.example` en `.env` et renseigner les valeurs (`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`). Ne jamais committer le fichier `.env`.

---

## Tests

```bash
python manage.py test
```

---

## Sécurité

Ce projet gère des données sensibles concernant des enfants mineurs.  
Toute contribution doit respecter les règles suivantes :

- Aucune donnée réelle d'élève ou de parent dans le code ou les tests
- Aucun secret dans le code source ou les commits
- Les pages privées sont protégées contre les accès non authentifiés
- Les permissions sont vérifiées côté serveur, jamais uniquement côté client

---

## Licence

Usage interne — école maternelle. Tous droits réservés.
