# -*- coding: utf-8 -*-
"""Final Project.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1geSen9EqoeQAq9UMjxpW4ImSmniOWsEK

# Project information

I plan to perform a RNA-Seq study project using a GEO dataset for Latent Tuberculosis CD4 T-Cell response within Human. Here is the link to the accession page: https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE99373. 

The organism is Homo sapiens, and the series accession ID is GSE99373. The data was collected using high throughput sequencing of CD4 T-cells from 20 subjects with latent tuberculosis infection and 19 healthy controls. I will be using the expression profiling counts that represent the transcriptomic response to the disease. 

My project plan is to first perform enrichment analysis & PCA dimensionality reduction (among other analysis), to identify candidate genes that express differential expression between the two conditions ('healthy' and 'Latent tuberculosis infection'). 

The planned steps for analysis:

1. Gene selection and filtering
2. Normalizing Counts
3. Finding differentially expressed genes (Clustering)
4. Dimensionality Reduction

### Set Up

[Ensure that `pip install pydeseq2` is run prior and `pip install umap-learn[plot]`]
"""

import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
import h5py
from umap import UMAP
import scipy 
from scipy import stats
import seaborn as sns
import altair as alt
import scipy.spatial as sp, scipy.cluster.hierarchy as hc

import GEOparse

import  scipy.signal.signaltools

def _centered(arr, newsize):
    # Return the center newsize portion of the array.
    newsize = np.asarray(newsize)
    currsize = np.array(arr.shape)
    startind = (currsize - newsize) // 2
    endind = startind + newsize
    myslice = [slice(startind[k], endind[k]) for k in range(len(endind))]
    return arr[tuple(myslice)]

scipy.signal.signaltools._centered = _centered

from scipy.signal.signaltools import _centered as trim_centered

from pydeseq2.dds import DeseqDataSet
from pydeseq2.ds import DeseqStats

"""## Reading Counts Data and Metadata

The data containing the read counts for the samples will be read, along with some metadata.
"""

# reading in the raw counts data (GSE Accession: GSE99373)
df = pd.read_excel("GSE99373_RawCounts_CD4.xlsx")
# setting it so Genes are columns and rows are samples
df = df.set_index('Transcript_ID').T
df = df.rename_axis(None, axis=1)  # removing Transcipt_ID axis name
df.head()

# seeing the raw count shape
print(df.shape)

"""We can confirm there are 39 samples (19 are healthy, 20 are latent TB). We have 21,920 genes present, which we will be filtering to ideally reduce the number of candidate genes. Prior to this step, we can read some metadata for the runs, including information on which runs are controls or not."""

# # Reading GEO data based on accession
# gse = GEOparse.get_GEO("GSE99373")
# # View metadata associated with the dataset
# meta = gse.phenotype_data
# meta.to_csv('meta_GSE99373.csv', index=False)

# Reading in metadata
meta_df = pd.read_csv('meta_GSE99373.csv')
print(meta_df.shape)
meta_df.head()

"""The metadata has 35 columns! Most are not going to be useful, so I will make a subset to be used. I will include 'title' to match with Sample Title, the 'geo_accession' as an ID, and 'characteristics_ch1.0.disease group' which indicated the treatment groups."""

meta_df.columns
# Making selection
meta_subset = ['title', 'geo_accession', 'characteristics_ch1.0.disease group']
meta = meta_df[meta_subset]
# Renaming characteristics_ch1.0.disease group --> 'disease_group'
meta = meta.rename(columns={'characteristics_ch1.0.disease group':'disease_group'})

# Joining our two datasets
counts = df.copy().reset_index().rename(columns={'index':'title'})
counts = meta.merge(counts)
counts.head()

"""## Gene Filterating

Prior to normalizing our counts, it would be advantageous to identify and select genes that impart the most information. 

From a cursory glance at the counts data, we can see a lot of zeros. Prior to converting to Log2, a small value will be added to avoid -inf errors.
"""

# small value
epsilon = 0.5

# taking log2 values
counts_log2 = np.log2(df + epsilon).clip(lower = np.log2(epsilon))
counts_log2.head()

"""Now that we have the log2 transformed counts, we can try to visualize the distribution of the counts:"""

sns.histplot(counts_log2.values.flatten())
plt.title('Log2 Count Values Distribution')
plt.xlabel('Log2 Counts')
plt.ylabel('Frequency')

