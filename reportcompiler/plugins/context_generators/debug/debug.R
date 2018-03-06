rm(list=ls(all=TRUE))

library(jsonlite)

debug.fragment <- function(doc.var, fragment.name, reportcompiler.engine.path, report.path) {
  
  fragment.path <- file.path(report.path, 'src', paste0(fragment.name, '.r'))
  source(fragment.path)
  subdir <- paste(doc.var, collapse='_')
  tmp.base.file <- file.path(report.path, 'gen', subdir, 'tmp', paste0(paste0(doc.var, collapse='-'), '_', fragment.name))
  
  doc.var <- fromJSON(paste0(tmp.base.file, '.docvar'))
  data <- fromJSON(paste0(tmp.base.file, '.data'))
  fragment.data <- fromJSON(paste0(tmp.base.file, '.metadata'))
  context = generate_context(doc.var, data, fragment.data)
  context
}

base.path <-  'C:/Users/47873315b/Dropbox/ICO/ReportCompiler/reportcompiler'
report.path <- 'C:/Users/47873315b/Dropbox/ICO/ReportCompiler/sample_reports'

doc.var <- list(artist_name='Gerald Moore')
fragment <- 'introduction'
report_dir <- 'TestPDFlatex'

debug.fragment( doc.var,
                fragment,
                base.path,
                file.path(report.path, report_dir))