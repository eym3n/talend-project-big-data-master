# Data Warehouse Alimentation Project

This project implements a complete data warehouse solution using Talend Open Studio for Data Integration and PostgreSQL. The system processes CSV files containing sales data (clients, products, categories, etc.) through an ETL pipeline that loads data into an Operational Data Store (ODS) and then transforms it into a dimensional data warehouse.

## Project Structure

```
TalendProjectBigData/
├── codeForOds.java                     # Java code snippets for tJava components
├── customCode.java                     # Custom utility routines
├── jGenerateCalendar.zip               # Calendar generation job
├── joursFeries.xlsx                    # Holiday reference data
├── README.md                           # This file
├── ALIMENTATION_DATA_WAREHOUSE/        # Main Talend project
│   ├── .project                        # Eclipse project configuration
│   ├── talend.project                  # Talend project definition
│   ├── code/                           # Custom routines and system utilities
│   ├── metadata/                       # Database connections and schemas
│   ├── poms/                           # Maven POMs and generated Java code
│   └── process/                        # ETL job definitions
├── csvFiles/                           # Source CSV data files
│   ├── ICOM_20250605_CATEGORY.csv
│   ├── ICOM_20250605_CUSTOMER.csv
│   ├── ICOM_20250605_PRODUIT.csv
│   ├── ICOM_20250605_SOUS_CATEGORIE.csv
│   └── ICOM_20250605_TYPE_CLIENT.csv
├── scriptSQL_partie_1/                 # Database schema scripts
└── scriptSQL_partie_2/                 # Additional SQL scripts
```

## Architecture

The project follows a typical data warehouse architecture with three main layers:

### 1. **Source Layer**

- CSV files containing business data with pattern: `ICOM_YYYYMMDD_[ENTITY].csv`
- Located in [`csvFiles/`](csvFiles/) directory
- Entities include: categories, customers, products, sub-categories, customer types, and sales data

### 2. **ODS Layer (Operational Data Store)**

- Staging area for raw data processing using [`tFileList`](ALIMENTATION_DATA_WAREHOUSE/poms/jobs/process/ODS/jodscategorie_0.1/src/main/java/alimentation_data_warehouse/jodscategorie_0_1/jOdsCategorie.java) components
- Data validation and cleansing
- Duplicate detection and removal
- Comprehensive logging with [`routines.system.ResumeUtil`](ALIMENTATION_DATA_WAREHOUSE/poms/code/routines/src/main/java/routines/system/ResumeUtil.java)

### 3. **DWH Layer (Data Warehouse)**

- Dimensional model with facts and dimensions
- Optimized for analytical queries
- Historical data preservation

## Database Setup

### PostgreSQL Configuration

1. **Create Database:**

```sql
CREATE DATABASE vente_db;
```

2. **Database Connections:**

   - **VENTE_ODS**: Connection for ODS schema
   - **VENTE_DWH**: Connection for Data Warehouse schema
   - **PARAMS_LOG**: Connection for logging and parameters

3. **Connection Parameters:**
   - Host: localhost
   - Port: 5432
   - Database: vente_db
   - Username: [your_username]
   - Password: [your_password]

## Talend Project Structure

### Context Variables

Configure the following context variables in Talend:

- `schema_ods`: ODS schema name
- `schema_dwh`: DWH schema name
- `database`: Database name (vente_db)
- `ServerName`: Database server (localhost)
- `port`: Database port (5432)
- `utilisateur`: Database username
- `password`: Database password
- `projectFolder`: Path to CSV files directory

### Job Categories

#### 1. **ODS Jobs** (`/process/ODS/`)

These jobs extract data from CSV files and load into the ODS layer using the [`tFileList_1Process`](ALIMENTATION_DATA_WAREHOUSE/poms/jobs/process/ODS/jodscategorie_0.1/src/main/java/alimentation_data_warehouse/jodscategorie_0_1/jOdsCategorie.java) method:

