# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from glob import glob

IS_WINDOWS = os.name == 'nt'

from time import time

import subprocess

from .status_messenger import StatusMessenger

# rq worker-pool -n 4 run_ss_batch_hillslope run_hillslope run_flowpath run_watershed run_ss_batch_watershed

_thisdir = os.path.dirname(__file__)
_template_dir = _join(_thisdir, "templates")

wepp_bin_dir = os.path.abspath(_join(_thisdir, "bin"))

linux_wepp_bin_opts = glob(_join(wepp_bin_dir, "wepp_*"))
linux_wepp_bin_opts = [_split(p)[1] for p in linux_wepp_bin_opts]
linux_wepp_bin_opts = [p for p in linux_wepp_bin_opts if '.' not in p]
linux_wepp_bin_opts.append('latest')
linux_wepp_bin_opts.sort()

if IS_WINDOWS:
    _wepp = _join(wepp_bin_dir, "wepp2014.exe")
else:
    _wepp = _join(wepp_bin_dir, "wepp")


def _template_loader(fn):
    global _template_dir

    with open(_join(_template_dir, fn)) as fp:
        _template = fp.readlines()

        # the watershedslope.template contains comments.
        # here we strip those out
        _template = [L[:L.find('#')] for L in _template]
        _template = [L.strip() for L in _template]
        _template = '\n'.join(_template)

    return _template


def ss_hill_template_loader():
    return _template_loader("ss_hillslope.template")

def ss_batch_hill_template_loader():
    return _template_loader("ss_batch_hillslope.template")


def hill_template_loader():
    return _template_loader("hillslope.template")

def reveg_hill_template_loader():
    return _template_loader("reveg_hillslope.template")


def ss_flowpath_template_loader():
    return _template_loader("ss_flowpath.template")


def flowpath_template_loader():
    return _template_loader("flowpath.template")


def watershed_template_loader():
    return _template_loader("watershed.template")


def ss_watershed_template_loader():
    return _template_loader("ss_watershed.template")


def ss_batch_watershed_template_loader():
    return _template_loader("ss_batch_watershed.template")



def hillstub_omni_contrasts_template_loader():
    return """
M
Y
{wepp_id_path}.pass.dat"""

def hillstub_template_loader():
    return """
M
Y
../output/H{wepp_id}.pass.dat"""


def hillstub_ss_batch_template_loader():
    return """
M
Y
../output/{ss_batch_key}/H{wepp_id}.pass.dat"""


