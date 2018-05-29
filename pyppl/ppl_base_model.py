#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  18:51
Date created:  19/03/2018

License: MIT
'''

from abc import ABC, abstractmethod, ABCMeta


class base_model(ABC):

    @abstractmethod
    def get_vertices(self):
        '''
        Generates the vertices of the graphical model.
        :return: Set of vertices
        '''
        return NotImplementedError

    @abstractmethod
    def get_vertices_names(self):
        return NotImplementedError

    @abstractmethod
    def get_arcs(self):
        return NotImplementedError

    @abstractmethod
    def get_arcs_names(self):
        return NotImplementedError

    @abstractmethod
    def get_conditions(self):
        return NotImplementedError

    @abstractmethod
    def gen_cond_vars(self):
        return NotImplementedError

    @abstractmethod
    def gen_if_vars(self):
        return NotImplementedError

    @abstractmethod
    def gen_cont_vars(self):
        return NotImplementedError

    @abstractmethod
    def gen_disc_vars(self):
        return NotImplementedError

    @abstractmethod
    def get_vars(self):
        return NotImplementedError

    @abstractmethod
    def gen_log_pdf(self):
        return NotImplementedError

    @abstractmethod
    def gen_log_pdf_transformed(self):
        return NotImplementedError

    @abstractmethod
    def gen_prior_samples(self):
        return NotImplementedError