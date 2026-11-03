# Master Pipeline Orchestrator (jAlimentationBDD)

## Purpose and Scope

The `jAlimentationBDD` job (version `0.1`, item path `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/Orechestration/jAlimentationBDD_0.1.item`) serves as the master execution harness for the complete warehouse alimentation cycle. It provides unified transaction scoping, execution timing, shared connection lifecycle management, and strict sequential ordering between raw staging (ODS) and analytical warehousing (DWH).

```mermaid
sequenceDiagram
    autonumber
    actor Scheduler as External Scheduler / Operator
    participant Master as jAlimentationBDD
    participant DB_ODS as PostgreSQL (VENTE_ODS)
    participant DB_DWH as PostgreSQL (VENTE_DWH)
    participant ODS as jChargeODS (Child 1)
    participant DWH as jChargeDWH (Child 2)

    Scheduler->>Master: Trigger Job Execution
    Note over Master: tPrejob Stage
    Master->>Master: tChronometerStart_1 (Record Start Timestamp)
    Master->>DB_ODS: tPostgresqlConnection (Shared Connection: "VENTE ODS")
    Master->>DB_DWH: tPostgresqlConnection (Shared Connection: "VENTE DWH")
    Master->>Master: tJava_1 (Log Startup Banner)

    Note over Master: Main Execution Pipeline
    Master->>ODS: tRunJob_1 (Execute ODS Pipeline, DieOnError=true)
    ODS-->>Master: OnSubjobOk (ODS Staging Successful)
    Master->>DWH: tRunJob_2 (Execute DWH Pipeline, DieOnError=true)
    DWH-->>Master: OnSubjobOk (DWH Mart Successful)

    Note over Master: tPostjob Stage
    Master->>DB_ODS: tPostgresqlClose (Close ODS Connection)
    Master->>DB_DWH: tPostgresqlClose (Close DWH Connection)
    Master->>Master: tChronometerStop_1 (Capture Elapsed Time)
    Master->>Master: tJava_2 (Log Completion Summary & Formatted Duration)
```

---

## Component Topology

| Component ID | Talend Component Type | Purpose & Configuration |
| :--- | :--- | :--- |
| `tPrejob_1` | `tPrejob` | Triggers pre-execution initialization hook |
| `tChronometerStart_1` | `tChronometerStart` | Captures job start epoch in `globalMap` under key `tChronometerStart_1_STARTTIME` |
| `tDBConnection_1` | `tPostgresqlConnection` | Opens shared connection `"VENTE ODS"`, `AUTO_COMMIT=false`, repository `_MQSMkD-pEfCJkrHegI1I0A` |
| `tDBConnection_2` | `tPostgresqlConnection` | Opens shared connection `"VENTE DWH"`, `AUTO_COMMIT=false`, repository `_FKqAwEHlEfCRobsmOeibog` |
| `tJava_1` | `tJava` | Emits job launch banner and human-readable start timestamp |
| `tRunJob_1` | `tRunJob` | Synchronously executes `jChargeODS`. `DIE_ON_CHILD_ERROR=true`, `TRANSMIT_WHOLE_CONTEXT=true` |
| `tRunJob_2` | `tRunJob` | Synchronously executes `jChargeDWH`. `DIE_ON_CHILD_ERROR=true`, `TRANSMIT_WHOLE_CONTEXT=true` |
| `tPostjob_1` | `tPostjob` | Triggers post-execution cleanup hook regardless of standard flow termination |
| `tDBClose_1` | `tPostgresqlClose` | Explicitly terminates connection `"VENTE ODS"` |
| `tDBClose_2` | `tPostgresqlClose` | Explicitly terminates connection `"VENTE DWH"` |
| `tChronometerStop_1` | `tChronometerStop` | Computes duration since beginning (`globalMap.get("tChronometerStop_1_DURATION")`) |
| `tJava_2` | `tJava` | Emits finish timestamp and formatted runtime using `customCode.getFormattedTime(...)` |

---

## Control Flow and Error Handling

1. **Failure Propagation:**
   - Both child jobs configure `DIE_ON_CHILD_ERROR = true`. If any component in `jChargeODS` fails (e.g. missing daily directory or schema violation), `jAlimentationBDD` terminates immediately with a non-zero exit code, preventing `jChargeDWH` from running on partial or corrupted staging data.
2. **Postjob Guarantees:**
   - The `tPostjob` sequence executes even on JVM shutdown signals or child errors, ensuring that database connection sockets are closed and resources freed.
3. **Implicit Context Loading:**
   - Inherits implicit database context loader reading table `PARAMS_LOG.CONTEXTE`. Values fetched override design-time defaults for `ServerName`, `database`, `port`, `utilisateur`, and `password`.

---

## Evidence Grounding

- Source definition: `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/process/Orechestration/jAlimentationBDD_0.1.item`
- Context parameters: `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/ALIMENTATION_DATA_WAREHOUSE/context/projectvariable_0.1.item`
- Formatting routine: `workspace://codebase/7c8eded6-9911-48de-929c-053e124fc8b5/file/customCode.java`
