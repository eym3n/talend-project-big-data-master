# ODS Batch Ingestion Orchestrator (jChargeODS)

## Purpose and Scope

The `jChargeODS` job (version `0.1`, item path `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/Orechestration/jChargeODS_0.1.item`) controls the extraction of raw daily CSV feeds and feeds them into the Operational Data Store. It enforces strict relational dependency sequencing across dimensions and transactional facts, verifying file presence before loading any tables.

```mermaid
flowchart TD
    PRE["tPrejob_1"] --> CHRONO_START["tChronometerStart_1"]
    CHRONO_START --> DIR_CHECK["tFileList_1<br/>Check Directory:<br/>context.projectFolder + YYYYMMDD"]
    DIR_CHECK -->|"Missing or Error"| DIE["tDie_1 (Exit Code 4)<br/>le repertoire du jour nexiste pas"]
    DIR_CHECK -->|"Directory Found"| DB_CONN["tDBConnection_1<br/>Connect VENTE_ODS"]
    DB_CONN --> LOG_START["tJava_1<br/>Log Start Banner"]

    subgraph DependencyChain["Sequential Loading Pipeline (OnSubjobOk)"]
        R1["jOdsCategorie (tRunJob_1)"] -->|"OnSubjobOk"| R2["jOdsSousCategorie (tRunJob_2)"]
        R2 -->|"OnSubjobOk"| R3["jOdsProduit (tRunJob_3)"]
        R3 -->|"OnSubjobOk"| R4["jOdsTypeClient (tRunJob_4)"]
        R4 -->|"OnSubjobOk"| R5["jOdsClient (tRunJob_5)"]
        R5 -->|"OnSubjobOk"| R6["jOdsVente (tRunJob_6)"]
    end

    LOG_START --> R1

    subgraph Cleanup["Postjob Cleanup"]
        POST["tPostjob_1"] --> DB_CLOSE["tDBClose_1"]
        DB_CLOSE --> CHRONO_STOP["tChronometerStop_1"]
        CHRONO_STOP --> LOG_END["tJava_2<br/>Log Duration Summary"]
    end
```

---

## Daily Directory Ingress Gate

Before any database operations occur, `tFileList_1` scans `context.projectFolder` looking for a directory matching `TalendDate.getDate("YYYYMMDD")`.

- **Listing Mode:** `DIRECTORIES`, `CASE_SENSITIVE=YES`, `ERROR=true`.
- **Failure Reaction:** If the directory is absent or empty, the `OnComponentError` trigger fires `tDie_1`.
- **Termination Parameters:** Message `"le repertoire du jour n'existe pas"`, Exit Code `4`, Priority `5`, `EXIT_JVM=true`.
- **Operational Impact:** This gate guarantees that jobs will never run against missing daily data or overwrite ODS tables with empty inputs.

---

## Dependency Sequence Rationale

The subjob execution order reflects strict entity relationship constraints:

1. **`jOdsCategorie`:** Loads parent product categories (`CD_CATEGORIE`).
2. **`jOdsSousCategorie`:** Loads sub-categories which depend on valid parent category references (`CD_CATEGORIE`).
3. **`jOdsProduit`:** Loads products which depend on valid sub-category references (`CD_SOUS_CATEGORIE`).
4. **`jOdsTypeClient`:** Loads customer classification tiers (`CD_TYPE_CLIENT`).
5. **`jOdsClient`:** Loads individual customer profiles which depend on valid customer type classifications (`CD_TYPE_CLIENT`).
6. **`jOdsVente`:** Ingests granular sales transactions referencing both products (`CD_PRODUIT`) and customers (`ID_CLIENT`).

Every `tRunJob` child invocation sets `DIE_ON_CHILD_ERROR=true` and `TRANSMIT_WHOLE_CONTEXT=true`.

---

## Evidence Grounding

- Item definition: `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/Orechestration/jChargeODS_0.1.item`
- Context parameters: `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/context/ConnectionODS_0.1.item`