- **jOdsCategorie**: Processes category data
- **jOdsClient**: Processes customer data
- **jOdsProduit**: Processes product data
- **jOdsSousCategorie**: Processes sub-category data
- **jOdsTypeClient**: Processes customer type data
- **jOdsVente**: Processes sales transaction data

#### 2. **DWH Jobs** (`/process/DWH/`)

These jobs transform ODS data into dimensional model:

- **jDwhClient**: Creates customer dimension
- **jDwhProduit**: Creates product dimension
- **jDwhVente**: Creates sales fact table
- **jGenerateCalendar**: Generates time dimension

#### 3. **Orchestration Jobs** (`/process/Orechestration/`)

Main orchestration jobs that coordinate the entire pipeline using [`jChargeODS`](ALIMENTATION_DATA_WAREHOUSE/poms/jobs/process/Orechestration/jchargeods_0.1/src/main/java/alimentation_data_warehouse/jchargeods_0_1/jChargeODS.java):

- **jChargeODS**: Orchestrates all ODS loading jobs
- **jChargeDWH**: Orchestrates all DWH transformation jobs
- **jAlimentationBDD**: Main job that runs the complete pipeline

## Installation and Setup

### 1. **Talend Setup**

1. **Import Project:**

   - Open Talend Open Studio for Data Integration
   - Import the [`ALIMENTATION_DATA_WAREHOUSE`](ALIMENTATION_DATA_WAREHOUSE/) project

2. **Configure Database Connections:**

   - Go to Metadata → Db Connections
   - Configure the three database connections in [`metadata/DbConnections/`](ALIMENTATION_DATA_WAREHOUSE/metadata/connections/)

3. **Configure Context Variables:**

   - Update context variables with your environment settings
   - Ensure `projectFolder` points to your [`csvFiles/`](csvFiles/) directory

4. **Install Custom Routines:**
   - The project includes custom code in [`customCode.java`](customCode.java)
   - Copy the [`routines.customCode`](ALIMENTATION_DATA_WAREHOUSE/poms/code/routines/src/main/java/routines/customCode.java) class to your Talend project

### 2. **File Placement**

1. **CSV Files:**

   - Place all CSV files in the [`csvFiles/`](csvFiles/) directory
   - Files should follow the naming pattern: `ICOM_YYYYMMDD_[ENTITY].csv`

2. **Custom Java Code:**

   - The [`codeForOds.java`](codeForOds.java) file contains Java code snippets used in various tJava components
   - Copy relevant code blocks into tJava components as specified in the comments

3. **jGenerateCalender:**:
   - This is used to create the jGenerateCalendar job, but u also need the **joursFeries.xlxs** to load the date to use through the tFileInputExcel component

## Usage Guide

After setting up the project, you can run the main orchestration job:

1. Open the job `jAlimentationBDD` in Talend
2. Run the job to execute the entire ETL pipeline
3. Watch the console for logs and progress

To validate your work, check the database for the following:

- ODS tables in the `VENTE_ODS` schema
- DWH tables in the `VENTE_DWH` schema

## Video References:

- [Part1](https://www.youtube.com/watch?v%3D2Ncg1ieyyZQ&source=gmail&ust=1749221568327000&usg=AOvVaw2miiFjfYEVptjbTy39twTJ)
- [Part2](https://www.youtube.com/watch?v%3D-CZILJ4swGk&source=gmail&ust=1749221568327000&usg=AOvVaw312oEIcgUhGVLWWhGUSw25)
- [Part3](https://www.youtube.com/watch?v%3DlGTMhZ22-jM&source=gmail&ust=1749221568327000&usg=AOvVaw2OGMtxmlI6JOoAc6k1sDYs)

**Note:** Part 3 isn’t included in the repository because it focuses on the build and scheduling process. However, it's straightforward to set up — just refer to the last video in the playlist linked above, which walks through everything step by step.
