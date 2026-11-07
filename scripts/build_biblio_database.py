#!/usr/bin/env python3
"""
Builds the BiblioIschio dataset (data/articles.json, data/categories.json, data/embedded_data.js),
downloads genuine Open-Access Publisher / PMC PDFs when available (never generates synthetic PDFs;
falls back to direct publisher/DOI/PubMed links), and generates Zotero export files (.ris, .bib, .json).
"""

import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PDFS_DIR = BASE_DIR / "pdfs"

CATEGORIES = {
    "proximal_acute": {
        "id": "proximal_acute",
        "label": "Ruptures Proximales Aiguës & Cohorte PHAS",
        "short_label": "Avulsions Proximales & PHAS",
        "icon": "zap",
        "color": "#f97316",
        "agenda_examples": [
            "Réinsertion trans-osseuse par ancres des avulsions tubérositaires aiguës (< 32 jours)",
            "Analyse des 757 patients de la cohorte PHAS (Clinique du Sport Paris)",
            "Retour au sport chez le sportif professionnel et résultats à long terme (≥ 8 ans)"
        ]
    },
    "chronic_revision_allograft": {
        "id": "chronic_revision_allograft",
        "label": "Ruptures Chroniques, Révisions & Greffes (Allogreffes)",
        "short_label": "Chroniques, Allogreffes & Révisions",
        "icon": "shield",
        "color": "#8b5cf6",
        "agenda_examples": [
            "Reconstruction par allogreffe structurelle (tendon quadricipital / Achille) des ruptures rétractées",
            "Reprises chirurgicales (révisions) après re-rupture proximale",
            "Réinsertion anatomique des avulsions isolées du semi-membraneux"
        ]
    },
    "imaging_bamic_mri": {
        "id": "imaging_bamic_mri",
        "label": "Imagerie IRM, Signe du Cobra, Tendon Central & BAMIC",
        "short_label": "IRM, BAMIC & Signe du Cobra",
        "icon": "eye",
        "color": "#6366f1",
        "agenda_examples": [
            "Signe du Cobra en IRM (surestimation de 21 % de la rétraction du semi-membraneux)",
            "IRM de première intention vs échographie et suivi IRM de cicatrisation post-opératoire",
            "Classification BAMIC (British Athletics) et lésions du tendon intramusculaire (type c)"
        ]
    },
    "pht_endoscopy_sciatic": {
        "id": "pht_endoscopy_sciatic",
        "label": "Tendinopathie Proximale (PHT), Endoscopie & Nerf Sciatique",
        "short_label": "Tendinopathie, Endoscopie & Sciatique",
        "icon": "activity",
        "color": "#ec4899",
        "agenda_examples": [
            "Ténotomie partielle et réinsertion sur ancres des tendinopathies proximales réfractaires (PHT)",
            "Réparation endoscopique des ruptures proximales et neurolyse du nerf sciatique",
            "Impact pronostique de l'œdème péri-sciatique en IRM sur le délai de retour au jeu"
        ]
    },
    "distal_tears_t_junction": {
        "id": "distal_tears_t_junction",
        "label": "Ruptures Distales & Jonction en T du Biceps Fémoral",
        "short_label": "Lésions Distales & Jonction T",
        "icon": "crosshair",
        "color": "#06b6d4",
        "agenda_examples": [
            "Réparation chirurgicale par ancres des avulsions distales du biceps fémoral chez l'athlète",
            "Suture chirurgicale des lésions aiguës de la jonction musculo-tendineuse distale en T (DMTJ)",
            "Sémiologie IRM de la jonction en T du biceps fémoral (taux de récidive > 50 % sans chirurgie)"
        ]
    },
    "scores_rehab_prevention": {
        "id": "scores_rehab_prevention",
        "label": "Scores PHAS / Hip-RSI, Rééducation Excentrique & RTS",
        "short_label": "Scores PHAS/RSI, Nordic & RTS",
        "icon": "flame",
        "color": "#10b981",
        "agenda_examples": [
            "Validation des scores PHAS (36 items), Short-PHAS (12 items) et Hip-RSI psychologique",
            "Essai randomisé PHARRLAP : rééducation accélérée sans attelle vs protocole classique",
            "Adaptations sarcomériques après Nordic Hamstring Exercise (NHE) et Consensus de Londres"
        ]
    },
    "acl_graft_harvest": {
        "id": "acl_graft_harvest",
        "label": "Ischio-Jambiers & Plastie du LCA (Prélèvement & Régénération)",
        "short_label": "Greffe DIDT/DT4 & Régénération",
        "icon": "target",
        "color": "#e11d48",
        "agenda_examples": [
            "Préservation de l'insertion tibiale distale des ischio-jambiers lors du LCA (maturation accélérée)",
            "Rétraction anatomique du corps charnu du semi-tendineux en IRM après prélèvement DIDT"
        ]
    }
}

