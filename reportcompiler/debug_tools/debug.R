library(jsonlite)

compile_last_fragment <- function(report_path) {
    tryCatch(
        json_file <- file(paste(report_path, '_meta', 'last_debug_errors',sep='/'), open='r'),
        error=function() {
            print('There is no file with debugging data, please retry generating a document on debug mode')
        })
    last_values <- fromJSON(json_file, simplifyVector=F)
    
    for(frag in last_values) {
        doc_var <- frag$doc_var
        data <- lapply(names(frag$data), function(n){data.frame(frag$data[n][[1]])})
        names(data) <- names(frag$data)
        metadata <- frag$metadata
        
        path <- metadata$fragment_path
        if (any(endsWith(path, c('.R', '.r')))) {
            source(metadata$fragment_path)
            tryCatch({
                  generate_context(doc_var, data, metadata)
                },
                error=function(){
                    print(paste(basename(path), " has finished with errors."))
                }
            )
            print(paste(basename(path), " has finished successfully."))
        } else {
            print(paste(basename(path), " doesn't use R, skipping..."))
        }
    }
}

reports.path <- Sys.getenv('REPORTS_PATH')

compile_last_fragment(reports.path)