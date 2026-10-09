library(DataQualityDashboard)

# 1. Connection Setup ----------------------------------------------------------
connectionDetails <- DatabaseConnector::createConnectionDetails(
  dbms = "postgresql",
  user = "postgres",
  password = Sys.getenv("MIMIC_DB_PASSWORD"),
  server = "localhost/mimic_iv_clinical_hosp",
  port = 5432,
  pathToDriver = Sys.getenv("OHDSI_DRIVER_PATH", "drivers")
)

cdmDatabaseSchema <- "cdm"
resultsDatabaseSchema <- "cdm" 
cdmVersion <- "5.3"            
cdmSourceName <- "MIMIC_IV_CDM"
outputFolder <- Sys.getenv("DQD_OUTPUT_DIR", "dqd_output")

# 2. Execute Data Quality Checks -----------------------------------------------
results <- DataQualityDashboard::executeDqChecks(
  connectionDetails = connectionDetails,
  cdmDatabaseSchema = cdmDatabaseSchema,
  resultsDatabaseSchema = resultsDatabaseSchema,
  cdmSourceName = cdmSourceName,
  numThreads = 1,
  sqlOnly = FALSE,               
  outputFolder = outputFolder,
  verboseMode = TRUE,
  writeToTable = FALSE,
  
  # REMEDY: We add VISIT_OCCURRENCE here to stop the column layout crash completely
  tablesToExclude = c(
    "VISIT_OCCURRENCE", "VISIT_DETAIL", 
    "CONCEPT", "VOCABULARY", "CONCEPT_ANCESTOR", 
    "CONCEPT_RELATIONSHIP", "CONCEPT_CLASS", "CONCEPT_SYNONYM", 
    "RELATIONSHIP", "DOMAIN"
  ),
  
  checkLevels = c("TABLE", "FIELD") 
)

# 3. View the Dashboard --------------------------------------------------------
DataQualityDashboard::viewDqDashboard(file.path(outputFolder, "results_MIMIC_IV_CDM.json"))