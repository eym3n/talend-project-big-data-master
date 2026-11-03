# DWH Dimensional Mart Orchestrator (jChargeDWH)

## Purpose and Scope

The `jChargeDWH` job (version `0.1`, item path `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/Orechestration/jChargeDWH_0.1.item`) orchestrates the dimensional modeling pipeline that extracts data from the normalized ODS schema (`VENTE_ODS`) and populates the dimensional star schema in `VENTE_DWH`.

```mermaid
flowchart TD
    PRE["tPrejob_1"] --> START_TIME["tChronometerStart_1"]
    START_TIME --> CONN_ODS["tDBConnection_1 (VENTE_ODS)"]
    CONN_ODS --> CONN_DWH["tDBConnection_2 (VENTE_DWH)"]
    CONN_DWH --> LOG_START["tJava_1<br/>Log Start Banner"]

    subgraph Pipeline["Dimensional Pipeline Sequence"]
        JOB_PROD["jDwhProduit (tRunJob_3)<br/>Update DIM_PRODUIT (SCD Type 2)"]
        JOB_CLI["jDwhClient (tRunJob_1)<br/>Update DIM_CLIENT (SCD Type 2)"]
        JOB_VTE["jDwhVente (tRunJob_6)<br/>Aggregate and Insert FAIT_VENTE"]

        JOB_PROD -->|"OnSubjobOk"| JOB_CLI
        JOB_CLI -->|"OnSubjobOk"| JOB_VTE
    end

    LOG_START --> JOB_PROD

    subgraph Postjob["Postjob Teardown"]
        POST["tPostjob_1"] --> CLOSE_ODS["tDBClose_1"]
        CLOSE_ODS --> CLOSE_DWH["tDBClose_2"]
        CLOSE_DWH --> STOP_TIME["tChronometerStop_1"]
        STOP_TIME --> LOG_END["tJava_2<br/>Log Total Runtime"]
    end
```

---

## Sequencing Rationale

The data warehouse star schema requires all dimensions to be fully populated and up-to-date before fact records can be evaluated and joined:

1. **`jDwhProduit` (Step 1):** Denormalizes product, sub-category, and category hierarchies from `ODS_PRODUIT`, `ODS_SOUS_CATEGORIE`, and `ODS_CATEGORIE`. Manages SCD-2 historical tracking in `DIM_PRODUIT`.
2. **`jDwhClient` (Step 2):** Joins `ODS_CLIENT` and `ODS_TYPE_CLIENT` to maintain SCD-2 customer records in `DIM_CLIENT`.
3. **`jDwhVente` (Step 3):** Extracts un-promoted sales records from `ODS_VENTE`, performs inner joins against `DIM_PRODUIT`, `DIM_CLIENT`, and `DIM_CALENDRIER` (previously initialized), aggregates metrics by dimension keys, and populates `FAIT_VENTE`.

If either dimension loader fails, `jDwhVente` will not execute, preventing orphaned foreign keys or inconsistent surrogate key assignments in the fact table.

---

## Connection Management

- Opens shared connections for both `VENTE_ODS` (source extraction) and `VENTE_DWH` (target upserts).
- Explicit non-auto-commit mode ensures transactional boundaries remain isolated to the individual child subjobs.
- Child jobs pass database credentials and context transparently (`TRANSMIT_WHOLE_CONTEXT=true`).

---

## Evidence Grounding

- Job design: `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/Orechestration/jChargeDWH_0.1.item`
- Target schema scripts: `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/scriptSQL_partie_2/2-script_create_table_dwh.sql`
