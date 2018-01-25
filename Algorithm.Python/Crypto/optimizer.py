from __future__ import division
from __future__ import with_statement

import numpy as np
import pprint
import json
import os
import sys

import sklearn
from sklearn.model_selection import ParameterGrid

class Optimizer(object):
    def __init__(self, params_json):
        self.params_json = params_json
        self.params = {}
        self.indicators = []
        self.param_grid = []

        self.parse_params()
        self.gen_param_grid()

    def parse_params(self):
        fh = open(self.params_json, 'r')
        self.params = json.load(fh)

    def gen_param_grid(self):
        if '__GLOBALS__' not in self.params.keys():
            print('ERROR: {} does not have __GLOBALS__ field required \
                    for further processing'.format(self.params_json))
            sys.exit(0)

        self.indicators = self.params['__GLOBALS__']['__INDICATORS__']
        for indicator in self.indicators:
            if indicator not in self.params.keys():
                print('ERROR: {} does not have {} field required for \
                        further processing'.format(self.params_json, indicator))
                sys.exit(0)

        for _global_pgrid_elem in list(ParameterGrid(self.params['__GLOBALS__'])):
            current_indicator = _global_pgrid_elem['__INDICATORS__']
            for _indicator_pgrid_elem in list(ParameterGrid(self.params[current_indicator])):
                config_inst = _global_pgrid_elem.copy()
                config_inst.update(_indicator_pgrid_elem)
                self.param_grid.append(config_inst)

    def run(self):
        pass

    def __repr__(self):
        return json.dumps(self.params)

