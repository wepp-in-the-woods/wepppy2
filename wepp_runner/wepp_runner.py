# Copyright (c) 2016-2025, University of Idaho
# All rights reserved.
#
# Author: Roger Lew (rogerlew@gmail.com)

"""
`wepp_runner` a Python wrapper for running WEPP simulations.

============================================================================

This module provides functions for running WEPP simulations for hillslopes, flowpaths, and watersheds
with continuous, single storm (ss), and batch single storm (ss_batch) climates.

### General workflow for running WEPP simulations:
0. assumes you already have p<wepp_id>.sol, p<wepp_id>.cli, p<wepp_id>.slp, and p<wepp_id>.man
   files in the runs_dir

1. generate the hillslope .run files using one of the `make*_hillslope_run` functions
2. run the hillslope simulations using `run_hillslope`, `run_ss_hillslope`, or `run_ss_batch_hillslope`
3. generate the watershed .run file using one of the `make*_watershed_run` functions
4. run the watershed simulation using `run_watershed` or `run_ss_batch_watershed`

The module is implemented in a manner that allows for parallel execution of the hillslope simulations
using the `concurrent.futures.ThreadPoolExecutor`

### Flowpaths
support for continuous and single storm flowpath simulations
flowpaths are independent from the hillslope/watershed simulations and WEPP does not support watershed 
routing of flowpaths.

### `*_relpath`s for hillslope running functions
wepp.cloud has an Omni functionality that builds scenarios as child projects within a parent.
The `make*_hillslope_run` functions have optional arguments to specify relative paths to the
management, climate, slope, and soil files from the runs_dir. This embeds the relative paths
in the .run files so that wepp can find files from the parent project. This prevents the climates,
and slopes from being copied into each child project.

### `make_watershed_omni_contrasts_run`
This supports mix and matching the hillslope outputs from different sibling and parent projects for
watershed simulations. The `wepp_path_ids` is a list of relative paths to the hillslope pass files
with the wepp_id included (without the .pass.dat). 
  e.g. ['H1', '../../<scenario>/wepp/output/H2', 'H3', 'H4', ...]
"""

import os
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from glob import glob

_IS_WINDOWS = os.name == 'nt'

from time import time

import subprocess

from .status_messenger import StatusMessenger

__all__ = [
    "wepp_bin_dir",
    "linux_wepp_bin_opts",
    "make_flowpath_run",
    "make_ss_flowpath_run",
    "make_hillslope_run",
    "make_ss_hillslope_run",
    "make_ss_batch_hillslope_run",
    "run_ss_batch_hillslope",
    "run_hillslope",
    "run_flowpath",
    "make_watershed_omni_contrasts_run",
    "make_watershed_run",
    "make_ss_watershed_run",
    "make_ss_batch_watershed_run",
    "run_watershed",
    "run_ss_batch_watershed",
]

# rq worker-pool -n 4 run_ss_batch_hillslope run_hillslope run_flowpath run_watershed run_ss_batch_watershed

_thisdir = os.path.dirname(__file__)
_template_dir = _join(_thisdir, "templates")

wepp_bin_dir = os.path.abspath(_join(_thisdir, "bin"))

# this is a list of available linux wepp binaries that can be specified for wepp_bin argument
linux_wepp_bin_opts = glob(_join(wepp_bin_dir, "wepp_*"))
linux_wepp_bin_opts = [_split(p)[1] for p in linux_wepp_bin_opts]
linux_wepp_bin_opts = [p for p in linux_wepp_bin_opts if '.' not in p]
linux_wepp_bin_opts = [p for p in linux_wepp_bin_opts if not p.endswith('_hill')]
linux_wepp_bin_opts.sort()

if _IS_WINDOWS:
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


def _ss_hill_template_loader():
    return _template_loader("ss_hillslope.template")

def _ss_batch_hill_template_loader():
    return _template_loader("ss_batch_hillslope.template")