#plt.savefig('Log2CountsHistogram.png')

"""The histogram shows us a pretty standard distribution, where most values are -1 (0 reads). To better understand by how much we should filter our data, I will utilize a mean-variance relationship."""

# Finding means per gene
means_per_gene = np.mean(counts_log2, axis=0)
# Calculating variability per gene
var_per_gene = np.sqrt(counts_log2.std())

# Plotting variability against means
fig, ax = plt.subplots(figsize=(8, 6))

# model3 = np.poly1d(np.polyfit(means_per_gene, var_per_gene, 3))
# model4 = np.poly1d(np.polyfit(means_per_gene, var_per_gene, 4))
# polyline = np.linspace(-1, 17.5)
# plt.plot(polyline, model3(polyline), color='blue')
# plt.plot(polyline, model4(polyline), color='orange')

plt.scatter(means_per_gene, var_per_gene, alpha=0.5, s=0.5)
plt.title("Mean-Variance Plot")
plt.xlabel("Mean Log2(counts)")
plt.ylabel("Variance (Std. Dev.)")
plt.axvline(0.5, linestyle='--', color='orange', label='Cut-Off')
plt.legend()
#plt.savefig('MeanVariance.png')
plt.show()

"""We can notice a sharp 'hook' right around the value of 0.5 along the x-axis. This indicates information loss past this point - where there is both low mean and low variance. Likely these genes are mostly undetected or would confer little meaningful in downstream analysis and could then be filtered out.

Using the threshold of 0.5, we can filter out any gene with an average expression below 0.5.
"""

# Finding the mean expression per gene
means_log2 = means_per_gene.to_frame()
# applying filter
to_remove = means_log2 < 0.5
to_remove.columns = ['Log2Count']
# Keeping all False
to_keep = to_remove[~to_remove['Log2Count']]
# Getting list of genes to keep
to_keep = list(to_keep.index)
print(len(to_keep))

"""Applying the 0.5 theshold reduces our number of genes from ~22,000 to 14,419 genes, which is a good reduction but doesn't seem to overreaching."""

# Saving the filtered genes
filtered_df = counts_log2.copy()
filtered_df = filtered_df.loc[:, to_keep]
filtered_df.head()

# Plotting the filtered subset of genes
fig, ax = plt.subplots(figsize=(8, 6))
# Only using filtered_df
plt.scatter(np.mean(filtered_df, axis=0), np.sqrt(filtered_df.std()), alpha=0.5, s=0.5)
plt.title("Mean-Variance Plot (Filtered)")
plt.xlabel("Mean Log2(counts)")
plt.ylabel("Variance (Std. Dev.)")
plt.show()

"""We can see that after applying our filter, there are no genes with low mean and low variance both remaining at the left tail end. Now we can apply normalization to this smaller subset to better control for differences in samples sequence reads. 

DeSeq2 will be used to normalize the expression counts, which utilizes a Median of Ratios normalization methodology.

## Normalization
"""

filtered_counts = counts.loc[:, 'MARCH1':]
filtered_counts = filtered_counts.loc[:, to_keep]
filtered_counts.index = meta['title']  # setting index to be sample title
filtered_counts.shape

filtered_counts.head()

# setting index to be title
meta_copy = meta.copy()
meta_copy.index = meta_copy['title']
meta_copy['condition'] = ['Healthy' if x == 'Healthy' else 'TB' for x in meta_copy['disease_group']]
meta_copy.head()

"""Note, KeyError occurs in `DeseqStats()` when using disease_group likely due to use of space in strings for Latent TB, so a copy column named disease_group was used to bypass this KeyError."""

# Runing the DeSeq2 model fit
dds = DeseqDataSet(counts = filtered_counts, clinical = meta_copy, design_factors = "condition")
dds.deseq2()

# Calculating statistics and showing summary
deseq_stats = DeseqStats(dds, alpha=0.05)
deseq_stats.summary()

results = deseq_stats.results_df
results.isna().sum()  # should I drop these NaN padj values? Can I use the unadjusted pvalues instead?

"""To correct for the NaN values that appear in the adjusted p-value, I manually applied the Benjamin-Hochberg FDR correction. These values will be used to choose for significant genes."""

import statsmodels.stats.multitest as smm
adjusted = smm.multipletests(results['pvalue'], alpha=0.05, method='fdr_bh')

results['bh_adj'] = adjusted[1]
results['bh_adj'].isna().sum()

