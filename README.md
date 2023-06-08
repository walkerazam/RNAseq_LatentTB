# Bioinformatics Project: 
## RNA-Seq Analysis of Latent Tuberculosis CD4 T-Cells and Comparison of Predictive Classifier Models

### Introduction

Latent Tuberculosis Infection (LTBI) is an inactive form of Tuberculosis (TB), wherein the TB bacteria resides within a body in an inactive state, and the patient shows no symptoms. However, this can progress to active TB, specially within people with weakened immune systems. It remains an important challenge to find effective ways to detect and screen for LTBI, as well as develop treatment. 
 
Within the scope of this project, a dataset of Latent TB within Human CD4 T-Cell samples will be used to identify a set of Differentially Expressed Genes (DEG) that can be used in further downstream analysis as genes of interest in treating LTBI. This set of DEGs could be used to inform future research, and find enriched GO pathways. 
Moreover, common machine learning models will be compared to identify effective classifiers in predicting Latent TB. Although there are existing options to test patients for latent TB, an accurate predictive model would be beneficial in drug development and testing, potentially lowering costs associated with checking treatment efficacy.

### Dataset

The dataset is from the GEO database, hosted by the NCBI, from a study by Burel et al., 2018 (GSE99373). The study design performed RNA-sequencing via Illumina HiSeq 2500 on 39 Human subject’s memory CD4 T-Cells. 20 of these subjects had latent TB, whereas 19 were healthy controls. The raw counts included 21,920 genes for these 39 samples, and run metadata was available on the GEO Accession Display.

### Methodology

1. Bulk RNA-Seq - Gene Filtering (Mean-Variance Thresholding), Normalization (PyDESeq2: Median of Ratios), Log Fold Change Cut off and BH-Adjusted P-Values
2. ShinyGO - Finding Enriched KEGG pathways for Differentially Expressed Genes
3. PCA - Finding top genes associated with Principal Components
4. Predictive Modelling - Fitting and comparing Naive Bayes, SVM (Radial), and k-NN (k=2)
5. Decision Boundary - Visualizaing model's boundaries on PCA plots (meshgrid)

### Information

**Repo Tree**
```
.
├── README.md
├── docs
│   ├── Walker Azam_PABIO Final Report.pdf
│   └── Walker Azam_PABIO536 Lightning Talk.pdf
├── environments.yml
├── visualizations
└── src
    ├── Data
    │   ├── GSE99373_RawCounts_CD4.xlsx
    │   ├── LatentTB_DEG.csv
    │   └── meta_GSE99373.csv
    ├── RNAseq_LTBI.ipynb
    └── RNAseq_RawCode.py
```
**Note**: Code was developed and written in Jupyter Notebook. Raw Code form of notebook is also available as .py. To run code, ensure the provided `environments.yml` is used, and that data paths are updated to match local directory set up. 

Files:

1. docs: Contains PDF for project report and slides
2. environments.yml: the conda environment and pip builds for libraries used in the project
3. src/Data: data files used and generated in the project (contains Raw counts, metadata, and list of DEGs)
4. src/RNAseq_LTBI.ipynb: Jupyter Notebook used for RNAseq and ML training/visualizations
5. src/RNAseq_RawCode.py: Copy of Jupyter Notebook as a .py file
