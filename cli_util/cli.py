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
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import libsedml as lsed
from libsedml import SedReport, SedPlot2D

def exec_sed_doc(omex_file_path, base_out_path):
    archive_tmp_dir = tempfile.mkdtemp()

    # defining archive
    archive = CombineArchiveReader.run(omex_file_path, archive_tmp_dir)

    # determine files to execute
    sedml_contents = get_sedml_contents(archive)

    report_results = ReportResults()
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
    df = pd.read_csv(csv_file_path, header=None)
    cols = list(df.columns)
    final_cols = [col for col in cols if col != '']
    df[final_cols].transpose().to_csv(csv_file_path, header=False, index=False)


def get_all_dataref_and_curves(sedml_path):
    all_plot_curves = {}
    all_report_dataref = {}

    sedml = lsed.readSedML(sedml_path)

    for output in sedml.getListOfOutputs():
        if type(output) == SedPlot2D:
            all_curves = {}
            for curve in output.getListOfCurves():
                all_curves[curve.getId()] = {
                    'x': curve.getXDataReference(),
                    'y': curve.getYDataReference()
                }
            all_plot_curves[output.getId()] = all_curves
        if type(output) == SedReport:
            for dataset in output.getListOfDataSets():

                ######
                if output.getId() in all_report_dataref:

                    all_report_dataref[output.getId()].append({
                        'data_reference': dataset.getDataReference(),
                        'data_label': dataset.getLabel()
                    })
                else:
                    all_report_dataref[output.getId()] = []
                    all_report_dataref[output.getId()].append({
                        'data_reference': dataset.getDataReference(),
                        'data_label': dataset.getLabel()
                    })


    return all_report_dataref, all_plot_curves



def get_report_label_from_data_ref(dataref: str, all_report_dataref):
    for report in all_report_dataref.keys():
        for data_ref in all_report_dataref[report]:
            if dataref == data_ref['data_reference']:
                return report, data_ref['data_label']


### Update plots dict

def update_dataref_with_report_label(all_report_dataref, all_plot_curves):

    for plot,curves in all_plot_curves.items():
        for curve_name,datarefs in curves.items():
            new_ref = dict(datarefs)
            new_ref['x'] = get_report_label_from_data_ref(datarefs['x'], all_report_dataref)[1]
            new_ref['y'] = get_report_label_from_data_ref(datarefs['y'], all_report_dataref)[1]
            new_ref['report'] = get_report_label_from_data_ref(datarefs['y'], all_report_dataref)[0]
            curves[curve_name] = new_ref

    return all_report_dataref, all_plot_curves



def get_report_dataframes(all_report_dataref, result_out_dir):
    report_frames = {}
    reports_list = list(set(all_report_dataref.keys()))
    for report in reports_list:
        report_frames[report] = pd.read_csv(os.path.join(result_out_dir, report + ".csv")).T.reset_index()
        report_frames[report].columns = report_frames[report].iloc[0].values
        report_frames[report].drop(index = 0, inplace=True)
    return report_frames

## PLOTTING

def plot_and_save_curves(all_plot_curves, report_frames, result_out_dir):
    all_plots = dict(all_plot_curves)
    for plot, curve_dat in all_plots.items():
        dims = (12, 8)
        fig, ax = plt.subplots(figsize=dims)
        for curve, data in curve_dat.items():
            df = report_frames[data['report']]
            sns.lineplot(x=df[data['x']].astype(np.float), y=df[data['y']].astype(np.float), ax=ax, label=curve)
            ax.set_ylabel('')
        #         plt.show()
        plt.savefig(os.path.join(result_out_dir, plot + '.pdf'), dpi=300)

def gen_plot_pdfs(sedml_path, result_out_dir):
    all_report_dataref, all_plot_curves = get_all_dataref_and_curves(sedml_path)
    all_report_dataref, all_plot_curves =  update_dataref_with_report_label(all_report_dataref, all_plot_curves)
    report_frames = get_report_dataframes(all_report_dataref, result_out_dir)
    plot_and_save_curves(all_plot_curves, report_frames, result_out_dir)


if __name__ == "__main__":
    fire.Fire({
        'execSedDoc': exec_sed_doc,
        'transposeVcmlCsv': transpose_vcml_csv,
        'genPlotPdfs': gen_plot_pdfs,
    })