results

results.sort_values('log2FoldChange', ascending=False)

# plotting ADARB2
plt.scatter(counts['disease_group'], counts['ADARB2'])

plt.plot(counts.groupby('disease_group')['ADARB2'].mean(), 'o', alpha = 0.75, label='ADARB2')
plt.plot(counts.groupby('disease_group')['SCGB3A1'].mean(), 'o', alpha = 0.75, label='SCGB3A1')
plt.title("Comparing mean count for genes")
plt.ylabel("Counts")
plt.legend()
plt.show()

"""A large negative fold change is associated with higher expression in the Healthy cells, whereas a positive fold change implies higher expression in the TB cells. ADARB2 had the most negative log2fold change, and we can see that there is a higher expression in the Healthy cells. This matches with SCGB3A1 which had the largest log2fold change, and has higher expression in Latent TB cells."""

# Plotting the filtered subset of genes
fig, ax = plt.subplots(figsize=(9, 6))
sns.histplot(results['log2FoldChange'])
plt.title("Log2FoldChange for Gene Subset")
#plt.savefig('FoldChangeDistribution.png')

"""Choosing an absolute log change value of 1 would be a good threshold to select for differentially expressed genes. A log2FoldChange of 1 would mean that there is at least a double expression change between the two conditions."""

# Filtering by adj p < 0.05 and log fold-change > 1
diff_exp_genes = results[(results['bh_adj'] < 0.05) & (abs(results['log2FoldChange']) > 1)]
print('Number of genes:', diff_exp_genes.shape[0])

diff_exp_genes

"""After using a threshold of log2 fold change value of 1, and a adjusted p-value of less than 0.05, I have a subset of 96 genes remaining. The next step is then to perform clustering and correlations, followed by PCA. However prior to that, I will use the [ShinyGo](http://bioinformatics.sdstate.edu/go/) tool to identify any signifcantly enriched KEGG pathways when using only our differenially expressed genes."""

# Exporting gene names to a CSV for use in ShinyGo
deg = pd.DataFrame(diff_exp_genes.index)
deg.to_csv("LatentTB_DEG.csv", index=False, header=False)

"""![enriched_pathway.png](attachment:enriched_pathway.png)

There was only one signifcantly enriched pathway from the list of differentially expressed genes identified in the RNASeq pipeline. We can see from ShinyGo that the Acute Myeloid Leukemia pathway had a fold enrichment of 19.3 with a FDR rate of 0.032. Perhaps the selection process was a little too stringent.

Although this pathway is mainly associated with the condition of Acute Myeloid Leukemia, this could imply some crossover in similar genes for Latent Tuberculosis. Potentially testing drugs that have been developed to treat Acute Myeloid Leukemia targetting this pathways could have some therapeutic power for treating latent TB. To get some more details on specific genes driving variance, PCA can be used to identify key genes of interest.

## Clustering

Prior to PCA, I will utilize a clustermap to identify any interesting groupings among the genes I selected
"""

deg = diff_exp_genes.index.tolist()

# Extracting the log2 expression values of only these genes
epsilon = 0.5
log2_deg = np.log2(filtered_counts.loc[:, deg] + epsilon).clip(lower=np.log2(epsilon))

# Renaming samples to include condition
samples_labeled = meta_copy['condition'] + "_" + meta_copy['title']
samples_labeled = samples_labeled.to_list()
log2_deg.index = samples_labeled
log2_deg.head()

# Viewing a clustermap
sns.clustermap(log2_deg.T, cmap = 'coolwarm')
plt.title("Clustermap of Differentially Expressed Genes Log2 Counts", loc='left')
#plt.savefig('Clustergram.png')
plt.show()

"""Figure Observations:

- We see some expected clustering for samples (ie: the healthy samples are generally clustered together vs. TB), however notably some of samples don't do this as cleanly. The sample TU0094 (Healthy) for example clusters more with the Latent TB sampels. Similarly the samples TUO119/146/110 cluster together but seem to fall more closely to the TB samples.
- In terms of genes, we can see that a small group of genes with really high log2 counts cluster together (in red) whereas most genes have medium to lower log2 counts (blue)
- From this clustermap there is a good chance that PCA may be useful in findings clusters of interesting genes

## Principal Component Analysis

I'll perform PCA on the log2counts for the genes of interest as done above
"""

