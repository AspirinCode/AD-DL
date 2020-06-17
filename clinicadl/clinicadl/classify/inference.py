# coding: utf8

from clinicadl.tools.deep_learning import create_model, load_model, read_json
from clinicadl.tools.deep_learning.data import MinMaxNormalization
import pandas as pd
import torch.nn as nn
from torch.utils.data import DataLoader

def classify(caps_dir, tsv_file, model_path, output_dir=None):
    """
    This function reads the command line parameters and point to inference

    Parameters:

    params : class clinicadl.tools.dee_learning.iotools.Parameters

    Returns:

    """
    from os.path import isdir, join, abspath, exists
    from os import strerror
    import errno 
    # Verify that paths exist
    caps_dir = abspath(caps_dir)
    model_path = abspath(model_path)
    print(model_path)
    tsv_file = abspath(tsv_file)

    if not isdir(caps_dir):
        print("Folder containing MRIs is not found, please verify its location")
        raise FileNotFoundError(
                errno.ENOENT, strerror(errno.ENOENT), caps_dir)
        print("Folder containing MRIs is not found, please verify its location")
    if not isdir(model_path):
        print("A valid model in the path was not found. Donwload them from aramislab.inria.fr")
        raise FileNotFoundError(
                errno.ENOENT, strerror(errno.ENOENT), model_path)
    if not exists(tsv_file):
        raise FileNotFoundError(
                errno.ENOENT, strerror(errno.ENOENT), tsv_file)
    
    # Infer json file from model_path (suppose that json file is at the same
    # folder)

    json_file = join(model_path, 'commandline_CNN.json')

    if not exists(json_file):
        print("Json file doesn't exist")
        raise FileNotFoundError(
                errno.ENOENT, strerror(errno.ENOENT), json_file)

    results_df = inference_from_model(caps_dir, tsv_file, model_path, json_file)
    
    print(results_df)

def inference_from_model(caps_dir,
                         tsv_file,
                         model_path=None,
                         json_file=None):
    """
    Inference from trained model

    This functions uses a previously trained model to classify the input

    Args:

    caps_dir: folder containing the tensor files (.pt version of MRI)
    tsv_file: file with the name of the MRIs to process (single or multiple)
    model_path: file with the model (pth format).
    json_file: file containing the training parameters.

    Returns:

    Pandas data frame with a list of subjects and their infered clases
    (predictions).

    Rises:


    """
#    TODO: Implement a DataLoader using clinica_file_reader
#
#    from clinica.utils.inputs import clinica_file_reader
#    from clinica.utils.exceptions import ClinicaBIDSError, ClinicaException
#    from clinica.utils.paricipants import get_subject_session_list
#
#    T1W_LINEAR_CROPPED_TENSOR = {'pattern': '*space-MNI152NLin2009cSym_desc-Crop_res-1x1x1_T1w.pt',
#            'description': 'Tensor vesrion of the T1W image registered using t1-linear and cropped '
#            '(matrix size 169×208×179, 1 mm isotropic voxels)',
#            'needed_pipeline': 'deeplearning-prepare-data'}
#
#    FILE_TYPE = T1W_LINEAR_CROPPED_TENSOR
#
#    sessions, subjects = get_subject_session_list(caps_dir,
#            tsv_file,
#            is_bids_dir=False,
#            use_session_tsv=False,
#            tsv_dir=None)
#
#    try:
#        t1w_files = clinica_file_reader(subjects,
#                sessions,
#                caps_dir,
#                FILE_TYPE)
#    except ClinicaException as e:
#        err = 'Clinica faced error(s) while trying to read files in your CAPS directory.\n' + str(e)
#        raise ClinicaBIDSError(err)

    import argparse

    print("This is the inference phase")
    
    parser = argparse.ArgumentParser()
    parser.add_argument("model_path", type=str,
            help="Path to the trained model folder.")
    options = parser.parse_args([model_path])
    options = read_json(options, "CNN", json_path=json_file)
    print("Load model with these options")
    print(options)

    options.use_gpu=False

    if (options.mode == 'image'):
        infered_classes = inference_from_image_model(
            caps_dir,
            tsv_file,
            model_path,
            options)
    elif (options.mode == 'slice'):
        infered_clases = inference_from_slice_model(
            caps_dir,
            tsv_file,
            model_path,
            options)
    elif (options.mode == 'patch'):
        infered_clases = inference_from_patch_model(
            caps_dir,
            tsv_file,
            model_path,
            options)
    elif (options.mode == 'roi'):
        infered_clases = inference_from_roi_model()
    else:
        print("Inference for this image mode is not implemented")
    
    return infered_classes


