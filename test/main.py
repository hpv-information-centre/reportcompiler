import os

from reportcompiler.errors import FragmentGenerationError
from reportcompiler.reports import Report

# TODO: More consistent testing
report_path = os.path.join(
                os.path.realpath(
                    os.path.join(__file__, '..', '..')),
                'sample_reports',
                'FactSheetTest'
                )
report = Report(report_path)
# report = Report(
#           repo_url='http://icosrvprec02/gitlab/'
#                    'informationcenter/report_factsheet-test.git',
#           repo_path='I:/d_gomez/reports')
try:
    report.generate([{'iso': iso} for iso in ['ESP', 'FRA', ]],
                    n_doc_workers=1,
                    n_frag_workers=1)
    print('All documents generated successfully!')
except FragmentGenerationError as e:
    print(e)