# Creating a copy of the meta dataset for PCA use
meta_pca = meta_copy.copy()
# Dropping redundant info
meta_pca.rename(columns={"title": "sample_title"}, inplace=True)
meta_pca.reset_index(drop=True, inplace=True)
meta_pca = meta_pca.drop('disease_group', axis=1)

# Applying a standard scalar to standardize values
tb_scaled = StandardScaler().fit_transform(log2_deg)

# Applying PCA 
tb_pca = PCA().fit(tb_scaled)
tb_pca_data = tb_pca.transform(tb_scaled)

# Checking the variance explained by first 10 PCs
print(tb_pca.explained_variance_ratio_[:10])

# Plotting to visualize the numbers
explained_variances = tb_pca.explained_variance_ratio_[:10] * 100
explained_variances = np.hstack([np.array([0]), explained_variances]) # Adding a zero
plt.plot(explained_variances.cumsum(), 'o', linestyle='--', alpha = 0.7)

plt.title("Cumulative Variance Explained by Each PC")
plt.ylabel("Percent of Total Variance")
plt.xlabel("Principal Component")
plt.xticks(np.arange(0, 10))
#plt.savefig('PCA_Explained.png')
plt.show()

"""We can see that the first principal component captures by far the most variance (over 1/3 of the total variance in the dataset). From then we see a small gradual plateau, with no sharp jumps. The first 4 PC's capture over 50% of the total variance."""

# Appending of pca data
pca_df = meta_pca.copy()
pca_df['PC1'] = tb_pca_data[:, 0] # Grabbing first column
pca_df['PC2'] = tb_pca_data[:, 1] # Grabbing second column
pca_df['PC3'] = tb_pca_data[:, 2] # Grabbing third column
pca_df['PC4'] = tb_pca_data[:, 3] # Grabbing fourth column

pca_df.head()

# Plotting first two PCs
fig = plt.figure(figsize=[8, 8])
ax = fig.add_subplot(111)

# Plotting PC1 vs PC2
sns.scatterplot(pca_df, x='PC1', y='PC2', hue='condition')

# Setting labels
ax.set_xlabel('PC1 ({0:.2f}%)'.format(tb_pca.explained_variance_ratio_[0]*100))
ax.set_ylabel('PC2 ({0:.2f}%)'.format(tb_pca.explained_variance_ratio_[1]*100))
plt.title("Latent TB (PC1 vs PC2)")
plt.legend(title='Condition')
#plt.savefig('PC1vsPC2.png')
plt.show()

"""Just looking at PC1 and PC2 we can see some differentiation between then healthy and TB samples. We generally can see Healthy samples cluster toegther in the center, wheread the TB samples appear more towards the left side of the plot."""

# plotting the chart pc1 vs pc2
pc_plot = alt.Chart(pca_df, title="PC1 vs PC2 Plot").mark_point().encode(
    x = "PC1",
    y = "PC2",
    color = "condition"
)

# plotting the chart pc2 vs pc3
pc_plot2 = alt.Chart(pca_df, title="PC2 vs PC3 Plot").mark_point().encode(
    x = "PC2",
    y = "PC3",
    color = "condition"
)
# plotting the chart pc3 vs pc4
pc_plot3 = alt.Chart(pca_df, title="PC3 vs PC4 Plot").mark_point().encode(
    x = "PC3",
    y = "PC4",
    color = "condition"
)

(pc_plot | pc_plot2) & pc_plot3

"""Visualizing mutliple PC plots PC1 vs PC2 seemed to have the clearest distinction between Latent TB and Healthy samples. On the PC1 and PC2 plot, I will overlay the genes that contribute most to each direction."""

# Getting PC1 values and multiplying by explained variance
pc1_loading = tb_pca.components_[0, :].T
pc1_weighted_loading = pc1_loading * tb_pca.explained_variance_[0]

# Retrieving gene names
gene_names = deg

# Getting top 5 genes
top_genes_idx = np.argsort(np.abs(pc1_weighted_loading))[-5:]
pc1_top_genes = []
for gene_id in top_genes_idx:
    pc1_top_genes.append(gene_names[gene_id])
    # start at 0,0 (middle)
    ax.annotate(text = gene_names[gene_id], # add gene name
                xy = [0, 0],
                xytext = [tb_pca.components_.T[gene_id, 0] * tb_pca.explained_variance_[0], 
                          tb_pca.components_.T[gene_id, 1] * tb_pca.explained_variance_[1]],
                arrowprops=dict(arrowstyle='<-',linewidth=1, shrinkA=0.9, color='red'), color='red') # add direction
    