def inference_from_image_model(caps_dir, tsv_file, model_path, options):
    '''
    Inference for image/subject model



    '''
    from clinicadl.tools.deep_learning.data import MRIDataset
    from clinicadl.image_level.utils import test
    # Recreate the model with the network described in the json file
    model = create_model(options.network)
    criterion = nn.CrossEntropyLoss()

    # Load model from path
    best_model, best_epoch = load_model(
        model, model_path,
        options.use_gpu, filename='model_best.pth.tar')

    if options.minmaxnormalization:
        transformations = MinMaxNormalization()
    else:
        transformations = None

    # Read/localize the data
    data_to_test = MRIDataset(
        caps_dir,
        tsv_file,
        options.preprocessing,
        transform=transformations)

    # Load the data
    test_loader = DataLoader(
        data_to_test,
        batch_size=options.batch_size,
        shuffle=False,
        num_workers=options.nproc,
        pin_memory=True)

    # Run the model on the data
    metrics_test, loss_test, test_df = test(
        best_model,
        test_loader,
        options.use_gpu,
        criterion,
        full_return=True)
    
    return test_df

def inference_from_slice_model(caps_dir, tsv_file, model_path, options):
    '''
    Inference for slice model



    '''
    from clinicadl.tools.deep_learning.data import MRIDataset_slice
    from clinicadl.slice_level.utils import test
    # Initialize the model
    print('Do transfer learning with existed model trained on ImageNet.')

    model = create_model(options.network, options.gpu)
    trg_size = (224, 224)  # most of the imagenet pretrained model has this input size

    # All pre-trained models expect input images normalized in the same way,
    # i.e. mini-batches of 3-channel RGB images of shape (3 x H x W), where H
    # and W are expected to be at least 224. The images have to be loaded in to
    # a range of [0, 1] and then normalized using mean = [0.485, 0.456, 0.406]
    # and std = [0.229, 0.224, 0.225].
    transformations = transforms.Compose([MinMaxNormalization(),
        transforms.ToPILImage(),
        transforms.Resize(trg_size),
        transforms.ToTensor()])
    # Define loss and optimizer
    loss = torch.nn.CrossEntropyLoss()

    # Load data
    _, test_df = load_data(tsv_file, options.diagnoses, fi,
            n_splits=options.n_splits, baseline=True)
    
    # Load model from path
    best_model, best_epoch = load_model(
        model, model_path,
        options.use_gpu, filename='model_best.pth.tar')

    if options.minmaxnormalization:
        transformations = MinMaxNormalization()
    else:
        transformations = None

    # Read/localize the data
    data_to_test = MRIDataset_slice(
        caps_dir,
        tsv_file,
        transform=transformations,
        mri_plane=options.mri_plane,
        prepare_dl=options.prepare_dl)

    # Load the data
    test_loader = DataLoader(
        data_to_test,
        batch_size=options.batch_size,
        shuffle=False,
        num_workers=options.nproc,
        pin_memory=True)

    # Run the model on the data
    metrics_test, loss_test, test_df = test(
        best_model,
        test_loader,
        options.use_gpu,
        loss)
    
    return test_df