CURATED_DATA = {
    "41918719": {
        "category_id": "proximal_acute",
        "title_fr": "Facteurs de risque de complications après chirurgie d'avulsion proximale des ischio-jambiers : analyse de 757 patients de la cohorte PHAS",
        "modality": "Chirurgie & Clinique",
        "intervention_type": "Réinsertion Proximal (Cohorte PHAS)",
        "cochin_link": "Étude de référence de la cohorte prospective PHAS (Dr Nicolas Lefèvre, Clinique du Sport Paris, n = 757) établissant la cartographie exacte des complications post-opératoires.",
        "summary_fr_short": "Sur 757 patients opérés d'une avulsion proximale des ischio-jambiers (2002–2023), le taux global de complications est de 10,4 %, comprenant 5,6 % de re-ruptures et 4,7 % de complications hors re-rupture. Trois quarts des complications surviennent dans les 5,5 premiers mois post-opératoires.",
        "summary_fr_detailed": "Cette large cohorte prospective (757 patients, âge moyen 47,3 ans) analyse les complications après réinsertion primaire des avulsions proximales des ischio-jambiers (PHAI). Le taux de complications hors re-rupture est faible (4,7 %), mais impacte significativement le score PHAS final et le retour au sport au niveau antérieur (31,3 % vs 65,0 %, p = 0,0137). Les deux facteurs de risque indépendants de complications hors re-rupture sont le contexte d'accident du travail (OR = 5,59) et l'atteinte isolée du tendon semi-membraneux (OR = 12,1). Une gêne assise modérée à sévère persiste chez seulement 5 % des patients.",
        "protocol_fr": "Réinsertion anatomique trans-osseuse sur la tubérosité ischiatique par ancres de suture • Suivi prospectif standardisé par scores PHAS, Tegner et UCLA (NCT02906865).",
        "key_points_fr": [
            "Taux global de complications de 10,4 % sur 757 patients : 5,6 % de re-ruptures et 4,7 % d'autres complications.",
            "75 % des événements indésirables surviennent au cours des 5,5 premiers mois post-opératoires.",
            "L'accident du travail (OR = 5,59) et l'avulsion isolée du semi-membraneux (OR = 12,1) augmentent le risque de complications.",
            "La douleur en position assise prolongée ne concerne qu'une minorité de patients (~5 %) à long terme."
        ],
        "tags": ["Avulsion proximale", "Complications", "Cohorte PHAS", "Semi-membraneux", "OJSM 2026"]
    },
    "41685043": {
        "category_id": "proximal_acute",
        "title_fr": "Résultats à très long terme (≥ 8 ans) et retour au sport après réinsertion chirurgicale des avulsions proximales des ischio-jambiers",
        "modality": "Chirurgie & Suivi ≥ 8 ans",
        "intervention_type": "Réinsertion par Ancres",
        "cochin_link": "Démontre la pérennité des résultats fonctionnels au-delà de 10 ans de recul moyen (123,4 mois) dans la cohorte parisienne PHAS et l'importance cruciale d'opérer en phase aiguë (< 4 semaines).",
        "summary_fr_short": "Sur 139 patients suivis en moyenne plus de 10 ans (123,4 mois, minimum 8 ans), le score PHAS atteint 87,5/100 et le score UCLA passe de 3,1 à 7,5. Le score PHAS continue de progresser favorablement jusqu'à 8 ans post-opératoires.",
        "summary_fr_detailed": "Étude prospective de niveau II évaluant 139 patients (âge moyen 44,4 ans) opérés entre 2002 et 2015 avec un recul minimum de 8 ans (moyenne 10,3 ans). Les résultats fonctionnels sont excellents et durables (PHAS moyen 87,5 ± 14,9). Point fondamental : l'analyse longitudinale montre que le score PHAS continue de s'améliorer au fil des années jusqu'à 8 ans après la chirurgie. En revanche, les réparations réalisées au stade chronique (> 4 semaines) présentent un risque près de 6 fois plus élevé de mauvais résultat fonctionnel à long terme comparativement aux réparations aiguës.",
        "protocol_fr": "Réinsertion chirurgicale primaire par ancres sur la tubérosité ischiatique • Évaluation longitudinale à 1, 2, 4, 6 et ≥ 8 ans par scores PHAS, UCLA et Tegner.",
        "key_points_fr": [
            "Recul moyen exceptionnel de 123,4 mois (> 10 ans) sur 139 patients opérés.",
            "Score PHAS moyen à long terme de 87,5/100 et amélioration majeure du score UCLA (de 3,1 à 7,5).",
            "La récupération fonctionnelle (PHAS) poursuit sa progression jusqu'à 8 ans post-opératoires.",
            "La chirurgie retardée (> 4 semaines) multiplie par ~6 le risque de score PHAS inférieur à long terme."
        ],
        "tags": ["Long terme", "Avulsion proximale", "Cohorte PHAS", "Retour au sport", "OJSM 2026"]
    },
    "42358117": {
        "category_id": "proximal_acute",
        "title_fr": "Réparation précoce vs différée des ruptures proximales des ischio-jambiers : revue systématique et méta-analyse (2026)",
        "modality": "Méta-analyse",
        "intervention_type": "Chirurgie Précoce (< 4–6 sem.)",
        "cochin_link": "Confirme à l'échelle internationale (1 720 patients) les conclusions de la cohorte PHAS : opérer dans les 4 à 6 premières semaines divise par deux le risque de re-rupture et par quatre le risque de sciatalgie.",
        "summary_fr_short": "Méta-analyse incluant 12 études (992 réparations précoces ≤ 4–6 semaines vs 728 réparations différées). La prise en charge précoce réduit significativement le risque de sciatalgie post-opératoire (RR = 0,26 ; p = 0,009) et de re-rupture (RR = 0,51 ; p = 0,03).",
        "summary_fr_detailed": "Cette méta-analyse publiée dans l'AJSM en 2026 compare les résultats des réparations primaires précoces (≤ 4 à 6 semaines) et différées (> 4 à 6 semaines) hors allogreffes, sur un total de 1 720 patients. Si les scores fonctionnels globaux restent satisfaisants dans les deux groupes, l'intervention précoce diminue de 74 % le risque de souffrance ou radiculalgie sciatique post-opératoire (RR = 0,26) grâce à l'absence de fibrose péri-nerveuse, et diminue de 49 % le taux de re-rupture tendineuse (RR = 0,51).",
        "protocol_fr": "Indication chirurgicale posée dès l'IRM initiale • Intervention idéale dans les 4 semaines suivant le traumatisme avant constitution de la fibrose péri-sciatique.",
        "key_points_fr": [
            "Analyse poolée de 1 720 réparations primaires (992 précoces vs 728 différées).",
            "Réduction de 74 % du risque de sciatalgie post-opératoire en cas de chirurgie précoce (RR = 0,26).",
            "Réduction de moitié du taux de re-rupture tendineuse (RR = 0,51 ; p = 0,03).",
            "Plaide pour un circuit IRM + avis chirurgical spécialisé en urgence différée dès la suspicion clinique."
        ],
        "tags": ["Méta-analyse", "Délai chirurgical", "Re-rupture", "Nerf sciatique", "AJSM 2026"]
    },
    "39844676": {
        "category_id": "proximal_acute",
        "title_fr": "Résultats de la chirurgie d'avulsion proximale des ischio-jambiers avant et après 50 ans : étude comparative appariée de la cohorte PHAS",
        "modality": "Chirurgie & Clinique",
        "intervention_type": "Réinsertion par Ancres",
        "cochin_link": "Valide l'indication opératoire chez le patient actif de plus de 50 ans : le bénéfice fonctionnel est majeur et le taux de complications n'est pas plus élevé que chez le sujet jeune.",
        "summary_fr_short": "Étude cas-témoins appariée (298 patients : 18–50 ans vs > 50 ans). La chirurgie procure une amélioration fonctionnelle hautement significative dans les deux tranches d'âge, avec un taux de retour au sport et de complications strictement comparable.",
        "summary_fr_detailed": "Sur 298 patients appariés selon le sexe, le type de rupture (complète ou partielle rétractée > 2 cm), la chronicité et le score de Tegner pré-lésionnel (âge moyen 41,8 ans vs 58,0 ans, suivi > 4 ans), la réinsertion chirurgicale améliore significativement les scores PHAS, UCLA et Tegner dans les deux groupes. Bien que l'amplitude du gain soit légèrement supérieure chez les moins de 50 ans, les patients de plus de 50 ans obtiennent d'excellents résultats fonctionnels sans sur-risque de complication ni baisse du taux de retour au sport.",
        "protocol_fr": "Indication chirurgicale maintenue après 50 ans devant toute avulsion complète ou partielle rétractée > 2 cm chez un patient actif.",
        "key_points_fr": [
            "298 patients appariés (groupe < 50 ans vs groupe > 50 ans d'âge moyen 58 ans).",
            "Gain fonctionnel significatif sur le score PHAS dans les deux groupes d'âge.",
            "Aucune différence significative sur le taux de complications ou le taux de retour au sport (p > 0,05).",
            "L'âge civil > 50 ans ne doit pas contre-indiquer la réinsertion chirurgicale chez le patient sportif."
        ],
        "tags": ["Plus de 50 ans", "Cohorte PHAS", "Appariement", "Retour au sport", "KSSTA 2025"]
    },
    "39165177": {
        "category_id": "proximal_acute",
        "title_fr": "Traitement chirurgical vs traitement conservateur des avulsions proximales des ischio-jambiers : étude comparative appariée à plus de 4 ans de recul",
        "modality": "Chirurgie vs Conservateur",
        "intervention_type": "Étude Appariée (Score de Propension)",
        "cochin_link": "Démonstration directe par appariement sur score de propension de la supériorité nette de la chirurgie sur le traitement fonctionnel (satisfaction 89,5 % vs 25 %, retour au niveau antérieur 67,7 % vs 26,7 %).",
        "summary_fr_short": "Comparaison appariée entre 95 patients opérés et 32 patients ayant refusé la chirurgie (suivi moyen > 4 ans). Le groupe chirurgical obtient un score PHAS nettement supérieur (86,3 vs 69,8), une satisfaction de 89,5 % (vs 25 %) et 6 fois plus de chances de reprendre son sport au même niveau.",
        "summary_fr_detailed": "Cette étude comparative de la cohorte PHAS utilise un appariement par score de propension pour comparer le traitement chirurgical (n = 95) au traitement non chirurgical chez des patients présentant une indication opératoire mais ayant refusé l'intervention (n = 32). À plus de 4 ans de recul moyen, tous les indicateurs favorisent la chirurgie : PHAS moyen (86,3 vs 69,8), scores Tegner et UCLA (p = 0,0026), retour au sport global (68,4 % vs 46,9 %) et surtout retour au niveau pré-lésionnel (67,7 % vs 26,7 % ; OR = 6,04). Le taux de satisfaction atteint 89,5 % après chirurgie contre seulement 25 % sans chirurgie.",
        "protocol_fr": "Indication chirurgicale : avulsion complète, ou avulsion partielle rétractée > 2 cm, ou échec à 6 mois du traitement médical.",
        "key_points_fr": [
            "Score PHAS à > 4 ans : 86,3 ± 13,7 (chirurgie) contre 69,8 ± 15,1 (traitement non chirurgical).",
            "Probabilité multipliée par 6 (OR = 6,04) de retrouver son niveau sportif antérieur après chirurgie.",
            "Taux de satisfaction des patients : 89,5 % dans le groupe opéré contre 25 % dans le groupe non opéré.",
            "Argument majeur pour éclairer le consentement des patients hésitant devant l'intervention."
        ],
        "tags": ["Chirurgie vs Conservateur", "Score de propension", "Cohorte PHAS", "Satisfaction", "AJSM 2024"]
    },
    "38482843": {
        "category_id": "proximal_acute",
        "title_fr": "Facteurs de risque de re-rupture après avulsion proximale des ischio-jambiers et détermination du délai chirurgical optimal (Seuil des 32 jours)",
        "modality": "Chirurgie & Pronostic",
        "intervention_type": "Timing Chirurgical Optimal",
        "cochin_link": "Article princeps sur 740 patients définissant le seuil critique de 32 jours au-delà duquel le risque de re-rupture est multiplié par 2,5.",
        "summary_fr_short": "Sur 740 patients opérés (suivi moyen 4,9 ans), le taux de re-rupture est de 4,59 % (34/740), survenant dans 75 % des cas durant les 6 premiers mois (médiane 88,5 jours) et de façon atraumatique (74 %). Un délai avant chirurgie > 32 jours multiplie par 2,5 le risque de re-rupture.",
        "summary_fr_detailed": "L'analyse multivariée et par courbe ROC de 740 réparations primaires de la cohorte PHAS identifie précisément le seuil temporel définissant la chronicité à risque : 32 jours post-traumatiques. Dépasser un délai de 32 jours entre l'accident et la chirurgie augmente significativement le risque de re-rupture (HR = 2,5 ; IC 95 % 1,24–5,06 ; p = 0,01), tout comme le caractère initialement complet de l'avulsion des 3 tendons (HR = 4,33 ; p = 0,04). Trois quarts des re-ruptures surviennent avant 6 mois (médiane à 3 mois) souvent sans nouveau traumatisme violent.",
        "protocol_fr": "Objectif organisationnel : réaliser l'IRM diagnostique et la réinsertion chirurgicale dans les 32 jours suivant le traumatisme initial • Protection prudente de la réinsertion pendant les 3 à 6 premiers mois.",
        "key_points_fr": [
            "Taux global de re-rupture primaire de 4,59 % (34/740 patients).",
            "Seuil optimal par courbe ROC : un délai accident–chirurgie > 32 jours multiplie par 2,5 le risque de re-rupture.",
            "Les avulsions complètes initiales présentent un HR de re-rupture de 4,33 par rapport aux avulsions partielles.",
            "75 % des re-ruptures surviennent dans les 6 premiers mois (médiane : 88,5 jours), dont 74 % sans traumatisme franc."
        ],
        "tags": ["Re-rupture", "Délai chirurgical", "Seuil 32 jours", "Cohorte PHAS", "AJSM 2024"]
    },
    "38353018": {
        "category_id": "proximal_acute",
        "title_fr": "Facteurs prédictifs du retour précoce au sport chez l'athlète professionnel opéré d'une lésion proximale du complexe ischio-jambier",
        "modality": "Sportif Professionnel",
        "intervention_type": "Chirurgie & Retour au Jeu (RTS)",
        "cochin_link": "Série prospective de 64 athlètes professionnels opérés à Paris : 98,4 % de retour au sport et distinction sémiologique clé entre avulsion osseuse/empreinte vide ('dropped ice cream sign +') et rupture du tendon libre ('dropped ice cream sign -').",
        "summary_fr_short": "Chez 64 sportifs professionnels (âge moyen 27,3 ans), le taux de retour au sport est de 98,4 %, dont 78,1 % au même niveau de compétition dans un délai moyen de 6,2 ± 2,5 mois. Les taux de maintien de performance atteignent 100 % au handball/escrime/escalade et 95,2 % au football.",
        "summary_fr_detailed": "Cette étude prospective distingue deux entités anatomiques au sein du complexe proximal : la véritable avulsion de l'empreinte tubérositaire ('dropped ice cream sign positif') et la rupture complète du tendon libre proximal ('dropped ice cream sign négatif', PHTR). En analyse multivariée, les facteurs prédictifs d'un retour au sport plus rapide sont : le sexe masculin, l'atteinte isolée du semi-membraneux, et la rupture du tendon libre proximal (PHTR, HR = 7,77).",
        "protocol_fr": "Analyse IRM pré-opératoire de l'empreinte tubérositaire ('dropped ice cream sign') • Réinsertion ou suture anatomique précoce • Rééducation spécifique orientée haute performance avec retour moyen à la compétition à 6,2 mois.",
        "key_points_fr": [
            "98,4 % de retour au sport chez 64 athlètes professionnels, à un délai moyen de 6,2 ± 2,5 mois.",
            "95,2 % des footballeurs professionnels et 100 % des handballeurs/escrimeurs retrouvent leur niveau antérieur.",
            "Distinction pronostique majeure entre avulsion tubérositaire vraie et rupture du tendon libre proximal (PHTR).",
            "Le sexe masculin, la lésion isolée du semi-membraneux et le type PHTR prédisent un RTS plus précoce."
        ],
        "tags": ["Athlète professionnel", "Retour au sport", "Dropped ice cream sign", "Football", "AJSM 2024"]
    },
    "42702351": {
        "category_id": "chronic_revision_allograft",
        "title_fr": "Reconstruction par allogreffe structurelle des avulsions proximales chroniques des ischio-jambiers : résultats fonctionnels à moyen terme",
        "modality": "Chirurgie Reconstructrice",
        "intervention_type": "Reconstruction par Allogreffe",
        "cochin_link": "Valide la reconstruction par allogreffe dans les ruptures chroniques irréparables directement : le score PHAS médian bondit de 56,3 à 84,5 à 3,4 ans de recul.",
        "summary_fr_short": "Sur 42 patients opérés par allogreffe structurelle pour avulsion proximale chronique rétractée (recul moyen 3,4 ans), le score PHAS médian progresse de 56,3 en pré-opératoire à 84,5 au dernier recul, avec une excellente récupération fonctionnelle quotidienne.",
        "summary_fr_detailed": "Lorsque la rétraction tendineuse chronique et la perte de souplesse musculaire empêchent une réinsertion directe sur l'ischion sans flexion excessive du genou, l'interposition d'une allogreffe structurelle constitue la solution de sauvetage. Sur cette cohorte suivie 3,4 ± 1,6 ans, l'analyse des seuils cliniques (MCID, SCB et PASS fixé à 82,3 sur le score PHAS) confirme un gain fonctionnel majeur et une bonne satisfaction des patients, bien que le retour au sport de compétition au niveau pré-lésionnel reste plus limité qu'après réparation aiguë.",
        "protocol_fr": "Abord longitudinal sous-fessier élargi • Neurolyse prudente du nerf sciatique • Fixation proximale solide de l'allogreffe sur la tubérosité ischiatique par ancres et suture distale en Pulvertaft/enveloppement sur le moignon rétracté.",
        "key_points_fr": [
            "Progression spectaculaire du score PHAS médian de 56,3 (IQR 49,0–64,0) à 84,5 (IQR 73,8–94,8).",
            "Plus de 56 % des patients franchissent le seuil PASS (Patient Acceptable Symptom State, PHAS > 82,3).",
            "Option fiable de sauvetage lorsque la réinsertion directe en extension/faible flexion est impossible.",
            "Information loyale du patient : excellente fonction quotidienne mais retour au sport intensif plus mesuré."
        ],
        "tags": ["Allogreffe", "Rupture chronique", "Cohorte PHAS", "PASS / MCID", "Arthroscopy 2026"]
    },
    "40815844": {
        "category_id": "chronic_revision_allograft",
        "title_fr": "Résultats des reprises chirurgicales (révisions) comparés aux réparations primaires des avulsions proximales des ischio-jambiers",
        "modality": "Chirurgie de Révision",
        "intervention_type": "Révision vs Chirurgie Primaire",
        "cochin_link": "Étude cas-témoins appariée 1:4 (32 révisions vs 128 primaires) quantifiant le défi technique des reprises chirurgicales : recours à une allogreffe dans 37,5 % des cas et risque de re-rupture itérative de 31,3 %.",
        "summary_fr_short": "Comparaison appariée de 32 révisions chirurgicales et 128 réparations primaires (recul ~4 ans). Si le score PHAS médian atteint 85,0 après révision (vs 91,5 en primaire, p = 0,01), le risque de nouvelle rupture est multiplié par 8 (31,3 % vs 3,9 % ; HR = 8,19).",
        "summary_fr_detailed": "Première étude comparative appariée dédiée aux reprises d'échec de réinsertion proximale des ischio-jambiers. Le recours à une allogreffe de comblement est quatre fois plus fréquent en révision (37,5 % vs 9,4 %, p = 0,0003). Malgré des scores d'activité Tegner et UCLA proches à 4 ans chez les patients consolidés, la chirurgie de révision expose à un taux de re-rupture de 31,3 % (contre 3,9 % en primaire, HR = 8,19) et à une persistance douloureuse plus fréquente (50 % sans douleur ou douleur minime vs 72,4 % en primaire).",
        "protocol_fr": "Planification pré-opératoire systématique avec allogreffe disponible en salle • Neurolyse extensive du nerf sciatique engainé dans la cicatrice • Rééducation post-opératoire ralentie et protégée.",
        "key_points_fr": [
            "Nécessité d'une allogreffe dans 37,5 % des chirurgies de révision (contre 9,4 % en primaire).",
            "Score PHAS médian honorable après révision (85,0 vs 91,5 en primaire).",
            "Risque de re-rupture multiplié par 8 en révision (31,3 % vs 3,9 %, HR = 8,19).",
            "Souligne l'importance capitale de réussir la réparation primaire en phase aiguë (< 32 jours)."
        ],
        "tags": ["Chirurgie de révision", "Re-rupture", "Allogreffe", "Cohorte PHAS", "AJSM 2025"]
    },
    "41132280": {
        "category_id": "chronic_revision_allograft",
        "title_fr": "Reconstruction des avulsions proximales chroniques des ischio-jambiers par allogreffe de tendon quadricipital : note technique",
        "modality": "Technique Chirurgicale",
        "intervention_type": "Allogreffe Quadricipitale",
        "cochin_link": "Description pas-à-pas de la technique originale du Dr Nicolas Lefèvre utilisant une allogreffe fraîche congelée de tendon quadricipital pour ponter les rétractions chroniques majeures.",
        "summary_fr_short": "Note technique décrivant l'utilisation d'une allogreffe de tendon quadricipital (avec pastille/extrémité patellaire épaisse) pour reconstruire les ruptures proximales chroniques irréparables sans imposer de flexion forcée du genou.",
        "summary_fr_detailed": "Dans les avulsions chroniques anciennes avec rétraction sévère (> 8–10 cm), l'allogreffe de tendon quadricipital offre une résistance biomécanique remarquable et une géométrie idéale : son extrémité proximale épaisse permet un ancrage solide par ancres multiples sur la tubérosité ischiatique avivée, tandis que son éventail aponévrotique distal vient envelopper ('wrap') le moignon des tendons ischio-jambiers rétractés, évitant le recours à une attelle en flexion du genou post-opératoire.",
        "protocol_fr": "Allogreffe fraîche congelée de tendon quadricipital • Ancrage tubérositaire proximal par 3 à 4 ancres • Suture distale circonférentielle en manchon autour du tendon conjoint et du semi-membraneux.",
        "key_points_fr": [
            "Géométrie asymétrique idéale : extrémité proximale dense sur l'ischion et éventail distal enveloppant le moignon.",
            "Évite la mise en flexion forcée du genou lors de la suture et en post-opératoire.",
            "Excellente résistance biomécanique initiale permettant une rééducation progressive sécurisée."
        ],
        "tags": ["Note technique", "Allogreffe quadricipitale", "Rupture chronique", "Arthrosc Tech 2025"]
    },
    "41220667": {
        "category_id": "chronic_revision_allograft",
        "title_fr": "Réinsertion anatomique des avulsions proximales isolées du tendon semi-membraneux chez le sportif : note technique",
        "modality": "Technique Chirurgicale",
        "intervention_type": "Réinsertion Semi-Membraneux",
        "cochin_link": "Détaille l'anatomie chirurgicale de l'empreinte antéro-latérale du semi-membraneux sur l'ischion et la correspondance per-opératoire du « Signe du Cobra ».",
        "summary_fr_short": "Description étape par étape de la réinsertion anatomique des avulsions isolées du tendon proximal du semi-membraneux chez l'athlète, mettant en évidence l'aspect per-opératoire de l'enroulement distal du moignon (Signe du Cobra).",
        "summary_fr_detailed": "Bien que plus rare que l'avulsion complète des 3 tendons, l'avulsion isolée du chef proximal du semi-membraneux survient typiquement chez le sportif (danse, arts martiaux, sprint, grand écart) et compromet la reprise sportive en l'absence de chirurgie. L'article décrit le repérage de l'empreinte facettaire supéro-latérale sur la tubérosité ischiatique, le déroulement du moignon tendineux replié sur lui-même ('Cobra sign') qui fait surestimer la rétraction en IRM, et sa fixation anatomique par ancres.",
        "protocol_fr": "Incision dans le pli sous-fessier • Identification du nerf sciatique en latéral et du tendon conjoint intact en médial • Déroulement du moignon du semi-membraneux (Signe du Cobra) • Réinsertion sur la facette antéro-latérale de l'ischion.",
        "key_points_fr": [
            "L'insertion proximale du semi-membraneux est située en antéro-latéral par rapport au tendon conjoint (BF + ST).",
            "Le déroulement per-opératoire de l'extrémité repliée ('Cobra sign') restitue ~2 cm de longueur tendineuse.",
            "Permet une réinsertion directe sans tension excessive chez le sportif."
        ],
        "tags": ["Semi-membraneux isolé", "Signe du Cobra", "Technique chirurgicale", "Arthrosc Tech 2025"]
    },
    "42963497": {
        "category_id": "imaging_bamic_mri",
        "title_fr": "Aspect IRM temporel de la cicatrisation post-opératoire après réparation proximale du complexe musculo-tendineux des ischio-jambiers",
        "modality": "IRM 3 Tesla",
        "intervention_type": "Suivi IRM Post-Opératoire",
        "cochin_link": "Étude de référence (Skeletal Radiology 2026, équipe Barça / Lempainen / Kassarjian) indispensable pour interpréter les IRM de contrôle post-opératoires chez le footballeur sans conclure à tort à un retard de cicatrisation.",
        "summary_fr_short": "Suivi longitudinal par 43 IRM 3T durant les 4 premiers mois après réparation chirurgicale chez 20 footballeurs professionnels. Des fentes intra-tendineuses résiduelles persistent dans ~40 % des cas malgré une cicatrice mature et une évolution clinique normale.",
        "summary_fr_detailed": "Lors du suivi IRM post-opératoire précoce (< 4 mois) des réparations proximales chez le footballeur professionnel, des fentes intra-tendineuses longitudinales (73,3 %) et transversales (86,7 %), une angulation tendineuse (100 %) et un œdème de dénervation musculaire (66,7 %) sont quasi constants initialement. Même lorsque la cicatrice devient mature en hyposignal, des fentes intra-tendineuses persistent dans ~40 % des tendons asymptomatiques : seules les cavités extensives en franc hypersignal DP-FatSat avec cicatrice immature signent une exacerbation clinique.",
        "protocol_fr": "IRM 3T séquentielle dans les 4 premiers mois post-opératoires • Analyse de la maturation du cal fibreux en T1/DP-FS sans sur-interpréter les fentes linéaires résiduelles de remodelage.",
        "key_points_fr": [
            "La présence de fentes intra-tendineuses (73–87 %) et d'un signal de dénervation (67 %) est habituelle dans les 4 premiers mois.",
            "Une fente résiduelle au sein d'un tendon remodelé en hyposignal mature ne contre-indique pas la progression vers le retour au jeu.",
            "Seule l'association fente large + cavité liquide + cicatrice immature corrèle avec une rechute clinique."
        ],
        "tags": ["IRM post-opératoire", "Cicatrisation tendineuse", "Football professionnel", "Skeletal Radiol 2026"]
    },
    "42530617": {
        "category_id": "imaging_bamic_mri",
        "title_fr": "Caractérisation en imagerie des lésions sportives des ischio-jambiers : sémiologie IRM et classifications",
        "modality": "IRM Diagnostique",
        "intervention_type": "Revue Sémiologique IRM",
        "cochin_link": "Synthèse radiologique complète 2026 (*Skeletal Radiology*) standardisant le compte-rendu IRM entre radiologues ostéo-articulaires, médecins du sport et chirurgiens orthopédistes.",
        "summary_fr_short": "Mise au point exhaustive sur la sémiologie IRM des lésions des ischio-jambiers chez l'athlète : topographie exacte (BFlh, ST, SM), atteinte de la jonction myo-tendineuse ou du tendon central, avulsions proximales et critères pronostiques de rechute.",
        "summary_fr_detailed": "Cet article de synthèse détaille les patterns lésionnels IRM des trois chefs ischio-jambiers selon le mécanisme traumatique (sprint haute vitesse touchant le long biceps fémoral vs étirement forcé en flexion de hanche/extension de genou touchant le semi-membraneux proximal). Il compare les classifications internationales (Munich, BAMIC, Barcelone) et insiste sur la description standardisée de l'atteinte tendineuse intra-musculaire, de la perte de tension et de la rétraction pour guider l'indication chirurgicale ou le délai de RTP.",
        "protocol_fr": "Protocole IRM Cuisse/Bassin : coupes axiales, coronales et sagittales T1 et DP/T2 Fat-Sat grand champ incluant la tubérosité ischiatique et la bifurcation distale.",
        "key_points_fr": [
            "Deux mécanismes distincts : sprint (chef long du biceps fémoral) vs étirement extrême (semi-membraneux proximal).",
            "Nécessité d'un langage standardisé entre radiologue et chirurgien (intégrité du tendon central, perte de tension, gap).",
            "Identification précoce des lésions à haut risque chirurgical (avulsions tubérositaires et ruptures du tendon libre)."
        ],
        "tags": ["IRM", "Sémiologie", "Classification", "Biceps fémoral", "Skeletal Radiol 2026"]
    },
    "39171445": {
        "category_id": "imaging_bamic_mri",
        "title_fr": "Le « Signe du Cobra » en IRM : un nouveau marqueur de surestimation de la rétraction tendineuse dans l'avulsion proximale du semi-membraneux",
        "modality": "IRM & Chirurgie",
        "intervention_type": "Sémiologie IRM (Signe du Cobra)",
        "cochin_link": "Découverte sémiologique majeure de l'équipe du Dr Nicolas Lefèvre : l'aspect en tête de cobra du moignon du semi-membraneux entraîne une surestimation radiologique moyenne de 2 cm (21 %) de la rétraction réelle.",
        "summary_fr_short": "Étude de 81 avulsions proximales opérées définissant le « Signe du Cobra » en IRM (bande hypo-T2 ondulée dont l'extrémité libre se replie distalement sur elle-même). Ce signe a une spécificité de 83,3 % pour le semi-membraneux et surestime la rétraction de 21 % (10,05 cm en IRM vs 7,9 cm en chirurgie).",
        "summary_fr_detailed": "En IRM sagittale/coronale T2, l'extrémité proximale avulsée du tendon semi-membraneux se replie souvent distalement sur elle-même en prenant la forme d'une tête de cobra dressée. Identifié chez 25 patients sur 81, ce signe présente une spécificité de 83,3 % (LR+ = 3,0) pour une avulsion du semi-membraneux. Surtout, les radiologues mesurent souvent la distance entre l'ischion et le dôme du pli plutôt que l'extrémité réelle repliée : la rétraction mesurée en IRM est de 10,05 ± 3,0 cm alors qu'elle n'est que de 7,9 ± 2,5 cm en per-opératoire après déroulement du tendon (différence moyenne de 2,0 cm, soit 21 % de surestimation).",
        "protocol_fr": "Recherche systématique du Signe du Cobra sur les coupes sagittales et coronales T2/DP-FS • Ne pas récuser une réinsertion primaire directe sur la seule foi d'une rétraction IRM apparente de 10 cm si le signe du Cobra est présent.",
        "key_points_fr": [
            "Définition du Signe du Cobra : repli distal en crosse de l'extrémité libre hypo-T2 du tendon semi-membraneux.",
            "Spécificité de 83,3 % et rapport de vraisemblance positif de 3,0 pour l'avulsion du semi-membraneux.",
            "Surestimation moyenne de la rétraction en IRM de 2,0 cm (10,05 cm en IRM contre 7,9 cm réels en chirurgie, soit -21 %).",
            "Impact chirurgical direct : évite de prévoir à tort une allogreffe alors qu'une réinsertion directe est réalisable une fois le tendon déroulé."
        ],
        "tags": ["Signe du Cobra", "IRM", "Semi-membraneux", "Rétraction tendineuse", "KSSTA 2025"]
    },
    "38769849": {
        "category_id": "imaging_bamic_mri",
        "title_fr": "L'IRM doit être l'examen de première intention devant toute suspicion d'avulsion proximale des ischio-jambiers (vs Échographie)",
        "modality": "IRM vs Échographie",
        "intervention_type": "Parcours Diagnostique",
        "cochin_link": "Démonstration sur 392 patients de la cohorte PHAS que prescrire une échographie en premier retarde la chirurgie de 10 jours (30 j vs 20 j) et dégrade les scores sportifs finaux (Tegner et UCLA).",
        "summary_fr_short": "Sur 392 patients opérés d'une avulsion proximale, ceux ayant bénéficié d'une IRM d'emblée sont opérés nettement plus tôt (médiane 20 jours vs 30 jours après échographie première) et obtiennent de meilleurs scores d'activité Tegner et UCLA à 4–5 ans.",
        "summary_fr_detailed": "L'échographie initiale en traumatologie des ischio-jambiers méconnaît fréquemment les avulsions proximales profondes (masquées par l'hématome fessier et l'épaisseur des parties molles) ou sous-estime le nombre de tendons rompus. Dans cette étude de 392 patients (2012–2020), la réalisation d'une IRM en première intention réduit de 10 jours le délai médian jusqu'à la chirurgie (20 jours vs 30 jours, restant ainsi largement sous le seuil critique des 32 jours) et permet des scores fonctionnels Tegner (médiane 5 vs 4) et UCLA significativement supérieurs au dernier recul.",
        "protocol_fr": "Bannir l'échographie isolée devant un traumatisme proximal sévère de la loge postérieure • Prescrire d'emblée une IRM du bassin/cuisse en urgence différée (< 7–10 jours).",
        "key_points_fr": [
            "Analyse comparative de 392 patients : groupe 'IRM d'emblée' vs groupe 'Échographie d'emblée'.",
            "Gain de 10 jours sur le délai chirurgical médian grâce à l'IRM première (20 jours contre 30 jours).",
            "Meilleurs résultats sportifs à long terme (scores Tegner et UCLA supérieurs) dans le groupe IRM première.",
            "Permet d'opérer les patients avant la barrière pronostique des 32 jours."
        ],
        "tags": ["IRM première intention", "Échographie", "Délai diagnostique", "Cohorte PHAS", "KSSTA 2024"]
    },
    "40985316": {
        "category_id": "imaging_bamic_mri",
        "title_fr": "Présentation clinique et progression de la rééducation des lésions des ischio-jambiers selon la classification BAMIC chez l'athlète d'élite",
        "modality": "IRM & Clinique (BAMIC)",
        "intervention_type": "Classification BAMIC (Type c)",
        "cochin_link": "Établit les corrélations clinico-radiologiques des lésions du tendon intramusculaire (BAMIC type 'c') chez les athlètes d'élite : douleur plus élevée à la marche et délai prolongé avant reprise du footing indolore.",
        "summary_fr_short": "Chez l'athlète d'athlétisme d'élite, les lésions touchant le tendon central/intramusculaire (BAMIC classe 'c') entraînent une EVA douleur supérieure à la marche et à la contraction résistée, ainsi qu'un allongement significatif du délai de retour à l'entraînement complet (TRFT).",
        "summary_fr_detailed": "Étude prospective menée auprès d'athlètes de haut niveau corrélant l'examen clinique initial, le grade IRM BAMIC (0 à 4, sous-types a myofascial, b jonction myo-tendineuse, c intra-tendineux) et le temps de retour à l'entraînement complet (TRFT). Fait notable : 30 % des athlètes présentaient des lombalgies ou des crampes/raideurs des ischio-jambiers dans la semaine précédant la déchirure. Les lésions intra-tendineuses de classe 'c' mettent significativement plus de temps à retrouver une extension passive indolore du genou et un footing sans douleur. La disparition de la douleur à la palpation (p = 0,69) ne prédit pas le délai de retour au jeu, contrairement au test MHFAKE et au test H d'Askling.",
        "protocol_fr": "Classification IRM BAMIC systématique (grade 0–4 et site a/b/c) • Surveillance clinique par test MHFAKE (Maximal Hip Flexion Active Knee Extension) et Askling H-test avant autorisation du sprint.",
        "key_points_fr": [
            "30 % des ruptures aiguës sont précédées de lombalgies ou de tensions/crampes dans les 7 jours avant l'accident.",
            "Les lésions du tendon intramusculaire (BAMIC 'c') ont une EVA plus élevée à la marche et un TRFT nettement allongé.",
            "La douleur à la palpation locale (p = 0,69) n'est pas un bon marqueur pronostique, contrairement au déficit d'amplitude MHFAKE et au test d'Askling."
        ],
        "tags": ["BAMIC", "Tendon intramusculaire", "Athlétisme élite", "Askling H-test", "Scand J Med Sci Sports 2025"]
    },
    "36650035": {
        "category_id": "imaging_bamic_mri",
        "title_fr": "Consensus International de Londres (Partie 1) : Classification des lésions des ischio-jambiers",
        "modality": "Consensus International",
        "intervention_type": "Classification BAMIC & IRM",
        "cochin_link": "Premier volet du Consensus International de Londres (F. Haddad, B. Paton et 112 experts mondiaux, BJSM 2023) consacrant la classification BAMIC comme standard international (utilisée par 58 % des experts).",
        "summary_fr_short": "Étude Delphi internationale réunissant 112 experts mondiaux des ischio-jambiers. La classification BAMIC (British Athletics Muscle Injury Classification) est la plus utilisée au monde (58 %), devant Munich (12 %) et Barcelone (6 %).",
        "summary_fr_detailed": "Ce consensus international recommande d'enrichir la classification IRM BAMIC en précisant systématiquement : le muscle individuel atteint (BFlh, BFsh, ST, SM), la zone anatomique exacte (insertion proximale, tendon libre, jonction myo-tendineuse, tendon central intramusculaire, jonction distale en T), le mécanisme lésionnel (sprint vs étirement/overstretch), la perte de tension tendineuse ('loss of tension' / 'gapping') et le niveau d'exigence sportive du patient.",
        "protocol_fr": "Compte-rendu structuré combinant BAMIC (Grade 0–4 + suffixe a/b/c) + Muscle spécifique + Mesure du gap tendineux et de la perte de tension.",
        "key_points_fr": [
            "88,4 % de taux de réponse au second tour Delphi parmi 112 experts internationaux.",
            "La classification BAMIC est plébiscitée par 58 % des centres experts dans le monde.",
            "Nécessité d'intégrer la spécificité de chaque chef musculaire (SM vs BFlh vs ST) et le mécanisme lésionnel."
        ],
        "tags": ["Consensus de Londres", "BAMIC", "Classification IRM", "Delphi", "BJSM 2023"]
    },
    "42281221": {
        "category_id": "pht_endoscopy_sciatic",
        "title_fr": "Ténotomie partielle et réinsertion pour tendinopathie proximale chronique des ischio-jambiers (PHT) : résultats fonctionnels et retour au sport",
        "modality": "Chirurgie & Tendinopathie",
        "intervention_type": "Ténotomie Partielle & Réinsertion",
        "cochin_link": "Nouvelle publication 2026 dans l'AJSM de l'équipe du Dr Nicolas Lefèvre validant la chirurgie de ténotomie-réinsertion sur ancres dans les tendinopathies proximales chroniques réfractaires (> 6 mois).",
        "summary_fr_short": "Sur 42 patients (âge moyen 50,4 ans, suivi moyen 4,1 ans) opérés d'une tendinopathie proximale chronique (PHT) résistante à > 6 mois de traitement médical, la ténotomie partielle avec réinsertion sur ancres fait passer le score PHAS de 63,0 à 84,2 (p < 0,001).",
        "summary_fr_detailed": "La tendinopathie proximale chronique des ischio-jambiers (PHT), caractérisée par des douleurs ischiatiques basses en position assise et à la course sans rupture franche, peut devenir rebelle à la rééducation excentrique, aux ondes de choc et aux infiltrations de PRP. Cette étude de cohorte évalue l'excision des zones de tendinose dégénérative (ténotomie partielle) associée à une réinsertion trans-osseuse sur ancres et neurolyse sciatique à la demande. À plus de 4 ans de recul moyen (2 à 12,6 ans), le score PHAS progresse de 21,2 points (63,0 à 84,2) avec un taux élevé de retour au sport et de satisfaction.",
        "protocol_fr": "Indication : PHT symptomatique réfractaire > 6 mois • Abord sous-fessier court • Excision du tissu tendineux nécrotique/fissuraire et avivement de la tubérosité ischiatique • Réinsertion solide par ancres de suture.",
        "key_points_fr": [
            "Série de 42 patients suivis en moyenne 4,1 ans (jusqu'à 12,6 ans).",
            "Amélioration hautement significative du score PHAS moyen de 63,0 ± 11,4 à 84,2 ± 18,2.",
            "Alternative chirurgicale fiable et efficace lorsque les traitements conservateurs (excentrique, PRP, ondes de choc) échouent après 6 mois."
        ],
        "tags": ["Tendinopathie proximale (PHT)", "Ténotomie-réinsertion", "Cohorte PHAS", "Douleur assise", "AJSM 2026"]
    },
    "42144919": {
        "category_id": "pht_endoscopy_sciatic",
        "title_fr": "Réparation endoscopique des ruptures proximales des ischio-jambiers : sécurité et résultats maintenus à plus de 6 ans de recul minimum",
        "modality": "Chirurgie Endoscopique",
        "intervention_type": "Réinsertion Endoscopique",
        "cochin_link": "Confirme la durabilité à long terme (suivi moyen 7,6 ans, min 6,2 ans) de la réparation endoscopique pour les lésions partielles ou complètes peu rétractées.",
        "summary_fr_short": "Suivi à moyen/long terme (6,2 à 10,6 ans, moyenne 7,6 ans) de réparations endoscopiques proximales des ischio-jambiers : score HOS-Sports moyen de 89,2/100, EVA douleur à 1,7/10, 86,4 % de satisfaction et 85,7 % des patients atteignant le seuil PASS.",
        "summary_fr_detailed": "La chirurgie endoscopique de l'espace sous-fessier profond permet de visualiser magnifiquement la tubérosité ischiatique, de réaliser une neurolyse endoscopique prudente du nerf sciatique et de réinsérer par ancres les déchirures partielles de haut grade ou les avulsions complètes non rétractées. À 7,6 ans de recul moyen, les scores fonctionnels (mHHS 82,6 ; HOS 83,2 ; HOS-SSS 89,2 ; SANE 80,2 %) démontrent le maintien pérenne du bénéfice clinique avec une morbidité cicatricielle minimale.",
        "protocol_fr": "Installation en décubitus ventral • Deux ou trois voies d'abord dans le pli sous-fessier • Bursectomie ischiatique, repérage et protection du nerf sciatique en latéral • Avivement osseux et réparation trans-tendineuse par ancres sous contrôle endoscopique.",
        "key_points_fr": [
            "Plus long suivi publié (moyenne 7,6 ans, jusqu'à 10,6 ans) pour la réparation endoscopique proximale.",
            "86,4 % de satisfaction globale et 85,7 % des patients atteignant un état symptomatique acceptable (PASS).",
            "Indication privilégiée : ruptures partielles de haut grade, tendinopathies fissuraires et avulsions aiguës peu rétractées (< 2–3 cm)."
        ],
        "tags": ["Endoscopie", "Espace sous-fessier", "PASS", "Réinsertion par ancres", "Arthroscopy 2026"]
    },
    "42785966": {
        "category_id": "pht_endoscopy_sciatic",
        "title_fr": "L'atteinte œdémateuse du nerf sciatique en IRM allonge significativement le délai de retour au sport après lésion aiguë des ischio-jambiers",
        "modality": "IRM & Nerf Sciatique",
        "intervention_type": "Pronostic IRM Péri-Sciatique",
        "cochin_link": "Étude prospective (BJSM 2026) montrant que l'engainement œdémateux circonférentiel du nerf sciatique en IRM initiale est présent dans 41,7 % des lésions aiguës chez le joueur de football américain et retarde significativement le retour au jeu.",
        "summary_fr_short": "Sur 96 lésions aiguës des ischio-jambiers explorées par IRM en NCAA Division I, un contact œdémateux avec le nerf sciatique est observé dans 78,1 % des cas (36,5 % partiel, 41,7 % circonférentiel complet) et corrèle directement avec un délai de retour au sport prolongé.",
        "summary_fr_detailed": "En raison de la proximité anatomique intime entre le nerf sciatique et le complexe proximal/moyen des ischio-jambiers (notamment le long biceps fémoral et le semi-membraneux), l'hématome et l'œdème post-traumatiques diffusent fréquemment dans la gaine péri-nerveuse. Cette étude prospective démontre que l'œdème circonférentiel complet autour du nerf sciatique augmente avec le grade BAMIC et constitue un facteur pronostique indépendant d'allongement de l'indisponibilité sportive.",
        "protocol_fr": "Évaluation systématique sur les coupes axiales T2/DP-FatSat du rapport entre l'œdème musculaire et le nerf sciatique : absence de contact, contact partiel (< 180°) ou engainement circonférentiel complet (360°).",
        "key_points_fr": [
            "L'œdème entre en contact avec le nerf sciatique dans 78,1 % des lésions aiguës (dont 41,7 % d'engainement complet).",
            "Corrélation significative entre le grade BAMIC, l'engainement sciatique complet et le nombre de jours d'arrêt sportif.",
            "Justifie l'intégration d'exercices de mobilisation neurodynamique douce du nerf sciatique durant la rééducation."
        ],
        "tags": ["Nerf sciatique", "IRM", "BAMIC", "Retour au sport", "BJSM 2026"]
    },
    "36650033": {
        "category_id": "pht_endoscopy_sciatic",
        "title_fr": "Consensus International de Londres (Partie 2) : Indications et prise en charge chirurgicale des lésions des ischio-jambiers",
        "modality": "Consensus Chirurgical",
        "intervention_type": "Indications Opératoires",
        "cochin_link": "Second volet du Consensus de Londres (R. Plastow, G. Kerkhoffs, F. Haddad et al., BJSM 2023) fixant les critères formels d'indication chirurgicale avec > 87 % d'accord international.",
        "summary_fr_short": "Le panel international de 112 experts valide trois indications chirurgicales majeures : le gap tendineux avec perte de tension (87,2 % d'accord), les avulsions osseuses déplacées symptomatiques (72,8 %), et les lésions du tendon libre proximal réfractaires au traitement conservateur (72,2 %).",
        "summary_fr_detailed": "Ce consensus Delphi international clarifie la prise de décision chirurgicale devant une lésion des ischio-jambiers. Outre les avulsions proximales complètes, les experts soulignent l'importance mécanique de la « perte de tension » ('loss of tension') et de l'écart inter-fragmentaire ('gapping') sur les tendons proximaux, centraux ou distaux chez l'athlète à haute exigence fonctionnelle. Le consensus rejette formellement les infiltrations de corticoïdes dans les lésions tendineuses aiguës.",
        "protocol_fr": "Critères décisionnels : (1) Anatomie lésionnelle (gap tendineux, perte de tension, nombre de tendons), (2) Exigence sportive du patient, (3) Risque de déficit de force ou de récidive sous traitement conservateur.",
        "key_points_fr": [
            "87,2 % d'accord sur l'indication chirurgicale en cas de gap tendineux avec perte de tension du fuseau musculo-tendineux.",
            "70 % des chirurgiens experts estiment que la réparation chirurgicale réduit significativement le risque de récidive.",
            "Contre-indication consensuelle aux infiltrations de corticoïdes dans les lésions aiguës des ischio-jambiers."
        ],
        "tags": ["Consensus de Londres", "Indications chirurgicales", "Perte de tension", "BJSM 2023"]
    },
    "33855098": {
        "category_id": "distal_tears_t_junction",
        "title_fr": "Réparation chirurgicale des avulsions distales du biceps fémoral chez l'athlète professionnel",
        "modality": "Chirurgie Distale",
        "intervention_type": "Réinsertion Distale Biceps Fémoral",
        "cochin_link": "Série prospective de référence (équipe du Pr Fares Haddad, Londres) sur 22 athlètes d'élite : 100 % de retour au niveau professionnel antérieur en 16,7 semaines après réinsertion par ancres sur la tête fibulaire, avec 0 % de récidive.",
        "summary_fr_short": "Chez 22 sportifs professionnels (football, rugby) opérés en aigu (délai moyen 12 jours) d'une avulsion distale du biceps fémoral par ancres de suture, 100 % reprennent la compétition à leur niveau antérieur en 16,7 ± 8,7 semaines sans aucune récidive à 2 ans.",
        "summary_fr_detailed": "L'avulsion distale du tendon du biceps fémoral à son insertion sur la tête de la fibula est une lésion grave du point d'angle postéro-latéral du genou, exposant à une perte durable de force de flexion/rotation externe si elle est traitée orthopédiquement. Opérée précocement (en moyenne à J12) par réinsertion anatomique sur ancres avec repérage et protection systématique du nerf fibulaire commun (SPE), elle permet un retour intégral au sport professionnel en ~4 mois sans récidive ni complication neurologique.",
        "protocol_fr": "Abord postéro-latéral centré sur la tête fibulaire • Neurolyse et protection première du nerf fibulaire commun (SPE) au col de la fibula • Réinsertion anatomique de l'empreinte distale du biceps fémoral par ancres de suture.",
        "key_points_fr": [
            "100 % de retour au niveau sportif professionnel antérieur chez 22 athlètes d'élite.",
            "Délai moyen de retour à la compétition complète de 16,7 ± 8,7 semaines (~4 mois).",
            "Zéro récidive à 1 et 2 ans de suivi et restauration complète de la force isocinétique.",
            "Protection impérative du nerf fibulaire commun (SPE) lors de l'abord postéro-latéral."
        ],
        "tags": ["Biceps fémoral distal", "Tête de la fibula", "Athlète professionnel", "Nerf fibulaire commun", "OJSM 2021"]
    },
    "32736504": {
        "category_id": "distal_tears_t_junction",
        "title_fr": "Réparation chirurgicale des lésions aiguës de la jonction musculo-tendineuse distale en T (T-junction) du biceps fémoral",
        "modality": "Chirurgie Distale",
        "intervention_type": "Suture de la Jonction en T (DMTJ)",
        "cochin_link": "Alors que le traitement conservateur des lésions de la jonction en T du biceps fémoral s'accompagne de 54 % de récidives, la réparation chirurgicale directe chez 34 professionnels permet 100 % de retour au jeu en 11,7 semaines avec 0 % de rechute.",
        "summary_fr_short": "Étude prospective de 34 athlètes professionnels opérés d'une rupture aiguë de la jonction musculo-tendineuse distale en T (DMTJ) du biceps fémoral : 100 % de retour au niveau pré-lésionnel en 11,7 ± 3,6 semaines et aucune récidive à 28,4 mois de recul moyen.",
        "summary_fr_detailed": "La jonction musculo-tendineuse distale en T (DMTJ) du biceps fémoral, zone de confluence entre le chef long (innervé par le contingent tibial) et le chef court (innervé par le contingent fibulaire commun), est tristement célèbre pour son taux de récidive supérieur à 50 % sous traitement médical. Dans cette série prospective (34 professionnels), la remise en tension et la suture anatomique de l'aponévrose en T réduisent le délai de retour au jeu à moins de 3 mois (11,7 semaines) et suppriment le risque de rechute (0 % à plus de 2 ans).",
        "protocol_fr": "Voie postéro-latérale distale de cuisse • Évacuation de l'hématome et débridement du tissu cicatriciel • Suture anatomique bord à bord en paletot des feuillets aponévrotiques des chefs long et court du biceps fémoral.",
        "key_points_fr": [
            "34 athlètes professionnels suivis pendant 28,4 mois en moyenne.",
            "Retour complet à la compétition en 11,7 ± 3,6 semaines (< 3 mois).",
            "Taux de récidive ramené à 0 % (contre > 50 % dans la littérature non chirurgicale).",
            "100 % des joueurs satisfaits ou très satisfaits avec récupération symétrique de la force à 3 mois."
        ],
        "tags": ["Jonction en T (T-junction)", "Biceps fémoral distal", "Chirurgie", "Zéro récidive", "AJSM 2020"]
    },
    "28795071": {
        "category_id": "distal_tears_t_junction",
        "title_fr": "Lésions de la jonction musculo-tendineuse distale en T du biceps fémoral : sémiologie IRM et haut risque de récidive (54 %)",
        "modality": "IRM Diagnostique",
        "intervention_type": "Sémiologie IRM Jonction en T",
        "cochin_link": "Article fondateur d'Entwisle, Brukner et Connell décrivant l'anatomie IRM en T de la confluence distale des chefs long et court du biceps fémoral et démontrant son taux redoutable de récidive (54 %).",
        "summary_fr_short": "Analyse de 106 IRM chez 55 patients présentant une lésion de la jonction distale en T (DMTJ) du biceps fémoral : le chef long est touché isolément dans 51 % des cas et les deux chefs dans 43 %. Le taux de récidive sous traitement conservateur atteint 54 %, dont 76 % dans les 3 premiers mois.",
        "summary_fr_detailed": "En coupe axiale IRM au tiers distal de la cuisse, l'aponévrose distale du chef long et celle du chef court du biceps fémoral fusionnent selon une configuration en « T ». En raison de la double innervation (nerf tibial pour le chef long, nerf fibulaire commun pour le chef court) et des contraintes de cisaillement lors du sprint, les lésions de cette jonction en T récidivent dans 54 % des cas, et dans 86 % des cas la rechute est de grade égal ou plus sévère que la lésion initiale.",
        "protocol_fr": "Analyse fine sur les coupes axiales T2/DP-FS distales des deux bras du 'T' aponévrotique (composante du chef long, composante du chef court, ou dissociation complète des deux).",
        "key_points_fr": [
            "Entité anatomique et clinique distincte : 51 % d'atteinte du chef long seul, 43 % d'atteinte combinée des deux chefs.",
            "Taux de récidive exceptionnellement élevé de 54 % sous traitement rééducatif seul.",
            "76 % des rechutes surviennent dans les 3 mois suivant la reprise et 86 % sont au moins aussi graves que la lésion initiale."
        ],
        "tags": ["Jonction en T (DMTJ)", "IRM", "Récidive", "Double innervation", "OJSM 2017"]
    },
    "42169801": {
        "category_id": "scores_rehab_prevention",
        "title_fr": "Développement et validation de la version courte du Parisian Hamstring Avulsion Score : le Short-PHAS (12 items)",
        "modality": "Score Clinique (PROM)",
        "intervention_type": "Validation du Short-PHAS",
        "cochin_link": "Validation sur 335 patients opérés (Clinique du Sport / Cochin / Pitié, 2026) du *Short-PHAS* en 12 items : corrélation de 0,94 avec le PHAS long et prédiction fiable du retour au sport au niveau antérieur (seuil 47/65).",
        "summary_fr_short": "Sur une cohorte prospective de 335 patients opérés d'une avulsion proximale, le score Short-PHAS (réduit de 36 à 12 items, sur 65 points) démontre une excellente cohérence interne (α = 0,85), une corrélation de r = 0,94 avec le PHAS complet et une bonne valeur prédictive du retour au sport (AUC = 0,75).",
        "summary_fr_detailed": "Pour faciliter le suivi clinique quotidien en consultation et par télé-suivi, l'équipe parisienne a développé une version condensée en 12 items du Parisian Hamstring Avulsion Score (notée sur 65 points). Validé sur 335 patients (âge moyen 48 ± 10 ans), le Short-PHAS conserve les mêmes performances psychométriques et prédictives que le score long de 36 items : un score seuil de 39/65 prédit la reprise sportive globale, 46/65 la reprise du même sport, et 47/65 le retour au niveau sportif pré-lésionnel (AUC = 0,75).",
        "protocol_fr": "Auto-questionnaire rapide en 12 items (sur 65 points) administré en pré-opératoire puis à 4, 8 et 12 mois • Seuil cible ≥ 47/65 pour autoriser le retour à la compétition au niveau antérieur.",
        "key_points_fr": [
            "Réduction de 36 à 12 items permettant un remplissage ultra-rapide en consultation ou sur smartphone.",
            "Corrélation quasi-parfaite avec le score PHAS original (r = 0,94 ; Cronbach α = 0,85) sur 335 patients.",
            "Seuils décisionnels validés sur 65 points : 39/65 (RTS global), 46/65 (même sport), 47/65 (niveau pré-lésionnel)."
        ],
        "tags": ["Short-PHAS", "Score clinique", "Retour au sport", "Validation psychométrique", "OJSM 2026"]
    },
    "41306750": {
        "category_id": "scores_rehab_prevention",
        "title_fr": "Validation du score Hip-RSI pour évaluer l'aptitude psychologique au retour au sport après chirurgie d'avulsion proximale des ischio-jambiers",
        "modality": "Score Psychologique (RSI)",
        "intervention_type": "Évaluation Psychologique RTS",
        "cochin_link": "Transpose aux ischio-jambiers l'approche psychologique que le Dr Nicolas Lefèvre avait popularisée avec l'ACL-RSI pour le genou : un score Hip-RSI > 51,7 à 4 mois prédit le retour au sport à 9 mois.",
        "summary_fr_short": "Étude prospective sur 84 patients opérés d'une avulsion proximale évaluant le score psychologique Hip-RSI à 4 et 9 mois. Fortement corrélé au PHAS (r = 0,55 ; ICC = 0,89), un seuil de Hip-RSI ≥ 51,7/100 à 4 mois prédit le retour au sport antérieur à 9 mois (AUC = 0,76).",
        "summary_fr_detailed": "L'appréhension de la rechute (kinésiophobie) lors du sprint ou de la flexion de tronc est un frein majeur au retour au sport après réinsertion proximale des ischio-jambiers. Cette étude valide l'utilisation du score Hip-RSI (Return to Sport after Injury) chez 84 patients actifs. Le score présente une excellente reproductibilité (ICC = 0,89) et une bonne capacité discriminante (AUC = 0,76) : dès le 4e mois post-opératoire, un score Hip-RSI supérieur à 51,7 prédit le retour au sport pré-lésionnel à 9 mois avec une spécificité de 77 %.",
        "protocol_fr": "Passation conjointe du Short-PHAS et du Hip-RSI à 4 mois et 9 mois post-opératoires • Accompagnement mental et réathlétisation progressive si Hip-RSI < 52 à 4 mois.",
        "key_points_fr": [
            "Première validation d'un score psychologique de préparation au retour au sport (Hip-RSI) pour les ischio-jambiers.",
            "Excellente fiabilité test-retest (ICC = 0,89) et corrélation significative avec le score fonctionnel PHAS (r = 0,55).",
            "Seuil prédictif à 4 mois : Hip-RSI ≥ 51,7/100 (sensibilité 69 %, spécificité 77 %, AUC = 0,76 pour le RTS à 9 mois)."
        ],
        "tags": ["Hip-RSI", "Psychologie du sport", "Kinésiophobie", "Cohorte PHAS", "OJSM 2025"]
    },
    "38353118": {
        "category_id": "scores_rehab_prevention",
        "title_fr": "Validation du Parisian Hamstring Avulsion Score (PHAS) dans l'évaluation et le suivi des patients opérés d'une avulsion proximale",
        "modality": "Score de Référence (PHAS)",
        "intervention_type": "Création & Validation du PHAS",
        "cochin_link": "Article fondateur dans l'AJSM (Dr Nicolas Lefèvre et al., 2024) établissant le score PHAS comme gold standard spécifique d'évaluation fonctionnelle et de prédiction du retour au sport après avulsion proximale.",
        "summary_fr_short": "Validation prospective sur 156 patients (suivi moyen 69 mois) du Parisian Hamstring Avulsion Score (PHAS). Excellente fiabilité (ICC = 0,96 ; Cronbach α = 0,86 ; absence d'effet plafond). Un score PHAS ≥ 86/100 à 9 mois prédit le retour au sport à 1 an avec une spécificité de 81,4 %.",
        "summary_fr_detailed": "Avant le PHAS, aucun score validé en langue française ou internationale ne permettait de prédire le retour au sport après chirurgie d'avulsion proximale des ischio-jambiers. Sur 156 patients opérés par ancres et suivis plus de 5,5 ans, le PHAS démontre une reproductibilité remarquable (ICC = 0,96), une variation minimale détectable (MDC) de 12,9 points, et une forte corrélation avec les scores UCLA et Tegner. À 9 mois post-opératoires, une valeur seuil de 86/100 prédit la reprise sportive à 1 et 2 ans (spécificité 81,4 %).",
        "protocol_fr": "Évaluation par le score PHAS (sur 100 points) à 6, 9, 12 et 24 mois • Cible décisionnelle à 9 mois : PHAS ≥ 86/100.",
        "key_points_fr": [
            "Excellentes propriétés psychométriques sur 156 patients : Cronbach α = 0,86 et ICC = 0,96.",
            "Absence totale d'effet plafond à 2 ans, permettant de discriminer finement les sportifs exigeants.",
            "Seuil prédictif à 9 mois : PHAS ≥ 86/100 (spécificité de 81,4 % pour le retour au sport à 1 an)."
        ],
        "tags": ["PHAS", "Score de référence", "Retour au sport", "Validation", "AJSM 2024"]
    },
    "42324766": {
        "category_id": "scores_rehab_prevention",
        "title_fr": "Essai randomisé PHARRLAP à 2 ans : Rééducation accélérée sans attelle et appui immédiat vs Protocole conservateur après réinsertion proximale",
        "modality": "Essai Randomisé (Niveau I)",
        "intervention_type": "Rééducation Post-Opératoire",
        "cochin_link": "Essai contrôlé randomisé de niveau I (AJSM 2026) démontrant que l'appui complet immédiat selon tolérance sans attelle de genou donne des résultats fonctionnels et isocinétiques équivalents à 2 ans sans augmenter les re-ruptures.",
        "summary_fr_short": "Essai randomisé comparant 27 patients sous protocole accéléré (sans attelle, appui complet immédiat selon tolérance) et 30 patients sous protocole restreint (6 semaines d'attelle et décharge partielle) après réparation aiguë d'au moins 2 tendons : résultats cliniques, isocinétiques et taux de re-rupture identiques à 2 ans.",
        "summary_fr_detailed": "L'immobilisation post-opératoire par attelle articulée de genou ou de hanche est souvent mal tolérée par les patients. L'essai randomisé PHARRLAP montre que chez des patients opérés en aigu d'une avulsion d'au moins 2 tendons, le groupe sans attelle avec appui immédiat toléré présente moins de douleurs à 3 et 12 mois, un meilleur score physique SF-12 à 3 mois, et une symétrie de force isocinétique des fléchisseurs (LSI PKFT) et de saut monopodal strictement équivalente à 6, 12 et 24 mois (2 re-ruptures dans chaque groupe sur 2 ans).",
        "protocol_fr": "Protocole accéléré (AR) : absence d'attelle de genou, marche en appui complet protégé par cannes selon confort dès J1, éviction des flexions de tronc jambes tendues pendant 6 semaines, renforcement progressif dès S6.",
        "key_points_fr": [
            "Étude randomisée contrôlée de Niveau I avec suivi clinique et isocinétique complet à 3, 6, 12 et 24 mois.",
            "Moins de douleurs à 3 et 12 mois dans le groupe sans attelle avec remise en charge selon tolérance.",
            "Récupération identique du couple de force isocinétique des fléchisseurs et du hop-test à 2 ans.",
            "Pas d'augmentation du taux de re-rupture précoce en l'absence d'attelle rigide de genou."
        ],
        "tags": ["Essai randomisé (RCT)", "Rééducation post-opératoire", "Attelle", "Isocinétisme", "AJSM 2026"]
    },
    "39461588": {
        "category_id": "scores_rehab_prevention",
        "title_fr": "Adaptations multi-échelles des ischio-jambiers après 9 semaines d'entraînement excentrique (Nordic Hamstring) : ajout de sarcomères en série",
        "modality": "Biomécanique & Prévention",
        "intervention_type": "Nordic Hamstring Exercise (NHE)",
        "cochin_link": "Preuve directe in vivo chez l'humain (micro-endoscopie par seconde harmonique + IRM, Stanford/Queensland 2025) que l'exercice Nordic Hamstring allonge les fascicules du long biceps de +33 % par addition réelle de sarcomères en série (+49 %).",
        "summary_fr_short": "Après 9 semaines d'entraînement supervisé en Nordic Hamstring Exercise (NHE), la force excentrique augmente de +40 %, la longueur des fascicules du chef long du biceps fémoral augmente de +33 % en distal, grâce à une addition mesurée de +49 % de sarcomères en série.",
        "summary_fr_detailed": "Pour la première fois chez l'humain, cette étude combine l'échographie 3D, l'IRM et la micro-endoscopie optique non linéaire pour mesurer directement le nombre de sarcomères en série au sein du chef long du biceps fémoral (BFlh). Neuf semaines de Nordic Hamstring induisent une hypertrophie (+8 % de volume), un gain de force de flexion de +40 %, et une sarcomerogenèse longitudinale massive (+25 % au centre, +49 % en distal). Attention toutefois : un désentraînement de seulement 3 semaines fait reperdre la moitié de ce gain de longueur fasciculaire (-16 %), imposant un maintien continu en saison.",
        "protocol_fr": "Programme Nordic Hamstring supervisé sur 9 semaines + maintien hebdomadaire obligatoire en saison pour prévenir la réversion rapide (dès 3 semaines d'arrêt) des sarcomères en série.",
        "key_points_fr": [
            "Démonstration directe in vivo de la sarcomerogenèse en série (+49 % en région distale du BFlh).",
            "Allongement fasciculaire de +19 % (zone centrale) à +33 % (zone distale) et +40 % de force excentrique.",
            "Réversibilité rapide : 3 semaines d'arrêt suffisent à perdre ~16 % de longueur fasciculaire (nécessité d'une dose d'entretien hebdomadaire)."
        ],
        "tags": ["Nordic Hamstring", "Sarcomères en série", "Biceps fémoral", "Prévention", "J Sport Health Sci 2025"]
    },
    "36650032": {
        "category_id": "scores_rehab_prevention",
        "title_fr": "Consensus International de Londres (Partie 3) : Rééducation, course haute vélocité et critères de retour au sport (RTS)",
        "modality": "Consensus Rééducation",
        "intervention_type": "Protocole Réathlétisation & RTS",
        "cochin_link": "Troisième volet du Consensus de Londres (BJSM 2023) établissant les règles d'or de la progression rééducative, de l'exposition au sprint et de la validation du retour sur le terrain.",
        "summary_fr_short": "Consensus international (112 experts) sur la rééducation des ischio-jambiers : individualisation selon le muscle et le mécanisme (89,8 %), intégration de la chaîne cinétique lombo-pelvienne (95 %), et exigence d'un sprint maximal totalement indolore avant retour au jeu (85,5 %).",
        "summary_fr_detailed": "Les experts internationaux s'accordent sur une progression guidée par la capacité fonctionnelle plutôt que par des délais fixes. Le contrôle de l'antéversion pelvienne et de la chaîne cinétique (tronc, fessiers, triceps sural) fait l'objet d'un consensus massif (95 %). Si une gêne légère contrôlée est tolérée lors de certains exercices de renforcement lent, l'exposition progressive à la course à très haute vitesse (sprint > 90–95 % Vmax) doit impérativement être indolore (85,5 % d'accord) avant de valider le retour à la compétition.",
        "protocol_fr": "3 phases validées par critères : (1) Protection et mise en charge isométrique/concentrique précoce, (2) Renforcement excentrique allongé (Askling L-protocol / Slider / Diver) + contrôle pelvien, (3) Sprint haute vélocité indolore et situations spécifiques au poste.",
        "key_points_fr": [
            "95 % d'accord sur le traitement conjoint de la chaîne cinétique (contrôle lombo-pelvien et antéversion du bassin).",
            "Combinaison d'exercices à dominante hanche (allongement élevé : Diver, RDL) et à dominante genou (Nordic, Slider).",
            "Critère absolu avant RTS : réalisation de sprints répétés à vitesse maximale strictement indolores (85,5 % d'accord)."
        ],
        "tags": ["Consensus de Londres", "Rééducation", "Sprint", "Critères RTS", "BJSM 2023"]
    },
    "42310826": {
        "category_id": "acl_graft_harvest",
        "title_fr": "Reconstruction du LCA par autogreffe d'ischio-jambiers préservant l'insertion tibiale : maturation IRM accélérée (Essai randomisé)",
        "modality": "Plastie LCA & IRM",
        "intervention_type": "Greffe DIDT Pédiculée (Attachment-Sparing)",
        "cochin_link": "Essai contrôlé randomisé de Niveau I (AJSM 2026) prouvant que conserver l'insertion distale de la patte d'oie lors du prélèvement des ischio-jambiers accélère significativement la ligamentisation IRM (score de Figueroa 5/5 chez 100 % des patients à 9 mois vs 10 % en greffe libre).",
        "summary_fr_short": "Essai randomisé (56 patients, IRM séquentielles à 3, 6 et 9 mois) comparant la plastie du LCA par ischio-jambiers pédiculés sur le tibia (AS) vs greffe libre (FG). Le maintien de l'insertion tibiale évite l'œdème de nécrose avasculaire du greffon et permet une maturation IRM complète chez 100 % des patients à 9 mois.",
        "summary_fr_detailed": "Lors du prélèvement classique du semi-tendineux et du gracilis au stripper pour reconstruction du LCA, le détachement tibial dévascularise totalement le transplant. Dans cet essai randomisé, la préservation de l'attache tibiale native maintient un apport vasculaire et neuro-proprioceptif : dès 3 mois, 26,3 % des greffons pédiculés présentent un score IRM de Figueroa ≥ 4 (contre 0 % à 3 mois pour les greffes libres), et à 9 mois 100 % atteignent le grade maximal de maturation (score 5) sans gonflement œdémateux du greffon.",
        "protocol_fr": "Prélèvement des tendons semi-tendineux et gracilis au stripper ouvert en conservant intacte leur insertion distale sur la patte d'oie • Passage dans les tunnels tibial et fémoral • Contrôle IRM séquentiel (score de Figueroa).",
        "key_points_fr": [
            "Essai randomisé de Niveau I avec suivi IRM longitudinal à 3, 6 et 9 mois.",
            "100 % de maturation IRM optimale (score de Figueroa 5) à 9 mois dans le groupe pédiculé contre 10 % en greffe libre.",
            "Absence de phase de gonflement œdémateux ('graft swelling') du transplant lorsque l'insertion tibiale est préservée."
        ],
        "tags": ["Plastie LCA", "DIDT pédiculé", "Ligamentisation IRM", "Score de Figueroa", "AJSM 2026"]
    },
    "34471958": {
        "category_id": "acl_graft_harvest",
        "title_fr": "Rétraction anatomique du muscle semi-tendineux en IRM après prélèvement tendineux pour reconstruction du LCA",
        "modality": "IRM Bilatérale Comparative",
        "intervention_type": "Morbidité Site Donneur DIDT",
        "cochin_link": "Quantifie précisément en IRM bilatérale le raccourcissement définitif du corps charnu du semi-tendineux après prélèvement pour LCA : 81 mm en moyenne (soit 25 % de sa longueur), expliquant le déficit de force en flexion profonde (> 70–90°).",
        "summary_fr_short": "À 6,8 ans de recul moyen après prélèvement DIDT pour plastie du LCA, l'IRM bilatérale comparative montre une rétraction proximale moyenne de 81 mm (25 % de raccourcissement) du corps musculaire du semi-tendineux par rapport au côté sain (où la variation naturelle est < 10 mm).",
        "summary_fr_detailed": "En comparant par IRM panoramique des deux cuisses des sujets opérés d'un LCA par DIDT à un groupe témoin sain (chez qui l'asymétrie droite/gauche de longueur du semi-tendineux est toujours < 10 mm), les auteurs démontrent que toute rétraction > 10 mm est directement imputable au prélèvement chirurgical. Malgré la fréquente régénération d'un néo-tendon fibreux distal s'insérant plus haut sur le fascia poplité, le ventre musculaire du semi-tendineux reste raccourci de 8,1 cm (25 %), ce qui réduit son bras de levier en flexion profonde du genou chez les sportifs de combat ou de gymnastique.",
        "protocol_fr": "Prise en compte du raccourcissement du semi-tendineux (-25 %) dans le choix du greffon chez les athlètes nécessitant une force maximale en flexion profonde du genou (> 90°) ou en sprint.",
        "key_points_fr": [
            "Asymétrie physiologique naturelle du semi-tendineux entre les deux jambes toujours inférieure à 10 mm.",
            "Raccourcissement musculaire moyen de 81 mm (-25 %) du semi-tendineux persistant à près de 7 ans post-LCA.",
            "Explique biomécaniquement le déficit résiduel de flexion active profonde après prélèvement ST/Gracilis."
        ],
        "tags": ["Prélèvement DIDT", "Semi-tendineux", "Rétraction musculaire", "IRM", "KSSTA 2022"]
    }
}


