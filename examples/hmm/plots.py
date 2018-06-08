#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Author: Bradley Gram-Hansen
Time created:  22:18
Date created:  03/02/2018

License: MIT
'''

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
plt.figure()
x = pd.read_csv('./data/chain_0_samples_after_burnin.csv', header=0)
new_columns = dict([['hmm-step.states_'+str(i), i] for i in range(16)])
x_new  = x.drop(['hmm-step.get-obs-dist.k'], axis=1)
x_new.rename(columns=new_columns, inplace=True)
x_new = x_new[[i for i in range(16)]]
x_count = x_new.apply(pd.value_counts)
x_count = x_count.fillna(0)
ax = sns.heatmap(x_count, cmap='binary',yticklabels=False)
colorbar = ax.collections[0].colorbar
print(x_count)
colorbar.set_ticks([1666.66, 3333.333 , 5000])
colorbar.set_ticklabels(['1', '2', '3'])
ax.set_xlabel('State')
plt.tight_layout()
plt.show()