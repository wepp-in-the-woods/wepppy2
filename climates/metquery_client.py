# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import requests
from posixpath import join as urljoin

import numpy as np

from all_your_base import c_to_f


_metquery_url = "https://wepp.cloud/webservices/metquery/"


def _metquery_retrieve_monthly(dataset, lng, lat, method):
    global _metquery_url
    query = urljoin(_metquery_url, 'monthly') + \
                    '?lat={lat}&lng={lng}&dataset={dataset}&method={method}'\
                    .format(dataset=dataset, lat=lat, lng=lng, method=method)
    r = requests.get(query)

    if r.status_code != 200:
        raise Exception("Encountered error retrieving from metquery")

    # noinspection PyBroadException
    try:
        _json = r.json()
    except Exception:
        _json = None
    
    if _json is None:
        raise Exception("Cannot parse json from metquery response")
        
    return _json


def get_daymet_prcp_mean(lng, lat, method='cubic', units='mm/day'):
    _json = _metquery_retrieve_monthly('daymet/prcp/mean', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)
        
    if units is not None and 'in' in units.lower():
            vals *= 0.0393701
        
    return vals


def get_daymet_prcp_std(lng, lat, method='cubic', units='mm/day'):
    _json = _metquery_retrieve_monthly('daymet/prcp/std', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)
        
    if units is not None and 'in' in units.lower():
            vals *= 0.0393701
        
    return vals


def get_daymet_prcp_skew(lng, lat, method='cubic', units='mm/day'):
    _json = _metquery_retrieve_monthly('daymet/prcp/skew', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)
        
    if units is not None and 'in' in units.lower():
            vals *= 0.0393701
        
    return vals


def get_daymet_prcp_pww(lng, lat, method='cubic'):
    _json = _metquery_retrieve_monthly('daymet/prcp/pww', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)
        
    return vals


def get_daymet_prcp_pwd(lng, lat, method='cubic'):
    _json = _metquery_retrieve_monthly('daymet/prcp/pwd', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)
        
    return vals


def get_daymet_srld_mean(lng, lat, method='cubic'):
    _json = _metquery_retrieve_monthly('daymet/srld/mean', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)
        
    return vals


def get_prism_monthly_tmean(lng, lat, method='cubic', units='f'):
    _json = _metquery_retrieve_monthly('prism/tmean', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)
    
    if 'f' in units:
        vals = c_to_f(vals)
        
    return vals


def get_prism_monthly_tdmean(lng, lat, method='cubic', units='f'):
    _json = _metquery_retrieve_monthly('prism/tdmean', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)
    
    if 'f' in units:
        vals = c_to_f(vals)
        
    return vals


def get_prism_monthly_tmin(lng, lat, method='cubic', units='c'):
    _json = _metquery_retrieve_monthly('prism/tmin', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)
    
    if units is not None and 'f' in units.lower():
        vals = c_to_f(vals)
        
    return vals


def get_prism_monthly_tmax(lng, lat, method='cubic', units='c'):
    _json = _metquery_retrieve_monthly('prism/tmax', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)
    
    if units is not None and 'f' in units.lower():
        vals = c_to_f(vals)
        
    return vals


def get_prism_monthly_ppt(lng, lat, method='cubic', units=None):
    _json = _metquery_retrieve_monthly('prism/ppt', lng, lat, method)
    
    vals = _json['MonthlyValues']
    assert len(vals) == 12
    
    vals = [(v, float('nan'))[v < 0] for v in vals]
    vals = np.array(vals)
    
    if units is not None and 'in' in units.lower():
            vals *= 0.0393701
        
    if units is not None and 'daily' in units.lower():
            vals /= np.array([31.0, 28.25, 31.0, 30.0, 31.0, 30.0, 
                              31.0, 31.0, 30.0, 31.0, 30.0, 31.0])
    
    return vals


def get_eobs_monthly_tmin(lng, lat, method='cubic', units='c'):
    _json = _metquery_retrieve_monthly('eu/e-obs/tn/mean', lng, lat, method)

    vals = _json['MonthlyValues']
    assert len(vals) == 12

    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)

    if units is not None and 'f' in units.lower():
        vals = c_to_f(vals)

    return vals