# Repeating for pc2
pc2_loading = tb_pca.components_[1, :].T
pc2_weighted_loading = pc2_loading * tb_pca.explained_variance_[1]
top_genes_idx = np.argsort(np.abs(pc2_weighted_loading))[-5:]
pc2_top_genes = []
for gene_id in top_genes_idx:
    pc2_top_genes.append(gene_names[gene_id])
    ax.annotate(text = gene_names[gene_id], # add gene name
                xy = [0, 0],
                xytext = [tb_pca.components_.T[gene_id, 0] * tb_pca.explained_variance_[0], 
                          tb_pca.components_.T[gene_id, 1] * tb_pca.explained_variance_[1]],
                arrowprops=dict(arrowstyle='<-',linewidth=1, shrinkA=0.9, color='green'), color='green') # add direction
#fig.savefig('PC_directions.png')
fig

pc2_top_genes

"""We can see that the top 5 genes that contribute most to PC1 all pull in the same direction (colored in red). For PC2 (colored in green), there is less alignment. The genes that contribute most to PC1 are SLC15A1, TMOD2, and HIST1H1E, HIST1H1C, HIST2H2AC. For PC2 the largest contributing genes are PTGDR2, PABPC3, S100A12, NACA2, HIST1H2BB. 

Since these genes are large contirbutors to observed variance, they would be top candidate genes for further experiments in being early identifiers for latent tubercolosis.

## Disease Predictive Modelling 

Having identified an enriched pathways, and some top genes of interest for further analysis, I want to also start the process of creative predictive models that use the log2 count values of the 96 differentially expressed genes to predict liklihood of a sample being healthy or having latent TB.

Since I am only working with 39 samples, this approach is meant to give a better understanding to what models may be best at predicting chance of disease rather than build a fully robust model. I will utilize cross validation to seperate training and testing data from my 39 samples. Since the dataset is really small and 'wide' (using 39 samples, and 96 columns) I will compare Naive Bayes, SVM, and K-NN which all generally perform better with smaller sample sizes than models such as Neural Networks or Decision Trees.

Although there are existing options to test patients for latent TB, a predicitive model that is accurate in differentiating samples would be beneficial in drug development and testing, potentially lowering costs associated with checking treatments efficacy.
"""

# preparing our dataframes for modelling
X_values = log2_deg.copy() 
labels = meta_pca['condition']

# using 5 fold cross validation
from sklearn.model_selection import cross_validate
from sklearn.model_selection import StratifiedKFold, KFold

# using 5 folds
cv = StratifiedKFold(n_splits=5)

from sklearn.naive_bayes import GaussianNB

nb_score = 0
naivebayes = GaussianNB()
results = cross_validate(naivebayes, X_values.values, labels.values, cv = cv, return_train_score=True)
nb_score = results['test_score'].mean()
print("Average Naive Bayes Test Accuracy:", nb_score)

# Making a NB Model trained on all the data
model_results_df = pd.DataFrame()
model_results_df['nb_test'] = results['test_score']
model_results_df

plt.figure(figsize=[8, 6])
plt.bar(np.arange(1, 6), results['train_score'], alpha = 0.4, label = 'Train Scores')
plt.bar(np.arange(1, 6), results['test_score'], alpha = 0.7, label = 'Test Scores')
plt.title("Naive Bayes Performance (Cross-Validation)")
plt.axhline(nb_score, linestyle='--', label='Average Test Accuracy')
plt.xlabel("CV Iteration")
plt.ylabel("Accuracy")
plt.legend(bbox_to_anchor=(1,1))
#plt.savefig('NB_cv.png')
plt.show()

"""From the cross validation results, Naive Bayes is performing at around 74% test accuracy, which is pretty good. We can see that training scores are much higher typically, showing a slight tendency to over-fit. Lets compare this model to SVM and K-NN:"""

import matplotlib.patches as mpatches
pca = PCA(n_components = 2)
pca.fit(tb_scaled)
pcs = pca.transform(tb_scaled)
X = pcs
h = .02  # step size in the mesh

nb_model = naivebayes.fit(X, labels)


