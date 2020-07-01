# coding: utf8

import pytest
import os
import shutil


@pytest.fixture(params=[
    'classify_image',
    'classify_slice',
    'classify_patch'
])
def cli_commands(request):

    if request.param == 'classify_image':
        test_input = [
            'classify',
            'data/OASIS_test',
            'data/OASIS_test/data.tsv',
            'data/models/image/baseline/AD_CN_one_fold/',
            '--output_directory', 'data/output/',
            '--prefix_output', 'DB-XXXX',
            '-cpu'
        ]
    elif request.param == 'classify_slice':
        test_input = [
            'classify',
            'data/OASIS_test',
            'data/OASIS_test/data.tsv',
            'data/models/slice/baseline/AD_CN/',
            '--prefix_output', 'DB-XXXX',
            '-cpu'
        ]
    elif request.param == 'classify_patch':
        test_input = [
            'classify',
            'data/OASIS_test',
            'data/OASIS_test/data.tsv',
            'data/models/patch/baseline/AD_CN/',
            '--prefix_output', 'DB-XXXX',
            '-cpu'
        ]
    else:
        raise NotImplementedError(
            "Test %s is not implemented." %
            request.param)

    return test_input


def test_train(cli_commands):
    test_input = cli_commands

    flag_error = not os.system("clinicadl " + " ".join(test_input))

    assert flag_error
