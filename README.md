<img src="assets/icon.svg" width="64" height="64" alt="BiblioIschio">

# BiblioIschio — Veille Bibliographique & Synthèses Cliniques sur les Ischio-Jambiers (Chirurgie, IRM & Sport)

Portail de veille bibliographique, de résumés cliniques structurés en français (avec abstracts originaux PubMed), de stockage de PDF intégraux Open-Access et de synchronisation automatique vers **Zotero**, calqué sur le design et l'architecture de **[`Mrthomaslef/biblioosteo`](https://github.com/Mrthomaslef/biblioosteo)** et dédié à la pathologie des **ischio-jambiers** (Cohorte **PHAS** — *Parisian Hamstring Avulsion Score*, Clinique du Sport Paris, et littérature internationale de référence 2017–2026).

---

## 🎯 7 Thématiques couvertes (32 articles de référence indexés)

1. **⚡ Ruptures Proximales Aiguës & Cohorte PHAS (`proximal_acute`)**
   - Analyse des complications sur **757 patients** de la cohorte PHAS (*OJSM 2026*, Dr N. Lefèvre et al.).
   - Résultats fonctionnels à **très long terme (≥ 8 ans, moyenne > 10 ans)** après réinsertion proximale (*OJSM 2026*).
   - Délai chirurgical optimal : **seuil critique des 32 jours** pour diviser par 2,5 le risque de re-rupture (*AJSM 2024*) et méta-analyse internationale 2026 sur 1 720 patients (*AJSM 2026*).
   - Étude comparative appariée **Chirurgie vs Traitement Conservateur** (*AJSM 2024*) et résultats avant/après 50 ans (*KSSTA 2025*).
   - Facteurs prédictifs du retour précoce au sport chez **64 athlètes professionnels** (*AJSM 2024*).
2. **🔩 Ruptures Chroniques, Révisions & Reconstructions par Allogreffe (`chronic_revision_allograft`)**
   - Reconstruction par **allogreffe structurelle** des avulsions chroniques rétractées (*Arthroscopy 2026*, Dr N. Lefèvre et al.) et technique par allogreffe de tendon quadricipital (*Arthrosc Tech 2025*).
   - Étude cas-témoins appariée des **reprises chirurgicales (révisions) vs réparations primaires** (*AJSM 2025*).
   - Réinsertion anatomique des avulsions proximales isolées du **semi-membraneux** chez le sportif (*Arthrosc Tech 2025*).
3. **🧲 Imagerie IRM, Signe du Cobra, Tendon Intramusculaire & Classification BAMIC (`imaging_bamic_mri`)**
   - **Le « Signe du Cobra » en IRM** (*KSSTA 2025*, Dr N. Lefèvre et al.) : marqueur de surestimation de 21 % (2 cm) de la rétraction du semi-membraneux.
   - **IRM de première intention vs Échographie** sur 392 patients (*KSSTA 2024*) : gain de 10 jours sur le délai opératoire et meilleurs scores Tegner/UCLA.
   - Suivi IRM 3T de la cicatrisation post-opératoire chez le footballeur professionnel (*Skeletal Radiology 2026*) et sémiologie IRM des lésions sportives (*Skeletal Radiology 2026*).
   - **Classification BAMIC** (*British Athletics Muscle Injury Classification*), atteinte du tendon central/intramusculaire (classe *c*) et **Consensus International de Londres — Partie 1** (*BJSM 2023*).
4. **🎯 Tendinopathie Proximale (PHT), Endoscopie & Nerf Sciatique (`pht_endoscopy_sciatic`)**
   - **Ténotomie partielle et réinsertion sur ancres** pour tendinopathie proximale chronique réfractaire (*AJSM 2026*, Dr N. Lefèvre et al.).
   - Résultats à long terme (> 6 ans) de la **réparation endoscopique** des ruptures proximales (*Arthroscopy 2026*).
   - Impact pronostique de l'**œdème péri-sciatique circonférentiel en IRM** sur le délai de retour au jeu (*BJSM 2026*).
   - **Consensus International de Londres — Partie 2** : indications chirurgicales formelles (*BJSM 2023*).
5. **🦵 Ruptures Distales & Jonction en T du Biceps Fémoral (`distal_tears_t_junction`)**
   - Réparation chirurgicale par ancres des **avulsions distales du biceps fémoral** chez l'athlète professionnel (*OJSM 2021*, 100 % de RTS à 16,7 semaines).
   - Réparation chirurgicale des lésions aiguës de la **jonction musculo-tendineuse distale en T (T-junction)** du biceps fémoral (*AJSM 2020*, 0 % de récidive vs 54 % sans chirurgie, *OJSM 2017*).
6. **🏃 Scores PHAS / Hip-RSI, Rééducation Excentrique & Retour au Sport (`scores_rehab_prevention`)**
   - Validation du **PHAS** (*AJSM 2024*), du **Short-PHAS en 12 items** sur 335 patients (*OJSM 2026*) et du score psychologique **Hip-RSI** (*OJSM 2025*).
   - Essai contrôlé randomisé **PHARRLAP** (*AJSM 2026*) : rééducation accélérée sans attelle et appui immédiat vs protocole conservateur.
   - Preuve in vivo de l'addition de **sarcomères en série (+49 %)** après 9 semaines de **Nordic Hamstring Exercise** (*J Sport Health Sci 2025*) et **Consensus de Londres — Partie 3** (*BJSM 2023*).
7. **🧬 Ischio-Jambiers & Plastie du LCA (`acl_graft_harvest`)**
   - Essai randomisé sur la **préservation de l'insertion tibiale distale** des ischio-jambiers lors de la plastie du LCA (*AJSM 2026*).
   - Rétraction anatomique du muscle semi-tendineux (-25 % / 81 mm) en IRM bilatérale après prélèvement DIDT (*KSSTA 2022*).

---

## 🛠️ Commandes utiles (Ajout d'articles & Mise à jour)

```bash
# Régénérer toute la base, les PDFs et les exports Zotero
python3 scripts/build_biblio_database.py

# Ajouter un nouvel article PubMed par son PMID ou par requête
python3 scripts/add_article.py 41918719
python3 scripts/add_article.py "proximal hamstring avulsion repair"

# Synchroniser avec votre compte Zotero
ZOTERO_API_KEY="votre_cle" python3 scripts/zotero_sync.py
```
