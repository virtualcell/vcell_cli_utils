
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
import pandas
import shutil
import tempfile


def exec_sed_doc(sedml_file_path, working_dir, base_out_path, csv_dir, rel_out_path=None,
                 apply_xml_model_changes=True, report_formats=None, plot_formats=None,
                 log=None, indent=0):
    """
    Args:
        sedml_file_path (:obj:`str`): a path to SED-ML file which defines a SED document
        working_dir (:obj:`str`): working directory of the SED document (path relative to which models are located)

        out_path (:obj:`str`): path to store the outputs

            * CSV: directory in which to save outputs to files
              ``{out_path}/{rel_out_path}/{report.id}.csv``
            * HDF5: directory in which to save a single HDF5 file (``{out_path}/reports.h5``),
              with reports at keys ``{rel_out_path}/{report.id}`` within the HDF5 file

        rel_out_path (:obj:`str`, optional): path relative to :obj:`out_path` to store the outputs
        apply_xml_model_changes (:obj:`bool`, optional): if :obj:`True`, apply any model changes specified in the SED-ML file before
            calling :obj:`task_executer`.
        report_formats (:obj:`list` of :obj:`ReportFormat`, optional): report format (e.g., csv or h5)
        plot_formats (:obj:`list` of :obj:`PlotFormat`, optional): plot format (e.g., pdf)
        log (:obj:`SedDocumentLog`, optional): execution status of document
        indent (:obj:`int`, optional): degree to indent status messages

    Returns:
        :obj:`ReportResults`: results of each report
    """

    tmp_out_dir = csv_dir
    doc = SedmlSimulationReader().run(sedml_file_path)
    report_results = ReportResults()
    for report_filename in glob.glob(os.path.join(tmp_out_dir, '*.csv')):
        report_id = os.path.splitext(os.path.basename(report_filename))[0]

        # read report from CSV file produced by tellurium
        print(report_filename)
        data_set_df = pandas.read_csv(report_filename).transpose()
        data_set_df.columns = data_set_df.iloc[0]
        data_set_df = data_set_df.drop(data_set_df.iloc[0].name)
        data_set_df = data_set_df.reset_index()
        data_set_df = data_set_df.rename(
            columns={'index': data_set_df.columns.name})
        data_set_df = data_set_df.transpose()
        data_set_df.index.name = None

        # create pseudo-report for ReportWriter
        print(report_id)
        for report in doc.outputs:
            print(report.id)
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

    # for plot_format in plot_formats:
    #     for plot_filename in glob.glob(os.path.join(tmp_out_dir, '*.' + plot_format.value)):
    #         shutil.move(plot_filename, out_dir)

    # Clean up the temporary directory for tellurium's outputs
    # shutil.rmtree(tmp_out_dir)

    # Return a data structure with the results of the reports
    # return report_results


if __name__ == "__main__":
    fire.Fire(exec_sed_doc)