y = [0 if x == 'Healthy' else 1 for x in labels]
# predict the classification probabilities on a grid
x_min, x_max = X[:, 0].min() - 1, X[:, 0].max() + 1
y_min, y_max = X[:, 1].min() - 1, X[:, 1].max() + 1
xx, yy = np.meshgrid(np.arange(x_min, x_max, h),
                     np.arange(y_min, y_max, h))
Z = nb_model.predict(np.c_[xx.ravel(), yy.ravel()])


fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111)
ax.scatter(X[:, 0], X[:, 1], c=y, zorder=2, cmap='coolwarm')
z = Z.reshape(xx.shape)
z = (z == 'Healthy').astype(int)

red_patch = mpatches.Patch(color='maroon', label='Latent TB',
                           alpha=0.75)
blue_patch = mpatches.Patch(color='royalblue', label='Healthy',
                            alpha=0.75)
plt.legend(handles=[red_patch, blue_patch])
plt.pcolormesh(xx, yy, z, cmap='coolwarm_r', alpha = 0.5)

plt.xlabel("PC 1", fontsize = 15)
plt.ylabel("PC 2", fontsize = 15)
plt.title("Latent TB Predictive Naive Bayes Model (PCA)", fontsize = 20)

# Getting top 5 genes
top_genes_idx = np.argsort(np.abs(pc1_weighted_loading))[-5:]
pc1_top_genes = []
for gene_id in top_genes_idx:
    pc1_top_genes.append(gene_names[gene_id])
    # start at 0,0 (middle)
    ax.annotate(text = gene_names[gene_id], # add gene name
                xy = [0, 0],
                xytext = [tb_pca.components_.T[gene_id, 0] * tb_pca.explained_variance_[0], 
                          tb_pca.components_.T[gene_id, 1] * tb_pca.explained_variance_[1]],
                arrowprops=dict(arrowstyle='<-',linewidth=1, shrinkA=0.9, color='black'), color='black') # add direction
    
# Repeating for pc2
pc2_loading = tb_pca.components_[1, :].T
pc2_weighted_loading = pc2_loading * tb_pca.explained_variance_[1]
top_genes_idx = np.argsort(np.abs(pc2_weighted_loading))[-5:]
pc2_top_genes = []
for gene_id in top_genes_idx:
    pc2_top_genes.append(gene_names[gene_id])
    ax.annotate(text = gene_names[gene_id], # add gene name
                xy = [0, 0],
                xytext = [tb_pca.components_.T[gene_id, 0] * tb_pca.explained_variance_[0], 
                          tb_pca.components_.T[gene_id, 1] * tb_pca.explained_variance_[1]],
                arrowprops=dict(arrowstyle='<-',linewidth=1, shrinkA=0.9, color='purple'), color='purple') # add direction
#plt.savefig('NB_pca.png')
plt.show()

from sklearn.svm import SVC

svm_score = 0
svm_model = SVC(kernel='rbf')
results = cross_validate(svm_model, X_values.values, labels.values, cv = cv, return_train_score=True)
svm_score = results['test_score'].mean()
print("Average Naive Bayes Test Accuracy:", svm_score)

model_results_df['svm_test'] = results['test_score']

plt.figure(figsize=[8, 6])
plt.bar(np.arange(1, 6), results['train_score'], alpha = 0.4, label = 'Train Scores')
plt.bar(np.arange(1, 6), results['test_score'], alpha = 0.7, label = 'Test Scores')
plt.title("SVM Performance (Cross-Validation)")
plt.axhline(svm_score, linestyle='--', label='Average Test Accuracy')
plt.xlabel("CV Iteration")
plt.ylabel("Accuracy")
plt.legend(bbox_to_anchor=(1,1))
#plt.savefig('svm_cv.png')
plt.show()

pca = PCA(n_components = 2)
pca.fit(tb_scaled)
pcs = pca.transform(tb_scaled)
X = pcs
h = .02  # step size in the mesh

svm_model = SVC(kernel='rbf')
svm_model = svm_model.fit(X, labels)


y = [0 if x == 'Healthy' else 1 for x in labels]
# predict the classification probabilities on a grid
x_min, x_max = X[:, 0].min() - 1, X[:, 0].max() + 1
y_min, y_max = X[:, 1].min() - 1, X[:, 1].max() + 1
xx, yy = np.meshgrid(np.arange(x_min, x_max, h),
                     np.arange(y_min, y_max, h))
Z = svm_model.predict(np.c_[xx.ravel(), yy.ravel()])


fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111)
ax.scatter(X[:, 0], X[:, 1], c=y, zorder=2, cmap='coolwarm')
z = Z.reshape(xx.shape)
z = (z == 'Healthy').astype(int)

red_patch = mpatches.Patch(color='maroon', label='Latent TB',
                           alpha=0.75)
blue_patch = mpatches.Patch(color='royalblue', label='Healthy',
                            alpha=0.75)
plt.legend(handles=[red_patch, blue_patch])
plt.pcolormesh(xx, yy, z, cmap='coolwarm_r', alpha = 0.5)

plt.xlabel("PC 1", fontsize = 15)
plt.ylabel("PC 2", fontsize = 15)
plt.title("Latent TB Predictive SVM-radial Model (PCA)", fontsize=20)

# Getting top 5 genes
top_genes_idx = np.argsort(np.abs(pc1_weighted_loading))[-5:]
pc1_top_genes = []
for gene_id in top_genes_idx:
    pc1_top_genes.append(gene_names[gene_id])
    # start at 0,0 (middle)
    ax.annotate(text = gene_names[gene_id], # add gene name
                xy = [0, 0],
                xytext = [tb_pca.components_.T[gene_id, 0] * tb_pca.explained_variance_[0], 
                          tb_pca.components_.T[gene_id, 1] * tb_pca.explained_variance_[1]],
                arrowprops=dict(arrowstyle='<-',linewidth=1, shrinkA=0.9, color='black'), color='black') # add direction
    
# Repeating for pc2
pc2_loading = tb_pca.components_[1, :].T
pc2_weighted_loading = pc2_loading * tb_pca.explained_variance_[1]
top_genes_idx = np.argsort(np.abs(pc2_weighted_loading))[-5:]
pc2_top_genes = []
for gene_id in top_genes_idx:
    pc2_top_genes.append(gene_names[gene_id])
    ax.annotate(text = gene_names[gene_id], # add gene name
                xy = [0, 0],
                xytext = [tb_pca.components_.T[gene_id, 0] * tb_pca.explained_variance_[0], 
                          tb_pca.components_.T[gene_id, 1] * tb_pca.explained_variance_[1]],
                arrowprops=dict(arrowstyle='<-',linewidth=1, shrinkA=0.9, color='purple'), color='purple') # add direction
#plt.savefig('svm_pca.png')
plt.show()

from sklearn.neighbors import KNeighborsClassifier

knn = KNeighborsClassifier(n_neighbors=2)
knn_score = 0
results = cross_validate(knn, X_values.values, labels.values, cv = cv, return_train_score=True)
knn_score = results['test_score'].mean()
print("Average Naive Bayes Test Accuracy:", knn_score)

model_results_df['knn_test'] = results['test_score']

plt.figure(figsize=[8, 6])
plt.bar(np.arange(1, 6), results['train_score'], alpha = 0.4, label = 'Train Scores')
plt.bar(np.arange(1, 6), results['test_score'], alpha = 0.7, label = 'Test Scores')
plt.title("KNN Performance (Cross-Validation)")
plt.axhline(knn_score, linestyle='--', label='Average Test Accuracy')
plt.xlabel("CV Iteration")
plt.ylabel("Accuracy")
plt.legend(bbox_to_anchor=(1,1))
#plt.savefig('KNN_cv.png')
plt.show()

pca = PCA(n_components = 2)
pca.fit(tb_scaled)
pcs = pca.transform(tb_scaled)
X = pcs
h = .02  # step size in the mesh

knn = KNeighborsClassifier(n_neighbors=2)
knn_model = knn.fit(X, labels)


y = [0 if x == 'Healthy' else 1 for x in labels]
# predict the classification probabilities on a grid
x_min, x_max = X[:, 0].min() - 1, X[:, 0].max() + 1
y_min, y_max = X[:, 1].min() - 1, X[:, 1].max() + 1
xx, yy = np.meshgrid(np.arange(x_min, x_max, h),
                     np.arange(y_min, y_max, h))
Z = knn_model.predict(np.c_[xx.ravel(), yy.ravel()])


fig = plt.figure(figsize=(10, 10))
ax = fig.add_subplot(111)
ax.scatter(X[:, 0], X[:, 1], c=y, zorder=2, cmap='coolwarm')
z = Z.reshape(xx.shape)
z = (z == 'Healthy').astype(int)

red_patch = mpatches.Patch(color='maroon', label='Latent TB',
                           alpha=0.75)
