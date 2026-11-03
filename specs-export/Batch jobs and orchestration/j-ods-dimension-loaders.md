# ODS Entity Loaders (Categories, Sub-Categories, Products, Customer Types, Customers)

## Purpose and Scope

The ODS dimension loader jobs ingest reference entities from CSV files into the `VENTE_ODS` schema. Each job implements an identical robust architectural pattern:
- File detection via `tFileList` and global variable masking.
- Line numbering via `tMap_1` and sequence generators.
- Null validation via `tFilterRow_1`.
- Business key deduplication via `tUniqRow_1`.
- Reject logging into `ODS_REJET` for both null fields and duplicates.
- SCD Type 2 active versioning and history tracking in the ODS destination table.

```mermaid
flowchart TD
    FILE["tFileInputDelimited<br/>Read CSV Feed"] --> MAP_SEQ["tMap_1<br/>Add NUM_LIGNE (Numeric.sequence)"]
    MAP_SEQ --> FILTER["tFilterRow_1<br/>Validate Mandatory Fields != null/empty"]

    FILTER -->|"Reject - Null Value"| REJ_MAP1["tMap_3<br/>Format Null Value Reject"]
    REJ_MAP1 --> REJ_DB1["tDBOutput (ODS_REJET)<br/>Valeurs nulles pour certain colonnes"]

    FILTER -->|"Filter - Valid"| UNIQ["tUniqRow_1<br/>Check Duplicate Business Keys"]
    UNIQ -->|"Reject - Duplicate"| REJ_MAP2["tMap_4<br/>Format Duplicate Reject"]
    REJ_MAP2 --> REJ_DB2["tDBOutput (ODS_REJET)<br/>Donnees en double"]

    UNIQ -->|"Unique - Clean"| MAP_SCD["tMap_2<br/>Lookup Existing ODS Record"]

    MAP_SCD -->|"Match Found and Changed"| UPD_OLD["tDBOutput_3 (Update)<br/>Set BL_LIGNE_ACTIVE = 0"]
    MAP_SCD -->|"Match Found and Changed"| INS_NEW["tDBOutput_2 (Insert)<br/>Insert with BL_LIGNE_ACTIVE = 1"]
    MAP_SCD -->|"New Record No Match"| INS_FIRST["tDBOutput_1 (Insert)<br/>Insert with BL_LIGNE_ACTIVE = 1"]
```

---

## Job Specifications Summary

| Job Name | Source File Pattern | Business Key | Target Table | Null Validation Condition |
| :--- | :--- | :--- | :--- | :--- |
| `jOdsCategorie` | `ICOM_*_CATEGORY.csv` | `CD_CATEGORIE` | `ODS_CATEGORIE` | `!input_row.CD_CATEGORIE.isEmpty() && !input_row.LB_CATEGORIE.isEmpty()` |
| `jOdsSousCategorie` | `ICOM_*_SOUS_CATEGORIE.csv` | `CD_SOUS_CATEGORIE` | `ODS_SOUS_CATEGORIE` | `!input_row.CD_SOUS_CATEGORIE.isEmpty() && !input_row.LB_SOUS_CATEGORIE.isEmpty() && !input_row.CD_CATEGORIE.isEmpty()` |
| `jOdsProduit` | `ICOM_*_PRODUIT.csv` | `CD_PRODUIT` | `ODS_PRODUIT` | Keys not empty, purchase & sales prices parseable |
| `jOdsTypeClient` | `ICOM_*_TYPE_CLIENT.csv` | `CD_TYPE_CLIENT` | `ODS_TYPE_CLIENT` | `!input_row.CD_TYPE_CLIENT.isEmpty() && !input_row.LB_TYPE_CLIENT.isEmpty()` |
| `jOdsClient` | `ICOM_*_CUSTOMER.csv` | `ID_CLIENT` | `ODS_CLIENT` | ID, name, surname, city, country, region, and client type not empty |

---

## SCD Type 2 Implementation in ODS

In `tMap_2`, the incoming unique flow is joined against the existing ODS table (`tDBInput_1` with lookup query `SELECT * FROM "VENTE_ODS"."..."`).

1. **New Insert Flow (`insert...`):**
   - Condition: `lookup.BUSINESS_KEY == null`
   - Sets `DT_INSERTION = TalendDate.getCurrentDate()`, `BL_LIGNE_ACTIVE = 1`, `LB_JOB_NAME = jobName`, `LB_NOM_FICHIER = currentFile`.
2. **Historical Invalidation Flow (`UpdateBICurrent`):**
   - Condition: `lookup.BUSINESS_KEY != null && (!incoming.ATTR.equals(lookup.ATTR) || ...)`
   - Action: `UPDATE` target table matching on business key; sets `BL_LIGNE_ACTIVE = 0`.
3. **Current Version Insertion Flow (`insertNewCurrent`):**
   - Condition: Same change condition as above.
   - Action: `INSERT` new record with updated attributes, `DT_INSERTION = now()`, `BL_LIGNE_ACTIVE = 1`.

---

## Evidence Grounding

- Job items in repository:
  - `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/ODS/jOdsCategorie_0.1.item`
  - `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/ODS/jOdsSousCategorie_0.1.item`
  - `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/ODS/jOdsProduit_0.1.item`
  - `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/ODS/jOdsTypeClient_0.1.item`
  - `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/ODS/jOdsClient_0.1.item`
