import os
import fire
import libcombine
import libsedml
import yaml
import tempfile
import zipfile


# Create temp directory
tmp_dir = tempfile.mkdtemp()

def extract_omex_archive(omex_file):
    if not os.path.isfile(omex_file):
        raise FileNotFoundError("File does not exist: {}".format(omex_file))

    if not zipfile.is_zipfile(omex_file):
        raise IOError("File is not an OMEX Combine Archive in zip format: {}".format(omex_file))

    omex_file = os.path.abspath(omex_file)

    archive = libcombine.CombineArchive()
    archive.initializeFromArchive(omex_file)
    is_extracted = archive.extractTo(tmp_dir)

    sedml_files_list = list()
    if is_extracted is True:
        for file_name in os.listdir(tmp_dir):
            if file_name.endswith(".sedml"):
                sedml_files_list.append(file_name)
    return sedml_files_list


def status_yml(omex_file, task_status, sim_status):
    yaml_dict = {}
    
    for sedml in extract_omex_archive(omex_file):
        outputs_dict = {"outputs": {}}
        tasks_dict = {"tasks": {}}
        # add temp dir path
        sedml_path = os.path.join(tmp_dir, sedml)
        sedml_doc = libsedml.readSedMLFromFile(sedml_path)

        # Get all the required metadata
        tasks = sedml_doc.getListOfTasks()
        plots = sedml_doc.getListOfOutputs()

        # Convert into the list
        task_list = [task.getId() for task in tasks]
        
        plots_dict = {}
        reports_dict = {}
        other_list = []
        
        for plot in plots:
            if type(plot) == libsedml.SedPlot2D:
                plots_dict[plot.getId()] = [curve.getId() for curve in plot.getListOfCurves()]
            elif type(plot) == libsedml.SedReport:
                reports_dict[plot.getId()] = [dataSet.getId() for dataSet in plot.getListOfDataSets()]
            else:
                other_list.append(plot.getId())        

        for plot in list(plots_dict.keys()):
            curves_dict = {}
            for curve in plots_dict[plot]:
                curves_dict[curve] = 'SKIPPED'
            outputs_dict["outputs"].update({plot: {"curves": curves_dict}})
            outputs_dict["outputs"][plot].update({"status": "SKIPPED"})
            
        for report in list(reports_dict.keys()):
            dataset_dict = {}
            for dataset in reports_dict[report]:
                dataset_dict[dataset] = 'SKIPPED'
            # TODO: get status from resultant CSV
            outputs_dict["outputs"].update({report: {"dataSets": dataset_dict}})
            outputs_dict["outputs"][report].update({"status": "SKIPPED"})

        for task in task_list:
            tasks_dict["tasks"].update({task: {"status": task_status}})

        sed_doc_dict = {sedml: {}}
        sed_doc_dict[sedml].update(outputs_dict)
        sed_doc_dict[sedml].update(tasks_dict)
        sed_doc_dict[sedml].update({"status": "SKIPPED"})
        yaml_dict[sedml] = sed_doc_dict[sedml]
    final_dict = {}
    final_dict['sedDocuments'] = dict(yaml_dict)
    final_dict['status'] = sim_status

    with open("status.yml", 'w' , encoding="utf-8") as sy:
        sy.write(yaml.dump(final_dict))
    # return final_dict


if __name__ == "__main__":
    fire.Fire({
        'status_yml': status_yml,
    })
    