blue_patch = mpatches.Patch(color='royalblue', label='Healthy',
                            alpha=0.75)
plt.legend(handles=[red_patch, blue_patch])
plt.pcolormesh(xx, yy, z, cmap='coolwarm_r', alpha = 0.5)

plt.xlabel("PC 1", fontsize = 15)
plt.ylabel("PC 2", fontsize = 15)
plt.title("Latent TB Predictive K-NN Model (PCA)", fontsize=20)

# Getting top 5 genes
top_genes_idx = np.argsort(np.abs(pc1_weighted_loading))[-5:]
pc1_top_genes = []
for gene_id in top_genes_idx:
    pc1_top_genes.append(gene_names[gene_id])
    # start at 0,0 (middle)
    ax.annotate(text = gene_names[gene_id], # add gene name
                xy = [0, 0],
                xytext = [tb_pca.components_.T[gene_id, 0] * tb_pca.explained_variance_[0], 
                          tb_pca.components_.T[gene_id, 1] * tb_pca.explained_variance_[1]],
                arrowprops=dict(arrowstyle='<-',linewidth=1, shrinkA=0.9, color='black'), color='black') # add direction
    
# Repeating for pc2
pc2_loading = tb_pca.components_[1, :].T
pc2_weighted_loading = pc2_loading * tb_pca.explained_variance_[1]
top_genes_idx = np.argsort(np.abs(pc2_weighted_loading))[-5:]
pc2_top_genes = []
for gene_id in top_genes_idx:
    pc2_top_genes.append(gene_names[gene_id])
    ax.annotate(text = gene_names[gene_id], # add gene name
                xy = [0, 0],
                xytext = [tb_pca.components_.T[gene_id, 0] * tb_pca.explained_variance_[0], 
                          tb_pca.components_.T[gene_id, 1] * tb_pca.explained_variance_[1]],
                arrowprops=dict(arrowstyle='<-',linewidth=1, shrinkA=0.9, color='purple'), color='purple') # add direction
#plt.savefig('KNN_pca.png')
plt.show()

# Comparing all 3 models performances:

sns.boxplot(data = model_results_df)
plt.ylim(0, 1.05)
plt.ylabel("Test Accuracies")
plt.xticks(np.arange(0, 3), ['Naive Bayes', 'SVM (Radial)', 'K-NN'])
plt.title("Comparing ML Models to Predict Latent TB")
#plt.savefig('model_comparisons.png')

"""**Summary**

Comparing the three different model's predictive abilities given the samples, it is apparent that SVM performed the best. Looking individually at cross-validation results, we see that it has the least tendency to overtrain since the training and test scores were similar. K-NN with 2 neighbors performed the worst, and showed most tendency to over-train. Given the small sample size, I expected K-NN to outperform Naive Bayes and SVM, but it did the worst across the board. Using the PCA plot to observe the decision boundaries, it becomes a little more clear why SVM did the best. Naive Bayes is a linear model and the simple delineation actually works pretty well for most sample points when only considering the differentially expressed genes. SVM's radial kernel adds just a bit more complexity to the decision boundary which actually doesn't 'trust' its trainig data as strictly (see the PCA plot where SVM's boundaries actually misclassify 4 Healthy samples, whereas Naive Bayes only misses 3). However in the context of predicting new cases, this helped SVM since it was likely picking up more of the 'true' signal among the genes by focusing on the support vectors. Finally K-NN, despite having the most complexity in terms of decision boundary, actually did the worst for the same reason as Naive Bayes but to a more extreme extent. It was not picking up a signal among the data values, and just relying on neighbors threw off many TB samples that were close to Healthy ones. 

Ultimately from this small case study, I observe that SVM models may be the most fruitful in terms of actually being predictive model. The 96 selected genes also seemd to perform decently well at differentiating samples by their log2 expressions, with an accuracy score of 84%. Moreover, models such as K-NN may not be appropriate for latent TB predictions since Healthy and non-Healthy samples can often be close together but still have differentiating factors other than distance. 

There are many limitations to this study, and I would treat it as a good starting point to build a stronger model by expanding the small sample size beyond 39. Using the list of 96 differentially expressed genes also is a step that should be taken to reduce the computational load of training models and also reduce the curse of dimensionality. The models I trained where only hyperpramater trained a little to find some optimal priors, but mostly kept at defaults. 
"""