def make_flowpath_run(fp, wepp_id, sim_years, fp_runs_dir):
    _fp_template = flowpath_template_loader()

    s = _fp_template.format(fp=fp,
                            wepp_id=wepp_id,
                            sim_years=sim_years)

    fn = _join(fp_runs_dir, f'{fp}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_flowpath_run(fp, wepp_id, runs_dir):
    _fp_template = ss_flowpath_template_loader()

    s = _fp_template.format(fp=fp, wepp_id=wepp_id, runs_dir=os.path.abspath(runs_dir))

    fn = _join(runs_dir, f'{fp}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_hillslope_run(wepp_id, sim_years, runs_dir, reveg=True, omni=False):
    if reveg:
        _hill_template = reveg_hill_template_loader()
    else:
        _hill_template = hill_template_loader()

    cli_dir = ''
    slp_dir = ''

    if omni:
        cli_dir = '../../../../../wepp/runs/'
        slp_dir = '../../../../../wepp/runs/'

    s = _hill_template.format(wepp_id=wepp_id,
                              sim_years=sim_years,
                              cli_dir=cli_dir,
                              slp_dir=slp_dir)

    fn = _join(runs_dir, f'p{wepp_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_hillslope_run(wepp_id, runs_dir, omni=False):
    _hill_template = ss_hill_template_loader()

    cli_dir = ''
    slp_dir = ''

    if omni:
        cli_dir = '../../../../../wepp/runs/'
        slp_dir = '../../../../../wepp/runs/'

    s = _hill_template.format(wepp_id=wepp_id, 
                              cli_dir=cli_dir,
                              slp_dir=slp_dir)

    fn = _join(runs_dir, f'p{wepp_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_batch_hillslope_run(wepp_id, runs_dir, ss_batch_key, ss_batch_id, omni=False):
    _hill_template = ss_batch_hill_template_loader()

    cli_dir = ''
    slp_dir = ''

    if omni:
        cli_dir = '../../../../../wepp/runs/'
        slp_dir = '../../../../../wepp/runs/'

    s = _hill_template.format(wepp_id=wepp_id,
                              ss_batch_id=ss_batch_id,
                              ss_batch_key=ss_batch_key,
                              cli_dir=cli_dir,
                              slp_dir=slp_dir)

    fn = _join(runs_dir, f'p{wepp_id}.{ss_batch_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def run_ss_batch_hillslope(wepp_id, runs_dir, wepp_bin=None, ss_batch_id=None, status_channel=None, omni=False):
    assert ss_batch_id is not None
    t0 = time()

    if wepp_bin is not None:
        cmd = [os.path.abspath(_join(wepp_bin_dir, wepp_bin))]
    else:
        cmd = [os.path.abspath(_wepp)]

    assert _exists(_join(runs_dir, f'p{wepp_id}.man'))
    assert _exists(_join(runs_dir, f'p{wepp_id}.sol'))

    if omni:
        assert _exists(_join(runs_dir, '../../../../../wepp/runs', f'p{wepp_id}.slp'))
        assert _exists(_join(runs_dir, '../../../../../wepp/runs', f'p{wepp_id}.{ss_batch_id}.cli'))
    else:
        assert _exists(_join(runs_dir, f'p{wepp_id}.slp'))
        assert _exists(_join(runs_dir, f'p{wepp_id}.{ss_batch_id}.cli'))

    _run = open(_join(runs_dir, f'p{wepp_id}.{ss_batch_id}.run'))
    _stderr_fn = _join(runs_dir, f'p{wepp_id}.{ss_batch_id}.err')

    _log = open(_stderr_fn, 'w')

    p = subprocess.Popen(cmd, stdin=_run, stdout=_log, stderr=_log, cwd=runs_dir)
    p.wait()
    _run.close()
    _log.close()

    log_fn = _stderr_fn
    with open(log_fn) as fp:
        lines = fp.readlines()
        for L in lines:
            if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in L:
                return True, wepp_id, time() - t0

    raise Exception('Error running wepp for wepp_id %i\nSee %s'
                    % (wepp_id, log_fn))


def run_hillslope(wepp_id, runs_dir, wepp_bin=None, status_channel=None, omni=False):
    t0 = time()

    if wepp_bin is not None:
        cmd = [os.path.abspath(_join(wepp_bin_dir, wepp_bin))]
    else:
        cmd = [os.path.abspath(_wepp)]

    assert _exists(_join(runs_dir, f'p{wepp_id}.man'))
    assert _exists(_join(runs_dir, f'p{wepp_id}.sol'))

    if omni:
        assert _exists(_join(runs_dir, '../../../../../wepp/runs', f'p{wepp_id}.slp'))
        assert _exists(_join(runs_dir, '../../../../../wepp/runs', f'p{wepp_id}.cli'))
    else:
        assert _exists(_join(runs_dir, f'p{wepp_id}.slp')), omni
        assert _exists(_join(runs_dir, f'p{wepp_id}.cli'))

    _run = open(_join(runs_dir, f'p{wepp_id}.run'))
    _log = open(_join(runs_dir, f'p{wepp_id}.err'), 'w')

    p = subprocess.Popen(cmd, stdin=_run, stdout=_log, stderr=_log, cwd=runs_dir)
    p.wait()
    _run.close()
    _log.close()

    log_fn = _join(runs_dir, f'p{wepp_id}.err')
    with open(log_fn) as fp:
        lines = fp.readlines()
        for L in lines:
            if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in L:
                return True, wepp_id, time() - t0

    raise Exception(f'Error running wepp for wepp_id {wepp_id}\nSee {log_fn}')


def run_flowpath(fp_id, wepp_id, runs_dir, fp_runs_dir, wepp_bin=None, status_channel=None):
    t0 = time()

    if wepp_bin is not None:
        cmd = [os.path.abspath(_join(wepp_bin_dir, wepp_bin))]
    else:
        cmd = [os.path.abspath(_wepp)]

    assert _exists(_join(runs_dir, f'p{wepp_id}.man'))
    assert _exists(_join(fp_runs_dir, f'{fp_id}.slp'))
    assert _exists(_join(runs_dir, f'p{wepp_id}.cli'))
    assert _exists(_join(runs_dir, f'p{wepp_id}.sol'))

    _run = open(_join(fp_runs_dir, f'{fp_id}.run'))
    _log = open(_join(fp_runs_dir, f'{fp_id}.err'), 'w')

    p = subprocess.Popen(cmd, stdin=_run, stdout=_log, stderr=_log, cwd=fp_runs_dir)
    p.wait()
    _run.close()
    _log.close()

    log_fn = _join(fp_runs_dir, f'{fp_id}.err')
    success = False
    with open(log_fn) as fp:
        lines = fp.readlines()
        for L in lines:
            if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in L:
                success = True

    if success:
        #os.remove(_join(fp_runs_dir, f'{fp_id}.slp'))
        os.remove(_join(fp_runs_dir, f'{fp_id}.run'))
        if _exists(_join(fp_runs_dir, f'{fp_id}.loss.dat')):
            os.remove(_join(fp_runs_dir, f'{fp_id}.loss.dat'))
        if _exists(_join(fp_runs_dir, f'{fp_id}.single_event.dat')):
            os.remove(_join(fp_runs_dir, f'{fp_id}.single_event.dat'))
        os.remove(_join(fp_runs_dir, f'{fp_id}.err'))
        return True, fp_id, time() - t0

    raise Exception(f'Error running wepp for {fp_id}\nSee {log_fn}')


def make_watershed_omni_contrasts_run(sim_years, wepp_path_ids, runs_dir):

    block = []
    for wepp_path_id in wepp_path_ids:
        block.append(hillstub_omni_contrasts_template_loader().format(wepp_id_path=wepp_path_id))
    block = ''.join(block)

    _watershed_template = watershed_template_loader()

    s = _watershed_template.format(sub_n=len(wepp_path_ids),
                                   hillslopes_block=block,
                                   sim_years=sim_years)

    fn = _join(runs_dir, 'pw0.run')
    with open(fn, 'w') as fp:
        fp.write(s)

    

def make_watershed_run(sim_years, wepp_ids, runs_dir):

    block = []
    for wepp_id in wepp_ids:
        block.append(hillstub_template_loader().format(wepp_id=wepp_id))
    block = ''.join(block)

    _watershed_template = watershed_template_loader()

    s = _watershed_template.format(sub_n=len(wepp_ids),
                                   hillslopes_block=block,
                                   sim_years=sim_years)

    fn = _join(runs_dir, 'pw0.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_watershed_run(wepp_ids, runs_dir):
    block = []
    for wepp_id in wepp_ids:
        block.append(hillstub_template_loader().format(wepp_id=wepp_id))
    block = ''.join(block)

    _watershed_template = ss_watershed_template_loader()

    s = _watershed_template.format(sub_n=len(wepp_ids),
                                   hillslopes_block=block)

    fn = _join(runs_dir, 'pw0.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_batch_watershed_run(wepp_ids, runs_dir, ss_batch_key, ss_batch_id):
    block = []
    for wepp_id in wepp_ids:
        block.append(hillstub_ss_batch_template_loader().format(wepp_id=wepp_id, ss_batch_key=ss_batch_key))
    block = ''.join(block)

    _watershed_template = ss_batch_watershed_template_loader()

    s = _watershed_template.format(sub_n=len(wepp_ids),
                                   hillslopes_block=block,
                                   ss_batch_id=ss_batch_id,
                                   ss_batch_key=ss_batch_key)

    fn = _join(runs_dir, f'pw0.{ss_batch_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def run_watershed(runs_dir, wepp_bin=None, status_channel=None):
    t0 = time()

    if wepp_bin is not None:
        cmd = [os.path.abspath(os.path.join(wepp_bin_dir, wepp_bin))]
    else:
        cmd = [os.path.abspath(_wepp)]

    _run = open(os.path.join(runs_dir, 'pw0.run'))
    _stderr_fn = os.path.join(runs_dir, 'pw0.err')
    _log = open(_stderr_fn, 'w')

    # for python3.7+ universal_newlines=True -> text=True
    p = subprocess.Popen(cmd, stdin=_run, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         cwd=runs_dir, universal_newlines=True)

    # Streaming the output to _log and, if provided, to the status channel
    while p.poll() is None:
        output = p.stdout.readline()
        output = output.strip()

        if output != '':
            _log.write(output + '\n')
            if status_channel:
                StatusMessenger.publish(status_channel, output)

    _run.close()
    _log.close()

    with open(_stderr_fn) as fp:
        stderr_content = fp.read()
        if 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in stderr_content:
            return True, time() - t0

    raise Exception(f'Error running wepp for watershed \nSee <a href="browse/wepp/runs/pw0.err">{_stderr_fn}</a>')


def run_ss_batch_watershed(runs_dir, wepp_bin=None, ss_batch_id=None, status_channel=None):
    assert ss_batch_id is not None

    t0 = time()

    if wepp_bin is not None:
        cmd = [os.path.abspath(_join(wepp_bin_dir, wepp_bin))]
    else:
        cmd = [os.path.abspath(_wepp)]

    assert _exists(_join(runs_dir, 'pw0.str'))
    assert _exists(_join(runs_dir, 'pw0.chn'))
    assert _exists(_join(runs_dir, 'pw0.imp'))
    assert _exists(_join(runs_dir, 'pw0.man'))
    assert _exists(_join(runs_dir, 'pw0.slp'))
    assert _exists(_join(runs_dir, f'pw0.{ss_batch_id}.cli'))
    assert _exists(_join(runs_dir, 'pw0.sol'))
    assert _exists(_join(runs_dir, f'pw0.{ss_batch_id}.run'))

    _run = open(_join(runs_dir, f'pw0.{ss_batch_id}.run'))
    _stderr_fn = _join(runs_dir, f'pw0.{ss_batch_id}.err')
    _log = open(_stderr_fn, 'w')

    p = subprocess.Popen(cmd, stdin=_run, stdout=_log, stderr=_log, cwd=runs_dir)
    p.wait()
    _run.close()
    _log.close()

    with open(_stderr_fn) as fp:
        stdout = fp.read()
        if 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in stdout:
            return True, time() - t0

    raise Exception('Error running wepp for watershed \nSee <a href="browse/wepp/runs/pw0.err">%s</a>' % _stderr_fn)

