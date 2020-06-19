# coding: utf8

import torch
import os
from torch.utils.data import DataLoader

from ..tools.deep_learning.autoencoder_utils import train, visualize_image
from ..tools.deep_learning.models import init_model, load_model, save_initialization
from ..tools.deep_learning.data import (load_data,
                                        get_transforms,
                                        return_dataset)


def train_autoencoder(params):

    init_path = os.path.join(params.output_dir, 'best_model_dir', 'ConvAutoencoder')
    save_initialization(params.model, init_path, init_state=params.init_state, autoencoder=True, dropout=params.dropout)
    transformations = get_transforms(params.mode, params.minmaxnormalization)
    criterion = torch.nn.MSELoss()

    if params.split is None:
        fold_iterator = range(params.n_splits)
    else:
        fold_iterator = params.split

    for fi in fold_iterator:

        training_df, valid_df = load_data(
                params.tsv_path,
                params.diagnoses,
                fi,
                n_splits=params.n_splits,
                baseline=params.baseline
                )

        print("Running for the %d-th fold" % fi)

        data_train = return_dataset(params.mode, params.input_dir, training_df, params.preprocessing,
                                    transformations, params)
        data_valid = return_dataset(params.mode, params.input_dir, valid_df, params.preprocessing,
                                    transformations, params)

        # Use argument load to distinguish training and testing
        train_loader = DataLoader(
                data_train,
                batch_size=params.batch_size,
                shuffle=True,
                num_workers=params.num_workers,
                pin_memory=True)

        valid_loader = DataLoader(
                data_valid,
                batch_size=params.batch_size,
                shuffle=False,
                num_workers=params.num_workers,
                pin_memory=True)

        # Define output directories
        log_dir = os.path.join(params.output_dir, "log_dir", "fold_%i" % fi, "ConvAutoencoder")
        model_dir = os.path.join(params.output_dir, "best_model_dir", "fold_%i" % fi, "ConvAutoencoder")
        visualization_dir = os.path.join(params.output_dir, 'autoencoder_reconstruction', 'fold_%i' % fi)

        decoder = init_model(params.model, init_path, params.init_state, gpu=params.gpu,
                             autoencoder=True, dropout=params.dropout)
        optimizer = eval("torch.optim." + params.optimizer)(filter(lambda x: x.requires_grad, decoder.parameters()),
                                                            lr=params.learning_rate,
                                                            weight_decay=params.weight_decay)

        train(decoder, train_loader, valid_loader, criterion, optimizer, False,
              log_dir, model_dir, params)

        if params.visualization:
            print("Visualization of autoencoder reconstruction")
            best_decoder, _ = load_model(decoder, os.path.join(model_dir, "best_loss"),
                                         params.gpu, filename='model_best.pth.tar')
            num_patches = train_loader.dataset.patchs_per_patient
            visualize_image(best_decoder, valid_loader, os.path.join(visualization_dir, "validation"),
                            nb_images=num_patches)
            visualize_image(best_decoder, train_loader, os.path.join(visualization_dir, "train"),
                            nb_images=num_patches)
        del decoder
        torch.cuda.empty_cache()
