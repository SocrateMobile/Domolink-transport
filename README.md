# DomoLink-Transport 🚆

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/v/release/SocrateMobile/Domolink-transport?color=brightgreen)](https://github.com/SocrateMobile/Domolink-transport/releases)
[![Maintainer](https://img.shields.io/badge/maintainer-SocrateMobile-blue.svg)](https://github.com/SocrateMobile)

Intégration complète et sur-mesure pour **Home Assistant** affichant les prochains départs de trains et les derniers retours nocturnes sous la forme d'un véritable **Panneau d'Affichage de Gare** (Infogare Moderne TFT & Palettes Mécaniques Vintage Solari).

Elle remplace avantageusement l'empilement complexe `train_traveler` + capteurs REST + templates YAML Jinja2, tout en conservant une **rétrocompatibilité totale** avec vos écrans **openHASP** (WT32-SC01 et Sunton 7").

---

## 🌟 Fonctionnalités Principales

* 📱 **Panneau dédié dans la barre latérale gauche (Sidebar Panel)** avec ergonomie soignée.
* 🔄 **Bouton de bascule de style en temps réel** :
  * **🚆 Mode Moderne** : Écran Infogare TFT haute lisibilité (fond bleu nuit, texte jaune haute visibilité, alertes fluides).
  * **📟 Mode Mécanique** : Panneau vintage à palettes rabattables (style Solari di Udine avec typographie split-flap et volets 3D).
* 🎯 **Gestion des trajets configurables** :
  * Les **3 prochains trains** de la Gare A vers la Gare B (ex: *Enghien-les-Bains ➔ Paris Nord*) avec Voie (Quai), Mission (ex: *APOR*, *POGI*), et ponctualité.
  * Les **3 prochains trains** de la Gare A vers la Gare C (ex: *Enghien-les-Bains ➔ Ermont - Eaubonne*).
  * Les **Derniers retours nocturnes (22h00 ➔ 03h30)** pour ne plus jamais rater le dernier train pour rentrer (Paris ➔ Enghien et Ermont ➔ Enghien).
* 🚦 **Gestion fine de la ponctualité** :
  * Détection automatique : *À l'heure*, *Retard de +X min*, *À quai*, *Départ imminent*.
* 🚨 **Flash Info Trafic en direct** : Bandeau défilant avec alertes officielles et perturbations de la Ligne H.
* 📋 **Générateur de Carte Lovelace** : Un bouton permet d'obtenir immédiatement le code YAML de la carte `<domolink-transport-card>` pour vos tableaux de bord classiques.
* 📦 **Mise à jour en un clic directement depuis le panel** : Détection automatique des releases GitHub via l'entité `update.domolink_transport` et installation sans ligne de commande.
* 📺 **Rétrocompatibilité Totale openHASP** : Crée nativement tous les capteurs historiques (`sensor.next_train_minutes_1..4`, `sensor.next_trains_one..two`, `sensor.train_traveler_eng_par_*`) afin que vos fichiers existants (`open.yaml` et `enghien_openhasp.yaml`) fonctionnent sans aucune modification.
* 🎆 **Easter Egg officiel "SOCRATE RULES"** : Module interactif immersif déclenché par un triple-clic sur le logo DomoLink.

---

## 🔑 Pas-à-pas : Obtenir vos Clés d'API

### 1. Obtenir la Clé API SNCF / Navitia (Obligatoire)
L'API SNCF permet de récupérer l'ensemble des trajets, horaires théoriques et temps réel, missions et perturbations.

1. Rendez-vous sur le portail développeur SNCF : [https://numerique.sncf.com/startup/api/](https://numerique.sncf.com/startup/api/) ou directement [https://api.sncf.com/](https://api.sncf.com/).
2. Cliquez sur **Créer un compte / S'inscrire** (gratuit).
3. Une fois connecté, accédez à votre profil / espace développeur :
   * Générez un nouveau **Jeton d'authentification (API Token)**.
4. Votre clé ressemble à un UUID (ex: `12345678-abcd-1234-ef01-123456789abc`).
5. Copiez cette clé et conservez-la pour l'étape de configuration dans Home Assistant.

---

### 2. Obtenir la Clé API PRIM Île-de-France Mobilités (Optionnelle mais recommandée)
La plateforme **PRIM** (Plateforme Régionale d'Information pour la Mobilité d'Île-de-France Mobilités) apporte des informations complémentaires en temps réel (notamment les voies et les correspondances de bus de nuit).

1. Rendez-vous sur le portail officiel PRIM : [https://prim.iledefrance-mobilites.fr/](https://prim.iledefrance-mobilites.fr/).
2. Cliquez en haut à droite sur **S'inscrire** et validez votre compte par e-mail.
3. Connectez-vous, puis allez dans votre **Profil** > **Mes clés d'API**.
4. Cliquez sur **Générer une nouvelle clé d'API**.
5. Donnez un nom (ex: `HomeAssistant DomoLink`) et validez.
6. Copiez la clé générée (elle sera demandée dans le champ facultatif *Clé API PRIM IDFM*).

---

## 🛠️ Installation

### Méthode 1 : Via HACS (Recommandée)
1. Dans Home Assistant, ouvrez **HACS** > **Intégrations**.
2. Cliquez sur les 3 points en haut à droite > **Dépôts personnalisés**.
3. Ajoutez l'URL : `https://github.com/SocrateMobile/Domolink-transport`
4. Sélectionnez la catégorie : **Intégration**.
5. Cliquez sur **Télécharger** puis redémarrez Home Assistant.

### Méthode 2 : Installation Manuelle
1. Téléchargez la dernière version depuis la section Releases de GitHub.
2. Déposez le dossier `custom_components/domolink_transport` dans votre répertoire `config/custom_components/`.
3. Redémarrez Home Assistant.

---

## ⚙️ Configuration

1. Allez dans **Paramètres** > **Appareils et services** > **Ajouter une intégration**.
2. Recherchez **DomoLink-Transport**.
3. Renseignez :
   * **Clé API SNCF / Navitia** (Obligatoire)
   * **Clé API PRIM IDFM** (Optionnelle)
   * **Gare A (Domicile)** : *Enghien-les-Bains* (ou votre gare habituelle)
   * **Gare B (Destination 1)** : *Paris Nord*
   * **Gare C (Destination 2)** : *Ermont - Eaubonne*
   * **Créer les capteurs rétrocompatibles openHASP** : Coché par défaut.
4. Validez ! Le panneau apparaîtra immédiatement dans votre barre latérale gauche.

> **Note :** Tous ces paramètres restent modifiables à tout moment en cliquant sur **Configurer** sur l'intégration dans Home Assistant.

---

## 📋 Utilisation en Carte Lovelace (Dashboard)

Pour intégrer le panneau directement dans vos dashboards :

```yaml
type: custom:domolink-transport-card
style: modern # ou "mechanical" pour le style à palettes vintage
station_a: Enghien-les-Bains
station_b: Paris Nord
station_c: Ermont - Eaubonne
```

---

## 📺 Entités Rétrocompatibles pour openHASP

Si vous utilisez des écrans **openHASP** (WT32-SC01, Sunton 7", etc.), l'intégration fournit automatiquement les entités identiques à vos anciens templates et intégrations :

| Entité | Description |
| :--- | :--- |
| `sensor.next_train_minutes_1` à `4` | Décompte en minutes jusqu'au prochain train |
| `sensor.next_trains_one` | Synthèse du prochain train (ex: `12 min` ou `1h05`) |
| `sensor.next_trains_two` | Synthèse des 2 trains suivants (ex: `15 min / 30 min`) |
| `sensor.train_traveler_eng_par_next_journey_1` à `5` | Entités de départ A ➔ B avec attributs complets |
| `sensor.train_traveler_eng_par_last_journey_1` | Dernier retour nocturne B ➔ A |
| `sensor.train_traveler_par_eng_next_journey_1` | Prochains retours B ➔ A |

---

## 👨‍💻 Auteur & Licence

Développé par **SocrateMobile** dans le cadre de la suite **DomoLink**.  
Licence MIT.
