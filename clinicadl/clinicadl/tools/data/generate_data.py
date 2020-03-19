"""
This file generates data for trivial or intractable (random) data for binary classification.
"""
import pandas as pd
import numpy as np
import nibabel as nib
from os import path
import os
import torch.nn.functional as F
import torch


def generate_random_dataset(caps_dir, tsv_path, output_dir, n_subjects, mean=0, sigma=0.5,
                            preprocessing="linear", output_size=None):
    """
    Generates an intractable classification task from the first subject of the tsv file.

    :param caps_dir: (str) path to the CAPS directory.
    :param tsv_path: (str) path to tsv file of list of subjects/sessions.
    :param output_dir: (str) folder containing the synthetic dataset in CAPS format
    :param n_subjects: (int) number of subjects in each class of the synthetic dataset
    :param mean: (float) mean of the gaussian noise
    :param sigma: (float) standard deviation of the gaussian noise
    :param preprocessing: (str) preprocessing performed. Must be in ['linear', 'extensive'].
    :param output_size: (tuple[int]) size of the output. If None no interpolation will be performed.
    """
    # Read DataFrame
    data_df = pd.read_csv(tsv_path, sep='\t')

    # Create subjects dir
    if not path.exists(path.join(output_dir, 'subjects')):
        os.makedirs(path.join(output_dir, 'subjects'))

    # Retrieve image of first subject
    participant_id = data_df.loc[0, 'participant_id']
    session_id = data_df.loc[0, 'session_id']
    if preprocessing == "linear":
        image_path = path.join(caps_dir, 'subjects', participant_id, session_id,
                               't1', 'preprocessing_dl',
                               participant_id + '_' + session_id +
                               '_space-MNI_res-1x1x1.nii.gz')
    elif preprocessing == "extensive":
        image_path = path.join(caps_dir, 'subjects', participant_id, session_id,
                               't1', 'spm', 'segmentation', 'normalized_space',
                               participant_id + '_' + session_id +
                               '_T1w_segm-graymatter_space-Ixi549Space_modulated-off_probability.nii.gz')
    else:
        raise ValueError("Preprocessing %s must be in ['linear', 'extensive']." % preprocessing)
    image_nii = nib.load(image_path)
    image = image_nii.get_data()

    # Create output tsv file
    participant_id_list = ['sub-RAND%i' % i for i in range(2 * n_subjects)]
    session_id_list = ['ses-M00'] * 2 * n_subjects
    diagnosis_list = ['AD'] * n_subjects + ['CN'] * n_subjects
    data = np.array([participant_id_list, session_id_list, diagnosis_list])
    data = data.T
    output_df = pd.DataFrame(data, columns=['participant_id', 'session_id', 'diagnosis'])
    output_df['age'] = 60
    output_df['sex'] = 'F'
    output_df.to_csv(path.join(output_dir, 'data.tsv'), sep='\t', index=False)

    for i in range(2 * n_subjects):
        gauss = np.random.normal(mean, sigma, image.shape)
        participant_id = 'sub-RAND%i' % i
        noisy_image = image + gauss
        if output_size is not None:
            noisy_image_pt = torch.Tensor(noisy_image[np.newaxis, np.newaxis, :])
            noisy_image_pt = F.interpolate(noisy_image_pt, output_size)
            noisy_image = noisy_image_pt.numpy()[0, 0, :, :, :]
        noisy_image_nii = nib.Nifti1Image(noisy_image, header=image_nii.header, affine=image_nii.affine)
        noisy_image_nii_path = path.join(output_dir, 'subjects', participant_id, 'ses-M00', 't1', 'preprocessing_dl')
        noisy_image_nii_filename = participant_id + '_ses-M00_space-MNI_res-1x1x1.nii.gz'
        if not path.exists(noisy_image_nii_path):
            os.makedirs(noisy_image_nii_path)
        nib.save(noisy_image_nii, path.join(noisy_image_nii_path, noisy_image_nii_filename))
