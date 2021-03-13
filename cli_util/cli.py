from biosimulators_utils.log.data_model import Status, CombineArchiveLog, SedDocumentLog  # noqa: F401
from biosimulators_utils.plot.data_model import PlotFormat  # noqa: F401
from biosimulators_utils.report.data_model import DataSetResults, ReportResults, ReportFormat  # noqa: F401
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml.io import SedmlSimulationReader
from biosimulators_utils.combine.utils import get_sedml_contents
from biosimulators_utils.combine.io import CombineArchiveReader
import fire
import glob
import os
import pandas as pd
import shutil
import tempfile


def exec_sed_doc(omex_file_path, base_out_path):
    archive_tmp_dir = tempfile.mkdtemp()

    # defining archive
    archive = CombineArchiveReader.run(omex_file_path, archive_tmp_dir)

    # determine files to execute
    sedml_contents = get_sedml_contents(archive)

    report_results = ReportResults()
    data_resutls_arr = []
    for i_content, content in enumerate(sedml_contents):
        content_filename = os.path.join(archive_tmp_dir, content.location)
        content_id = os.path.relpath(content_filename, archive_tmp_dir)

        doc = SedmlSimulationReader().run(content_filename)

        for report_filename in glob.glob(os.path.join(base_out_path, content.location, '*.csv')):
            report_id = os.path.splitext(os.path.basename(report_filename))[0]

            # read report from CSV file produced by VCell
            data_set_df = pd.read_csv(report_filename).transpose()
            data_set_df.columns = data_set_df.iloc[0]
            data_set_df = data_set_df.drop(data_set_df.iloc[0].name)
            data_set_df = data_set_df.reset_index()
            data_set_df = data_set_df.rename(
                columns={'index': data_set_df.columns.name})
            data_set_df = data_set_df.transpose()
            data_set_df.index.name = None

            report = next(
                report for report in doc.outputs if report.id == report_id)

            data_set_results = DataSetResults()
            for data_set in report.data_sets:
                data_set_results[data_set.id] = data_set_df.loc[data_set.label, :].to_numpy(
                )

            # append to data structure of report results
            report_results[report_id] = data_set_results

            # save file in desired BioSimulators format(s)
            # for report_format in report_formats:
            ReportWriter().run(report,
                               data_set_results,
                               base_out_path,
                               os.path.join(content.location, report.id),
                               format='h5')

    ## Remove temp directory
    shutil.rmtree(archive_tmp_dir)


def transpose_vcml_csv(csv_file_path: str):
    df = pd.read_csv(csv_file_path, header=None);
    cols = list(df.columns)
    final_cols = [col for col in cols if col != '']
    df[final_cols].transpose().to_csv(csv_file_path, header=False, index=False)


if __name__ == "__main__":
    fire.Fire({
        'execSedDoc': exec_sed_doc,
        'transposeVcmlCsv': transpose_vcml_csv,
    })
