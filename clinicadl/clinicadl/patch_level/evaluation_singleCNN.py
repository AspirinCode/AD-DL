# coding: utf8

import argparse
import os
import torchvision.transforms as transforms
from torch.utils.data import DataLoader
import torch

from clinicadl.tools.deep_learning.data import (MinMaxNormalization,
                                                load_data_test,
                                                load_data,
                                                MRIDataset_patch,
                                                MRIDataset_patch_hippocampus)
from clinicadl.tools.deep_learning import create_model, load_model
from ..tools.deep_learning.cnn_utils import test, sub_level_to_tsvs, soft_voting_to_tsvs


__author__ = "Junhao Wen"
__copyright__ = "Copyright 2018 The Aramis Lab Team"
__credits__ = ["Junhao Wen"]
__license__ = "See LICENSE.txt file"
__version__ = "0.1.0"
__maintainer__ = "Junhao Wen"
__email__ = "junhao.wen89@gmail.com"
__status__ = "Development"


def test_cnn(data_loader, subset_name, split, criterion, options):

    for selection in ["best_acc", "best_loss"]:
        # load the best trained model during the training
        model = create_model(options.model, options.gpu, dropout=options.dropout)
        model, best_epoch = load_model(model, os.path.join(options.output_dir, 'best_model_dir', "fold_%i" % split,
                                                           'CNN', selection),
                                       gpu=options.gpu, filename='model_best.pth.tar')

        results_df, metrics = test(model, data_loader, options.gpu, criterion, options.mode)
        print("%s level balanced accuracy is %f" % (options.mode, metrics['balanced_accuracy']))

        sub_level_to_tsvs(options.output_dir, results_df, metrics, split, selection, options.mode, dataset=subset_name)

        # Soft voting
        soft_voting_to_tsvs(options.output_dir, split, selection=selection, mode=options.mode, dataset=subset_name,
                            selection_threshold=options.selection_threshold)


parser = argparse.ArgumentParser(description="Argparser for test of hippocampus approach")

# Mandatory arguments
parser.add_argument("caps_directory", type=str,
                    help="Path to the caps of image processing pipeline of DL")
parser.add_argument('preprocessing', type=str,
                    help='Defines the type of preprocessing of CAPS data.',
                    choices=['t1-linear', 't1-extensive'])
parser.add_argument("diagnosis_tsv_path", type=str,
                    help="Path to tsv file of the population based on the diagnosis tsv files."
                         "To note, the column name should be participant_id, session_id and diagnosis.")
parser.add_argument("output_dir", type=str,
                    help="Path to store the classification outputs and the tsv files containing the performances.")

# Test parameters
parser.add_argument("--network", default="Conv4_FC3",
                    help="Autoencoder network type. (default=Conv_4_FC_3). "
                         "Also, you can try training from scratch using VoxResNet and AllConvNet3D")
parser.add_argument('--dropout', default=0, type=float,
                    help='rate of dropout that will be applied to dropout layers.')
parser.add_argument('--dataset', default="validation",
                    help="If the evaluation on the validation set is wanted, must be set to 'validation'. "
                         "Otherwise must be named with the form 'test-cohort_name'.")
parser.add_argument("--diagnoses", default=["sMCI", "pMCI"], type=str, nargs="+",
                    help="Labels based on binary classification.")
parser.add_argument("--patch_size", default=50, type=int,
                    help="The patch size extracted from the MRI")
parser.add_argument("--stride_size", default=50, type=int,
                    help="The stride for the patch extract window from the MRI")
parser.add_argument('--hippocampus_roi', default=False, action="store_true",
                    help="If train the model using only hippocampus ROI")
parser.add_argument('--prepare_dl', default=False, action="store_true",
                    help="If True the outputs of preprocessing prepare_dl are used, else the whole MRI is loaded.")
parser.add_argument("--n_splits", default=5, type=int,
                    help="Define the cross validation, by default, we use 5-fold.")
parser.add_argument("--split", default=None, type=int,
                    help="Default behaviour will run all splits, else only the splits specified will be run.")
parser.add_argument('--selection_threshold', default=None, type=float,
                    help='Threshold on the balanced accuracies to compute the subject-level performance '
                         'only based on patches with balanced accuracy > threshold.')


# Computational issues
parser.add_argument("--num_workers", default=8, type=int,
                    help='the number of batch being loaded in parallel')
parser.add_argument("--batch_size", default=32, type=int,
                    help="Batch size for training. (default=1)")
parser.add_argument('--gpu', default=False, action='store_true',
                    help='Uses gpu instead of cpu if cuda is available')


def main(options):

    transformations = transforms.Compose([MinMaxNormalization()])
    criterion = torch.nn.CrossEntropyLoss()

    if options.split is None:
        fold_iterator = range(options.n_splits)
    else:
        fold_iterator = options.split

    # Loop on folds
    for fi in fold_iterator:
        print("Fold %i" % fi)

        if options.dataset == 'validation':
            _, test_df = load_data(options.diagnosis_tsv_path, options.diagnoses, fi,
                                   n_splits=options.n_splits, baseline=True)
        else:
            test_df = load_data_test(options.diagnosis_tsv_path, options.diagnoses)

        if options.hippocampus_roi:
            data_test = MRIDataset_patch_hippocampus(options.caps_directory, test_df, transformations=transformations,
                                                     preprocessing=options.preprocessing)
        else:
            data_test = MRIDataset_patch(options.caps_directory, test_df, options.patch_size,
                                         options.stride_size, preprocessing=options.preprocessing,
                                         transformations=transformations, prepare_dl=options.prepare_dl)

        test_loader = DataLoader(data_test,
                                 batch_size=options.batch_size,
                                 shuffle=False,
                                 num_workers=options.num_workers,
                                 pin_memory=True)

        test_cnn(test_loader, options.dataset, fi, criterion, options)


if __name__ == "__main__":
    commandline = parser.parse_known_args()
    options = commandline[0]
    if commandline[1]:
        raise Exception("unknown arguments: %s" % (parser.parse_known_args()[1]))
    main(options)