def is_real_pdf(pdf_path: Path) -> bool:
    """Return True only if pdf_path exists and is a genuine publisher/author PDF."""
    if not pdf_path.exists():
        return False
    try:
        b = pdf_path.read_bytes()
        return len(b) > 40_000 and b.startswith(b"%PDF") and b"ReportLab PDF Library" not in b[:4096]
    except Exception:
        return False


def try_download_real_pdf(pmid: str, doi: str, pmcid: str, pdf_path: Path) -> bool:
    """
    Attempt to download the genuine publisher or open-access repository PDF (Europe PMC, PMC,
    Springer, Unpaywall, OpenAlex). Never generates a synthetic PDF.
    """
    if is_real_pdf(pdf_path):
        return True
    if pdf_path.exists():
        pdf_path.unlink()

    candidates = []
    if pmcid:
        candidates.append(f"https://europepmc.org/backend/ptpmcrender.fcgi?accid={pmcid}&blobtype=pdf")
        candidates.append(f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/pdf/")

    if doi:
        if doi.startswith("10.1007/") or doi.startswith("10.1186/") or doi.startswith("10.1245/"):
            candidates.append(f"https://link.springer.com/content/pdf/{doi}.pdf")

        # Query Unpaywall
        try:
            uw_url = f"https://api.unpaywall.org/v2/{doi}?email=nicolas.lefevre@cliniquedusport.fr"
            req = urllib.request.Request(uw_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as uwr:
                uwd = json.loads(uwr.read().decode())
                best = uwd.get("best_oa_location") or {}
                if best.get("url_for_pdf"):
                    candidates.append(best["url_for_pdf"])
                for loc in uwd.get("oa_locations", []):
                    u = loc.get("url_for_pdf")
                    if u and u not in candidates:
                        candidates.append(u)
        except Exception:
            pass

        # Query OpenAlex
        try:
            oa_url = f"https://api.openalex.org/works/https://doi.org/{doi}"
            req = urllib.request.Request(oa_url, headers={"User-Agent": "BiblioIschio/1.0"})
            with urllib.request.urlopen(req, timeout=8) as oar:
                oad = json.loads(oar.read().decode())
                for loc in oad.get("locations", []):
                    u = loc.get("pdf_url")
                    if u and u not in candidates:
                        candidates.append(u)
        except Exception:
            pass

    tmp_path = Path(f"/tmp/biblio_ischio_dl_{pmid}.pdf")
    for c in candidates:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
            subprocess.run(
                [
                    "curl",
                    "-sL",
                    "-A",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "--max-time",
                    "15",
                    c,
                    "-o",
                    str(tmp_path),
                ],
                check=False,
            )
            if is_real_pdf(tmp_path):
                pdf_path.write_bytes(tmp_path.read_bytes())
                tmp_path.unlink()
                print(f"[PDF] Downloaded real PDF for PMID {pmid} ({pdf_path.stat().st_size // 1024} KB)")
                return True
        except Exception:
            pass
    if tmp_path.exists():
        tmp_path.unlink()
    return False


MONTHS_FR = {
    1: "Janv.",
    2: "Févr.",
    3: "Mars",
    4: "Avr.",
    5: "Mai",
    6: "Juin",
    7: "Juil.",
    8: "Août",
    9: "Sept.",
    10: "Oct.",
    11: "Nov.",
    12: "Déc.",
}

JOURNAL_IMPACT_FACTORS = {
    "british journal of sports medicine": (11.8, "Br J Sports Med"),
    "journal of sport and health science": (9.7, "J Sport Health Sci"),
    "sports medicine": (9.3, "Sports Med"),
    "american journal of sports medicine": (4.2, "Am J Sports Med"),
    "the american journal of sports medicine": (4.2, "Am J Sports Med"),
    "arthroscopy : the journal of arthroscopic": (4.4, "Arthroscopy"),
    "arthroscopy": (4.4, "Arthroscopy"),
    "scandinavian journal of medicine & science in sports": (4.1, "Scand J Med Sci Sports"),
    "medicine and science in sports and exercise": (4.1, "Med Sci Sports Exerc"),
    "knee surgery, sports traumatology, arthroscopy": (3.3, "KSSTA"),
    "orthopaedic journal of sports medicine": (2.6, "Orthop J Sports Med"),
    "skeletal radiology": (1.9, "Skeletal Radiol"),
    "arthroscopy techniques": (1.3, "Arthrosc Tech"),
}


def get_journal_info_and_if(journal_title: str) -> tuple:
    j_low = (journal_title or "").lower()
    for key in sorted(JOURNAL_IMPACT_FACTORS.keys(), key=len, reverse=True):
        if key in j_low:
            return JOURNAL_IMPACT_FACTORS[key]
    return (2.8, journal_title)


def extract_pub_month_and_date(r: dict, fallback_year_str: str) -> tuple:
    ji = r.get("journalInfo", {})
    y_num = 0
    m_num = 0

    fpd = r.get("firstPublicationDate") or r.get("electronicPublicationDate") or ""
    parts = str(fpd).split("-")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
        y_cand = int(parts[0])
        m_cand = int(parts[1])
        if 1990 <= y_cand <= 2030 and 1 <= m_cand <= 12:
            y_num = y_cand
            m_num = m_cand

    if not (1 <= m_num <= 12):
        try:
            m_cand = int(ji.get("monthOfPublication") or 0)
            if 1 <= m_cand <= 12:
                m_num = m_cand
        except (TypeError, ValueError):
            pass

    if not y_num:
        try:
            y_num = int(ji.get("yearOfPublication") or fallback_year_str or 2025)
        except (TypeError, ValueError):
            y_num = 2025

    month_fr = MONTHS_FR.get(m_num, "")
    pub_date_fr = f"{month_fr} {y_num}".strip() if month_fr else str(y_num)
    return y_num, (m_num if m_num else 1), month_fr, pub_date_fr


def update_embedded_js(articles: list, categories: list):
    js_content = (
        f"window.BIBLIO_ARTICLES = {json.dumps(articles, ensure_ascii=False)};\n"
        f"window.BIBLIO_CATEGORIES = {json.dumps(categories, ensure_ascii=False)};\n"
    )
    (DATA_DIR / "embedded_data.js").write_text(js_content, encoding="utf-8")
    print(f"[Embedded JS] Updated data/embedded_data.js ({len(articles)} articles)")


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    PDFS_DIR.mkdir(parents=True, exist_ok=True)

    pmids = list(CURATED_DATA.keys())
    by_pmid = {}

    existing_json_path = DATA_DIR / "articles.json"
    if existing_json_path.exists():
        try:
            for ea in json.loads(existing_json_path.read_text(encoding="utf-8")):
                ep = str(ea.get("pmid", ""))
                if ep:
                    by_pmid[ep] = {
                        "pmid": ep,
                        "title": ea.get("title", ""),
                        "pubYear": str(ea.get("year", 2026)),
                        "firstPublicationDate": f"{ea.get('year', 2026)}-{int(ea.get('month_num', 1)):02d}-01",
                        "journalInfo": {
                            "volume": ea.get("volume", ""),
                            "issue": ea.get("issue", ""),
                            "yearOfPublication": ea.get("year", 2026),
                            "monthOfPublication": ea.get("month_num", 1),
                            "journal": {"title": ea.get("journal", "")},
                        },
                        "pageInfo": ea.get("pages", ""),
                        "doi": ea.get("doi", ""),
                        "pmcid": ea.get("pmcid", ""),
                        "abstractText": ea.get("abstract_en", ""),
                        "authorList": {"author": [{"fullName": nm} for nm in ea.get("authors_list", [])]},
                    }
        except Exception:
            pass

    try:
        query = " OR ".join([f"EXT_ID:{p}" for p in pmids])
        url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + urllib.parse.urlencode({
            "query": query,
            "format": "json",
            "pageSize": 100,
            "resultType": "core",
        })
        req = urllib.request.Request(url, headers={"User-Agent": "BiblioIschio/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw_results = json.loads(resp.read().decode("utf-8"))["resultList"]["result"]
        for r in raw_results:
            if r.get("pmid"):
                by_pmid[str(r.get("pmid"))] = r
    except Exception as e:
        print(f"[Metadata] Europe PMC warning: {e}")

    articles = []
    for pmid, cdata in CURATED_DATA.items():
        r = by_pmid.get(pmid, {})
        title = r.get("title", "").rstrip(".")
        journal_info = r.get("journalInfo", {})
        journal = journal_info.get("journal", {}).get("title", "")
        raw_year = str(r.get("pubYear", "2025"))
        year_int, month_num, month_fr, pub_date_fr = extract_pub_month_and_date(r, raw_year)
        impact_factor, journal_short = get_journal_info_and_if(journal)

        volume = str(journal_info.get("volume", ""))
        issue = str(journal_info.get("issue", ""))
        pages = str(r.get("pageInfo", ""))
        doi = str(r.get("doi", ""))
        pmcid = str(r.get("pmcid") or "")
        abstract_raw = r.get("abstractText", "Abstract non disponible.")
        abstract_clean = re.sub(r"<[^>]+>", " ", abstract_raw)
        abstract_clean = re.sub(r"\s+", " ", abstract_clean).strip()

        authors_list = []
        for a in r.get("authorList", {}).get("author", []):
            full = a.get("fullName") or f"{a.get('lastName', '')} {a.get('initials', '')}".strip()
            if full:
                authors_list.append(full)
        if not authors_list and r.get("authorString"):
            authors_list = [x.strip() for x in r["authorString"].rstrip(".").split(",") if x.strip()]

        if len(authors_list) > 3:
            authors_short = f"{authors_list[0]}, {authors_list[1]} et al."
        else:
            authors_short = ", ".join(authors_list)

        cat = CATEGORIES[cdata["category_id"]]
        rel_pdf = f"pdfs/PMID_{pmid}.pdf"
        pdf_path = BASE_DIR / rel_pdf

        has_real_pdf = is_real_pdf(pdf_path) or try_download_real_pdf(pmid, doi, pmcid, pdf_path)

        pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
        doi_url = f"https://doi.org/{doi}" if doi else pubmed_url
        pmc_url = f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else ""
        article_url = pmc_url or doi_url or pubmed_url

        art_obj = {
            "id": f"pmid-{pmid}",
            "pmid": pmid,
            "pmcid": pmcid,
            "doi": doi,
            "title": title,
            "title_fr": cdata["title_fr"],
            "authors_list": authors_list,
            "authors_short": authors_short,
            "journal": journal,
            "journal_short": journal_short,
            "impact_factor": impact_factor,
            "year": year_int,
            "month_num": month_num,
            "month_fr": month_fr,
            "pub_date_fr": pub_date_fr,
            "volume": volume,
            "issue": issue,
            "pages": pages,
            "category_id": cdata["category_id"],
            "category_label": cat["label"],
            "category_short": cat["short_label"],
            "category_color": cat["color"],
            "modality": cdata["modality"],
            "intervention_type": cdata["intervention_type"],
            "cochin_link": cdata["cochin_link"],
            "summary_fr_short": cdata["summary_fr_short"],
            "summary_fr_detailed": cdata["summary_fr_detailed"],
            "protocol_fr": cdata["protocol_fr"],
            "key_points_fr": cdata["key_points_fr"],
            "abstract_en": abstract_clean,
            "tags": cdata["tags"],
            "pdf_file": rel_pdf if has_real_pdf else None,
            "pdf_source": "publisher_oa_pdf" if has_real_pdf else "external_link",
            "pdf_size_kb": round(pdf_path.stat().st_size / 1024) if has_real_pdf else None,
            "pubmed_url": pubmed_url,
            "doi_url": doi_url,
            "pmc_url": pmc_url,
            "article_url": article_url,
        }
        articles.append(art_obj)

    articles.sort(key=lambda x: (-x["year"], -x.get("month_num", 1), x["category_id"]))
    cat_list = list(CATEGORIES.values())

    (DATA_DIR / "articles.json").write_text(
        json.dumps(articles, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (DATA_DIR / "categories.json").write_text(
        json.dumps(cat_list, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    update_embedded_js(articles, cat_list)

    real_pdf_count = sum(1 for a in articles if a.get("pdf_file"))
    print(f"[Database] Saved {len(articles)} articles ({real_pdf_count} with real PDFs, {len(articles) - real_pdf_count} with external links) to {DATA_DIR / 'articles.json'}")

    from zotero_sync import generate_static_exports
    generate_static_exports(articles)


if __name__ == "__main__":
    main()
