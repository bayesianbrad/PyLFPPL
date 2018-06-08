from pysppl.foppl import imports
import numpy as np, pandas as pd, matplotlib.pyplot as plt, seaborn as sns
# sns.set_context('paper')
# sns.set_style('white')
from pyfo.utils.eval_stats import *
import sys

PATH  = sys.path[0]
dir_MwG = PATH + '/hmm_MwG_10000_20180129'
dir_DHMC = PATH + '/data'

num_state = 3
T = 16
n_chain = 4
n_burnin = 8000
n_sample = 2000
n_sample_total = n_sample + n_burnin


### plot param
fontsize = 15
linewidth = 3


### true posterior
true_posterior =   np.array(\
   [[ 0.3775, 0.3092, 0.3133],
   [ 0.0416, 0.4045, 0.5539],
   [ 0.0541, 0.2552, 0.6907],
   [ 0.0455, 0.2301, 0.7244],
   [ 0.1062, 0.1217, 0.7721],
   [ 0.0714, 0.1732, 0.7554],
   [ 0.9300, 0.0001, 0.0699],
   [ 0.4577, 0.0452, 0.4971],
   [ 0.0926, 0.2169, 0.6905],
   [ 0.1014, 0.1359, 0.7626],
   [ 0.0985, 0.1575, 0.744 ],
   [ 0.1781, 0.2198, 0.6022],
   [ 0.0000, 0.9848, 0.0152],
   [ 0.1130, 0.1674, 0.7195],
   [ 0.0557, 0.1848, 0.7595],
   [ 0.2017, 0.0472, 0.7511],
   [ 0.2545, 0.0611, 0.6844]])  # 17 by 3
plt.imshow(true_posterior.transpose(), interpolation='None', aspect=1, cmap='binary')
# plt.savefig()
plt.title('True posterior')
plt.show()

### load DHMC data

samples_DHMC = load_data(n_chain, dir_DHMC, include_burnin_samples=True)  #if true, load all data
thr = 20 #the hand tune burnin

new_columns = dict([['hmm-step.states_'+str(i), i] for i in range(16)])
# x_new  = x.drop(['hmm-step.get-obs-dist.k'], axis=1)
new_columns['hmm-step.get-obs-dist.k'] = 16
samples_DHMC_reorder = samples_DHMC
for i in range(n_chain):
    samples_DHMC_reorder[i].rename(columns=new_columns, inplace=True)
    samples_DHMC_reorder[i] = samples_DHMC_reorder[i][[j for j in range(T + 1)]]
    samples_DHMC_reorder_matrix = samples_DHMC_reorder[i][thr:].as_matrix()
    heatmap_DHMC = samples_heatmap(num_state,T, samples_DHMC_reorder_matrix) # 3 by 17
    plt.imshow(heatmap_DHMC, interpolation='None', aspect=1, cmap='binary')
    # plt.savefig(dir_DHMC+'/chain_4_5000of10000.pdf')
    plt.show()


## load MwG data
samples_MwG = {}
for i in range(n_chain):
    df = pd.read_csv(dir_MwG + '/chain-{}.csv'.format(i), index_col=None, header=0)
    samples_MwG[i] = df.as_matrix() # type, dict{chain number: samples(sample size by T)
#
# heatmap = samples_heatmap(num_state,T,samples_MwG[4][n_burnin:]) # 3 by 17
# plt.imshow(heatmap, interpolation='None', aspect=1, cmap='gray')
# plt.savefig(dir_MwG+'/chain_4_5000of10000.pdf')
# # plt.show()
#
# l2norm_MwG = multi_l2norm_hmm(200, n_sample_total - n_burnin, l2_norm, true_posterior, samples_MwG[4][n_burnin:, :], num_state, T)
# print(l2norm_MwG)
# plt.plot(np.arange(200,n_sample_total-n_burnin+1,200),l2norm_MwG, label='Metropolis-within-Gibbs', linewidth=linewidth)
# plt.xlabel('sample size', fontsize = fontsize)
# plt.ylabel('l2-norm', fontsize = fontsize)
# plt.yticks(size=fontsize)
# plt.xticks(np.arange(200,n_sample_total-n_burnin+1,1000),size=fontsize)
# # plt.legend('Location','southeast')
# plt.legend()
# plt.savefig(PATH+'/l2norm.pdf')