def get_eobs_monthly_tmax(lng, lat, method='cubic', units='c'):
    _json = _metquery_retrieve_monthly('eu/e-obs/tx/mean', lng, lat, method)

    vals = _json['MonthlyValues']
    assert len(vals) == 12

    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)

    if units is not None and 'f' in units.lower():
        vals = c_to_f(vals)

    return vals


def get_eobs_monthly_ppt(lng, lat, method='cubic', units=None):
    _json = _metquery_retrieve_monthly('eu/e-obs/rr/mean', lng, lat, method)

    vals = _json['MonthlyValues']
    assert len(vals) == 12

    vals = [(v, float('nan'))[v < 0] for v in vals]
    vals = np.array(vals)

    if units is not None and 'in' in units.lower():
        vals *= 0.0393701

    if units is not None and 'daily' not in units.lower():
        vals *= np.array([31.0, 28.25, 31.0, 30.0, 31.0, 30.0,
                          31.0, 31.0, 30.0, 31.0, 30.0, 31.0])

    return vals


def get_agdc_monthly_tmin(lng, lat, method='cubic', units='c'):
    _json = _metquery_retrieve_monthly('au/agdc/monthlies/tmin', lng, lat, method)

    vals = _json['MonthlyValues']
    assert len(vals) == 12

    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)

    if units is not None and 'f' in units.lower():
        vals = c_to_f(vals)

    return vals


def get_agdc_monthly_tmax(lng, lat, method='cubic', units='c'):
    _json = _metquery_retrieve_monthly('au/agdc/monthlies/tmax', lng, lat, method)

    vals = _json['MonthlyValues']
    assert len(vals) == 12

    vals = [(v, float('nan'))[v < -273.15] for v in vals]
    vals = np.array(vals)

    if units is not None and 'f' in units.lower():
        vals = c_to_f(vals)

    return vals


def get_agdc_monthly_ppt(lng, lat, method='cubic', units=None):
    _json = _metquery_retrieve_monthly('au/agdc/monthlies/rain', lng, lat, method)
    vals = _json['MonthlyValues']
    assert len(vals) == 12

    vals = [(v, float('nan'))[v < 0] for v in vals]
    vals = np.array(vals)

    if units is not None and 'in' in units.lower():
        vals *= 0.0393701

    return vals


def get_daily(dataset, bbox, year=None, dst=None, start_year=None, end_year=None):
    global _metquery_url

    query = urljoin(_metquery_url, 'daily') + \
                    '?bbox={bbox}&dataset={dataset}'\
                    .format(bbox=bbox, dataset=dataset)
    if year is not None:
        query += '&year={year}'.format(year=year)
    if start_year is not None:
        query += '&start_year={start_year}'.format(start_year=start_year)
    if end_year is not None:
        query += '&end_year={end_year}'.format(end_year=end_year)

    r = requests.get(query)

    if r.status_code == 418:
        raise Exception(r.content)
    elif r.status_code != 200:
        raise Exception("Encountered error retrieving from metquery: " + r.content.decode('UTF-8'))

    with open(dst, 'wb') as fp:
        fp.write(r.content)


if __name__ == "__main__":

    import sys
    from pprint import pprint

    get_agdc_monthly_ppt(145.708065032959, -37.772953636729326)
    sys.exit()

    get_daily('daymet/prcp', '-117,39,-116.9,39.1', 1980, 'tests/daymet_prcp_1980_ws.nc4')


    _lng = -115.67
    _lat = 45.27
    pprint(get_prism_monthly_ppt(_lng, _lat, units='dailyin'))
    pprint(get_daymet_prcp_mean(_lng, _lat, units='in'))
    pprint(get_daymet_prcp_std(_lng, _lat, units='in'))
    pprint(get_daymet_prcp_skew(_lng, _lat, units='in'))
    pprint(get_daymet_prcp_pww(_lng, _lat))
    pprint(get_daymet_prcp_pwd(_lng, _lat))
    pprint(get_daymet_srld_mean(_lng, _lat))