def _hill_template_loader():
    return _template_loader("hillslope.template")

def _reveg_hill_template_loader():
    return _template_loader("reveg_hillslope.template")


def _ss_flowpath_template_loader():
    return _template_loader("ss_flowpath.template")


def _flowpath_template_loader():
    return _template_loader("flowpath.template")


def _watershed_template_loader():
    return _template_loader("watershed.template")


def _ss_watershed_template_loader():
    return _template_loader("ss_watershed.template")


def _ss_batch_watershed_template_loader():
    return _template_loader("ss_batch_watershed.template")



def _hillstub_omni_contrasts_template_loader():
    return """
M
Y
{wepp_id_path}.pass.dat"""

def _hillstub_template_loader():
    return """
M
Y
../output/H{wepp_id}.pass.dat"""


def _hillstub_ss_batch_template_loader():
    return """
M
Y
../output/{ss_batch_key}/H{wepp_id}.pass.dat"""


def make_flowpath_run(fp, wepp_id, sim_years, fp_runs_dir):
    _fp_template = _flowpath_template_loader()

    s = _fp_template.format(fp=fp,
                            wepp_id=wepp_id,
                            sim_years=sim_years)

    fn = _join(fp_runs_dir, f'{fp}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_flowpath_run(fp, wepp_id, runs_dir):
    _fp_template = _ss_flowpath_template_loader()

    s = _fp_template.format(fp=fp, wepp_id=wepp_id, runs_dir=os.path.abspath(runs_dir))

    fn = _join(runs_dir, f'{fp}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_hillslope_run(wepp_id, sim_years, runs_dir, reveg=True,
                       man_relpath='', cli_relpath='', slp_relpath='', sol_relpath=''):
    
    if man_relpath is not '':
        assert man_relpath.endswith('/'), man_relpath
    if cli_relpath is not '':
        assert cli_relpath.endswith('/'), cli_relpath
    if slp_relpath is not '':
        assert slp_relpath.endswith('/'), slp_relpath
    if sol_relpath is not '':
        assert sol_relpath.endswith('/'), sol_relpath
    
    if reveg:
        _hill_template = _reveg_hill_template_loader()
    else:
        _hill_template = _hill_template_loader()

    s = _hill_template.format(wepp_id=wepp_id,
                              sim_years=sim_years,
                              man_relpath=man_relpath,
                              cli_relpath=cli_relpath,
                              slp_relpath=slp_relpath,
                              sol_relpath=sol_relpath)

    fn = _join(runs_dir, f'p{wepp_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_hillslope_run(wepp_id, runs_dir,
                       man_relpath='', cli_relpath='', slp_relpath='', sol_relpath=''):
    if man_relpath is not '':
        assert man_relpath.endswith('/'), man_relpath
    if cli_relpath is not '':
        assert cli_relpath.endswith('/'), cli_relpath
    if slp_relpath is not '':
        assert slp_relpath.endswith('/'), slp_relpath
    if sol_relpath is not '':
        assert sol_relpath.endswith('/'), sol_relpath

    _hill_template = _ss_hill_template_loader()

    s = _hill_template.format(wepp_id=wepp_id, 
                              man_relpath=man_relpath,
                              cli_relpath=cli_relpath,
                              slp_relpath=slp_relpath,
                              sol_relpath=sol_relpath)

    fn = _join(runs_dir, f'p{wepp_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_batch_hillslope_run(wepp_id, runs_dir, ss_batch_key, ss_batch_id,
                       man_relpath='', cli_relpath='', slp_relpath='', sol_relpath=''):
    if man_relpath is not '':
        assert man_relpath.endswith('/'), man_relpath
    if cli_relpath is not '':
        assert cli_relpath.endswith('/'), cli_relpath
    if slp_relpath is not '':
        assert slp_relpath.endswith('/'), slp_relpath
    if sol_relpath is not '':
        assert sol_relpath.endswith('/'), sol_relpath

    _hill_template = _ss_batch_hill_template_loader()

    s = _hill_template.format(wepp_id=wepp_id,
                              ss_batch_id=ss_batch_id,
                              ss_batch_key=ss_batch_key,
                              man_relpath=man_relpath,
                              cli_relpath=cli_relpath,
                              slp_relpath=slp_relpath,
                              sol_relpath=sol_relpath)

    fn = _join(runs_dir, f'p{wepp_id}.{ss_batch_id}.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def run_ss_batch_hillslope(wepp_id, runs_dir, wepp_bin=None, ss_batch_id=None, status_channel=None, 
                       man_relpath='', cli_relpath='', slp_relpath='', sol_relpath=''):
    if man_relpath is not '':
        assert man_relpath.endswith('/'), man_relpath
    if cli_relpath is not '':
        assert cli_relpath.endswith('/'), cli_relpath
    if slp_relpath is not '':
        assert slp_relpath.endswith('/'), slp_relpath
    if sol_relpath is not '':
        assert sol_relpath.endswith('/'), sol_relpath

    assert ss_batch_id is not None
    t0 = time()

    if wepp_bin is not None:
        if _exists(os.path.abspath(_join(wepp_bin_dir, f'{wepp_bin}_hill'))):
            cmd = [os.path.abspath(_join(wepp_bin_dir, f'{wepp_bin}_hill'))]
        else:
            cmd = [os.path.abspath(_join(wepp_bin_dir, wepp_bin))]
    else:
        cmd = [os.path.abspath(_wepp)]

    assert _exists(_join(runs_dir, man_relpath, f'p{wepp_id}.man'))
    assert _exists(_join(runs_dir, slp_relpath, f'p{wepp_id}.slp'))
    assert _exists(_join(runs_dir, cli_relpath, f'p{wepp_id}.{ss_batch_id}.cli'))
    assert _exists(_join(runs_dir, sol_relpath, f'p{wepp_id}.sol'))

    _stderr_fn = _join(runs_dir, f'p{wepp_id}.{ss_batch_id}.err')
    _run = open(_join(runs_dir, f'p{wepp_id}.{ss_batch_id}.run'))
    _log = open(_stderr_fn, 'w')
    success = False

    try:
        p = subprocess.Popen(
            cmd,
            stdin=_run,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=runs_dir,
            universal_newlines=True,
        )

        while True:
            output = p.stdout.readline()
            if output == '' and p.poll() is not None:
                break

            output = output.strip()
            if output:
                if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in output:
                    success = True
                _log.write(output + '\n')
                _log.flush()

        p.wait()
        if p.stdout is not None:
            p.stdout.close()
    finally:
        _run.close()
        _log.close()

    if success:
        return True, wepp_id, time() - t0

    raise Exception('Error running wepp for wepp_id %i\nSee %s'
                    % (wepp_id, _stderr_fn))


def run_hillslope(wepp_id, runs_dir, wepp_bin=None, status_channel=None,
                  man_relpath='', cli_relpath='', slp_relpath='', sol_relpath=''):
    if man_relpath is not '':
        assert man_relpath.endswith('/'), man_relpath
    if cli_relpath is not '':
        assert cli_relpath.endswith('/'), cli_relpath
    if slp_relpath is not '':
        assert slp_relpath.endswith('/'), slp_relpath
    if sol_relpath is not '':
        assert sol_relpath.endswith('/'), sol_relpath

    t0 = time()

    if wepp_bin is not None:
        if _exists(os.path.abspath(_join(wepp_bin_dir, f'{wepp_bin}_hill'))):
            cmd = [os.path.abspath(_join(wepp_bin_dir, f'{wepp_bin}_hill'))]
        else:
            cmd = [os.path.abspath(_join(wepp_bin_dir, wepp_bin))]
    else:
        cmd = [os.path.abspath(_wepp)]

    assert _exists(_join(runs_dir, f'p{wepp_id}.man'))
    assert _exists(_join(runs_dir, f'p{wepp_id}.sol'))

    assert _exists(_join(runs_dir, man_relpath, f'p{wepp_id}.man'))
    assert _exists(_join(runs_dir, slp_relpath, f'p{wepp_id}.slp'))
    assert _exists(_join(runs_dir, cli_relpath, f'p{wepp_id}.cli'))
    assert _exists(_join(runs_dir, sol_relpath, f'p{wepp_id}.sol'))

    _stderr_fn = _join(runs_dir, f'p{wepp_id}.err')
    _run = open(_join(runs_dir, f'p{wepp_id}.run'))
    _log = open(_stderr_fn, 'w')
    success = False

    try:
        p = subprocess.Popen(
            cmd,
            stdin=_run,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=runs_dir,
            universal_newlines=True,
        )

        while True:
            output = p.stdout.readline()
            if output == '' and p.poll() is not None:
                break

            output = output.strip()
            if output:
                if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in output:
                    success = True
                _log.write(output + '\n')
                _log.flush()

        p.wait()
        if p.stdout is not None:
            p.stdout.close()
    finally:
        _run.close()
        _log.close()

    if success:
        return True, wepp_id, time() - t0

    raise Exception(f'Error running wepp for wepp_id {wepp_id}\nSee {_stderr_fn}')


def run_flowpath(fp_id, wepp_id, runs_dir, fp_runs_dir, wepp_bin=None, status_channel=None):
    t0 = time()

    if wepp_bin is not None:
        if _exists(os.path.abspath(_join(wepp_bin_dir, f'{wepp_bin}_hill'))):
            cmd = [os.path.abspath(_join(wepp_bin_dir, f'{wepp_bin}_hill'))]
        else:
            cmd = [os.path.abspath(_join(wepp_bin_dir, wepp_bin))]
    else:
        cmd = [os.path.abspath(_wepp)]

    assert _exists(_join(runs_dir, f'p{wepp_id}.man'))
    assert _exists(_join(fp_runs_dir, f'{fp_id}.slp'))
    assert _exists(_join(runs_dir, f'p{wepp_id}.cli'))
    assert _exists(_join(runs_dir, f'p{wepp_id}.sol'))

    _stderr_fn = _join(fp_runs_dir, f'{fp_id}.err')
    _run = open(_join(fp_runs_dir, f'{fp_id}.run'))
    _log = open(_stderr_fn, 'w')
    success = False

    try:
        p = subprocess.Popen(
            cmd,
            stdin=_run,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=fp_runs_dir,
            universal_newlines=True,
        )

        while True:
            output = p.stdout.readline()
            if output == '' and p.poll() is not None:
                break

            output = output.strip()
            if output:
                if 'WEPP COMPLETED HILLSLOPE SIMULATION SUCCESSFULLY' in output:
                    success = True
                _log.write(output + '\n')
                _log.flush()

        p.wait()
        if p.stdout is not None:
            p.stdout.close()
    finally:
        _run.close()
        _log.close()

    if success:
        #os.remove(_join(fp_runs_dir, f'{fp_id}.slp'))
        os.remove(_join(fp_runs_dir, f'{fp_id}.run'))
        if _exists(_join(fp_runs_dir, f'{fp_id}.loss.dat')):
            os.remove(_join(fp_runs_dir, f'{fp_id}.loss.dat'))
        if _exists(_join(fp_runs_dir, f'{fp_id}.single_event.dat')):
            os.remove(_join(fp_runs_dir, f'{fp_id}.single_event.dat'))
        os.remove(_stderr_fn)
        return True, fp_id, time() - t0

    raise Exception(f'Error running wepp for {fp_id}\nSee {_stderr_fn}')


def make_watershed_omni_contrasts_run(sim_years, wepp_path_ids, runs_dir):

    block = []
    for wepp_path_id in wepp_path_ids:
        block.append(_hillstub_omni_contrasts_template_loader().format(wepp_id_path=wepp_path_id))
    block = ''.join(block)

    _watershed_template = _watershed_template_loader()

    s = _watershed_template.format(sub_n=len(wepp_path_ids),
                                   hillslopes_block=block,
                                   sim_years=sim_years)

    fn = _join(runs_dir, 'pw0.run')
    with open(fn, 'w') as fp:
        fp.write(s)

    

def make_watershed_run(sim_years, wepp_ids, runs_dir):

    block = []
    for wepp_id in wepp_ids:
        block.append(_hillstub_template_loader().format(wepp_id=wepp_id))
    block = ''.join(block)

    _watershed_template = _watershed_template_loader()

    s = _watershed_template.format(sub_n=len(wepp_ids),
                                   hillslopes_block=block,
                                   sim_years=sim_years)

    fn = _join(runs_dir, 'pw0.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_watershed_run(wepp_ids, runs_dir):
    block = []
    for wepp_id in wepp_ids:
        block.append(_hillstub_template_loader().format(wepp_id=wepp_id))
    block = ''.join(block)

    _watershed_template = _ss_watershed_template_loader()

    s = _watershed_template.format(sub_n=len(wepp_ids),
                                   hillslopes_block=block)

    fn = _join(runs_dir, 'pw0.run')
    with open(fn, 'w') as fp:
        fp.write(s)


def make_ss_batch_watershed_run(wepp_ids, runs_dir, ss_batch_key, ss_batch_id):
    block = []
    for wepp_id in wepp_ids:
        block.append(_hillstub_ss_batch_template_loader().format(wepp_id=wepp_id, ss_batch_key=ss_batch_key))
    block = ''.join(block)

    _watershed_template = _ss_batch_watershed_template_loader()

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
    success = False
    while p.poll() is None:
        output = p.stdout.readline()
        output = output.strip()

        if output != '':
            if 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in output:
                success = True
            _log.write(output + '\n')
            if status_channel:
                StatusMessenger.publish(status_channel, output)

    _run.close()
    _log.close()

    if success:
        return True, time() - t0

    # need to identify if _pup project to set the correct browse link
    runs_dir = os.path.abspath(runs_dir)
    _runs_dir = runs_dir.split(os.sep)
    try:
        rel_path = _runs_dir[_runs_dir.index('_pups'):]
        href = 'browse/' + '/'.join(rel_path) + '/pw0.err'
    except:
        href = 'browse/wepp/runs/pw0.err'
    raise Exception(f'Error running wepp for watershed \nSee <a href="{href}">{_stderr_fn}</a>')


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

    _stderr_fn = _join(runs_dir, f'pw0.{ss_batch_id}.err')
    _run = open(_join(runs_dir, f'pw0.{ss_batch_id}.run'))
    _log = open(_stderr_fn, 'w')
    success = False

    try:
        p = subprocess.Popen(
            cmd,
            stdin=_run,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=runs_dir,
            universal_newlines=True,
        )

        while True:
            output = p.stdout.readline()
            if output == '' and p.poll() is not None:
                break

            output = output.strip()
            if output:
                if 'WEPP COMPLETED WATERSHED SIMULATION SUCCESSFULLY' in output:
                    success = True
                _log.write(output + '\n')
                _log.flush()

        p.wait()
        if p.stdout is not None:
            p.stdout.close()
    finally:
        _run.close()
        _log.close()

    if success:
        return True, time() - t0

    runs_dir = os.path.abspath(runs_dir)
    _runs_dir = runs_dir.split(os.sep)
    try:
        rel_path = _runs_dir[_runs_dir.index('_pups'):]
        href = 'browse/' + '/'.join(rel_path) + '/pw0.err'
    except:
        href = 'browse/wepp/runs/pw0.err'
    raise Exception(f'Error running wepp for watershed \nSee <a href="{href}">{_stderr_fn}</a>')
