
from biosimulators_utils.combine.exec import exec_sedml_docs_in_archive
from biosimulators_utils.log.data_model import Status, CombineArchiveLog, SedDocumentLog  # noqa: F401
from biosimulators_utils.plot.data_model import PlotFormat  # noqa: F401
from biosimulators_utils.report.data_model import DataSetResults, ReportResults, ReportFormat  # noqa: F401
from biosimulators_utils.report.io import ReportWriter
from biosimulators_utils.sedml.data_model import Task, Report, DataSet, Plot2D, Curve, Plot3D, Surface
from biosimulators_utils.sedml.io import SedmlSimulationReader
import fire
import glob
import os
import pandas as pd
import shutil
import tempfile


def exec_sed_doc(sedml_file_path, working_dir, base_out_path, csv_dir, rel_out_path=None,
                 apply_xml_model_changes=True, report_formats=None, plot_formats=None,
                 log=None, indent=0):

    tmp_out_dir = csv_dir
    doc = SedmlSimulationReader().run(sedml_file_path)
    report_results = ReportResults()
    for report_filename in glob.glob(os.path.join(tmp_out_dir, '*.csv')):
        report_id = os.path.splitext(os.path.basename(report_filename))[0]

        # read report from CSV file produced by VCell
        data_set_df = pandas.read_csv(report_filename).transpose()
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
                           os.path.join(
                               rel_out_path, report_id) if rel_out_path else report_id,
                           format='h5')
        # for report_format in report_formats:
        #     ReportWriter().run(report,
        #                        data_set_results,
        #                        base_out_path,
        #                        os.path.join(rel_out_path, report_id) if rel_out_path else report_id,
        #                        format=report_format)

    # Move the plot outputs to the permanent output directory
    out_dir = base_out_path
    if rel_out_path:
        out_dir = os.path.join(out_dir, rel_out_path)

    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

def transpose_vcml_csv(csv_file_path: str):
    df =  pd.read_csv(csv_file_path, header=None);
    cols = list(df.columns)
    final_cols = [col for col in cols if col!='']
    df[final_cols].transpose().to_csv(csv_file_path, header=False, index=False)


if __name__ == "__main__":
    fire.Fire({
        'execSedDoc': exec_sed_doc,
        'transposeVcmlCsv': transpose_vcml_csv,
    })

