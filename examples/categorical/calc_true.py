#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  15:50
Date created:  20/02/2018

License: MIT
'''

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
df = pd.read_csv('data1'
                 '/dhmc_chain_0_samples_after_burnin.csv')
col = list(df)

z = [0,1,2]
for i in z:
    for j in range(len(col)):
        score_lt1 = df[col[j]] == i
        sum_of = score_lt1.sum()
        exp_1 = sum_of/len(df[col[j]])
        print('The expected value of {0} is {1} for {2}'.format(i, exp_1, col[j]))
