----------------------------------------------------------------------------
------------ Script de sélection des données insérées dans l'ODS -----------
----------------------------------------------------------------------------
-- Définir le schéma à utiliser
SET SEARCH_PATH = "VENTE_ODS";


-- Liste des types client
TRUNCATE "ODS_TYPE_CLIENT";
SELECT * FROM "ODS_TYPE_CLIENT";

-- Liste des catégories
TRUNCATE "ODS_CATEGORIE";
SELECT * FROM "ODS_CATEGORIE";

-- Liste des sous-catégories
TRUNCATE "ODS_SOUS_CATEGORIE";
SELECT * FROM "ODS_SOUS_CATEGORIE";

-- Liste des produits
TRUNCATE "ODS_PRODUIT";
SELECT * FROM "ODS_PRODUIT";

-- Liste des clients
TRUNCATE "ODS_CLIENT";
SELECT * FROM "ODS_CLIENT";

-- Liste des ventes
TRUNCATE "ODS_VENTE";
SELECT * FROM "ODS_VENTE";

-- Liste des rejets
SELECT * FROM "ODS_REJET";