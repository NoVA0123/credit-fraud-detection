import numpy as np
import polars as pl
import duckdb
import matplotlib.pyplot as plt
from sklearn.metrics import r2_score
from scipy.stats import chi2_contingency
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score, classification_report, precision_recall_fscore_support
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
import os
import warnings
warnings.filterwarnings('ignore')


# reading the data
df1 = pl.read_excel('~/Downloads/case_study1.xlsx')
df2 = pl.read_excel('~/Downloads/case_study2.xlsx')
print(df1.describe())
print(df2.describe())


# Storing the orginal data
Originaldf1 = df1.clone()
Originaldf2 = df2.clone()


# removing '-99999' from  oldest TL
# print(df1.shape)
df1 = df1.filter(pl.col('Age_Oldest_TL') != -99999)
# print(df1.shape)


# removing columns if null values (-99999) have occurred more than 10000 times
# print(df2.shape)
ColsToRmv = []
for i in df2.select([pl.col(pl.Int64), pl.col(pl.Float64)]).columns:
    if df2.filter(pl.col(i) == -99999).shape[0] > 10000:
        ColsToRmv.append(i)
# print(ColsToRmv)
df2 = df2.drop(ColsToRmv)
# print(df2.shape)
for i in df2.select([pl.col(pl.Int64), pl.col(pl.Float64)]).columns:
    df2 = df2.filter(pl.col(i) != -99999)
print(df2.shape)

del ColsToRmv
del i


# Joining both dataframes
df = df1.join(df2, how='inner', left_on='PROSPECTID', right_on='PROSPECTID')
print(df[:5])
print(df.shape)


# Checking Null values
# print(df.null_count().sum_horizontal())


# checking contingency of categorical variable with our target variable
CheckCols = df2.select([pl.col(pl.String)]).columns[:-1]
def pivot_creator(Index: str,
                  DataFrame: pl.DataFrame = df) -> list:
    # Pivot the dataframe to show it in cross tabulation form
    CrossTab = DataFrame.pivot(on="Approved_Flag", index=Index, values="Approved_Flag", aggregate_function='count')
    # Remove index and convert it into list
    CrossTab = CrossTab.to_numpy()[:, 1:].tolist()
    return CrossTab

# print(CheckCols)
for i in CheckCols:
    chi2, pval, _, _ = chi2_contingency(pivot_creator(i))

del df1
del df2
del i
del CheckCols


# VIF sequential check
VifData = df.select([pl.col(pl.Int64), pl.col(pl.Float64)])
ColKept = []
ColIndex = 0

for i in VifData.columns[1:]:

    VifValue = variance_inflation_factor(VifData, ColIndex)

    if VifValue <= 6.:
        ColKept.append(i)
        ColIndex = ColIndex + 1

    else:
        VifData = VifData.drop(i)

print(ColKept)

del ColIndex
del VifData
del VifValue


# Checking Anova for columns to be kept
from scipy.stats import f_oneway

GrpDf = df.group_by('Approved_Flag').all()
UniqueItems = GrpDf[:, 'Approved_Flag'].to_list()
FinalColsNum = []
print(UniqueItems)
for i in ColKept:
    GrpPs = {} 
    for NumFlag in range(len(UniqueItems)):
        GrpPs[UniqueItems[NumFlag]] = GrpDf[NumFlag, i].to_list()

    FStatistic, Pval = f_oneway(*GrpPs.values())
    if Pval <= 0.5:
        FinalColsNum.append(i)

del UniqueItems
del GrpDf
del ColKept


# Treating categorical variables
'''print(df['MARITALSTATUS'].unique())
print(df['EDUCATION'].unique())
print(df['GENDER'].unique())
print(df['last_prod_enq2'].unique())
print(df['first_prod_enq2'].unique())'''


Mapper = {'SSC': 1,
          '12TH': 2,
          'GRADUATE': 3,
          'UNDER GRADUATE': 3,
          'POST-GRADUATE': 4,
          'PROFESSIONAL': 3,
          'OTHERS': 1}

df = df.with_columns(pl.col('EDUCATION').replace(Mapper).cast(pl.Int64))

del Mapper


# Creating final df list
FinalFeatures = FinalColsNum + ['MARITALSTATUS', 'EDUCATION', 'GENDER', 'last_prod_enq2', 'first_prod_enq2', 'Approved_Flag']
df = df[:, FinalFeatures]

del FinalFeatures


# One hot encoding
OneHotCols = ['MARITALSTATUS','GENDER', 'last_prod_enq2', 'first_prod_enq2']
df = df.to_dummies(columns=OneHotCols)
print(df)

del OneHotCols


'''Preparing models'''
# Splitting the data
y = df[:, 'Approved_Flag']
x = df.drop('Approved_Flag')

x_train, x_test, y_train, y_test = train_test_split(x,
                                                    y,
                                                    test_size=0.2,
                                                    random_state=1337)

# Random Forest model
print("RANDOM FOREST")
RfClassifier = RandomForestClassifier(n_estimators=200,
                                      random_state=1337)
# Training the data
RfClassifier.fit(x_train, y_train)

# Checking accuracy, recall and precision
y_pred = RfClassifier.predict(x_test)
accuracy = accuracy_score(y_test, y_pred)
print(f'\nAccuracy: {accuracy: .7f}')

precision, recall, F1Score, _ = precision_recall_fscore_support(y_test, y_pred)

for i, v in enumerate(['P1', 'P2', 'P3', 'P4']):
    print(f"Class {v}")
    print(f"Precision: {precision[i]: .7f}")
    print(f"Recall: {recall[i]: .7f}")
    print(f"F1 Score: {F1Score[i]: .7f}")


# Decision Tree
print("\nDECISION TREE")
DtModel = DecisionTreeClassifier(max_depth=20,
                                 min_samples_split=10)
DtModel.fit(x_train, y_train)

y_pred = DtModel.predict(x_test)
print(f'\nAccuracy: {accuracy: .7f}')

precision, recall, F1Score, _ = precision_recall_fscore_support(y_test, y_pred)

for i, v in enumerate(['P1', 'P2', 'P3', 'P4']):
    print(f"Class {v}")
    print(f"Precision: {precision[i]: .7f}")
    print(f"Recall: {recall[i]: .7f}")
    print(f"F1 Score: {F1Score[i]: .7f}")


# Encoding labels for gradient boosters
from sklearn.preprocessing import LabelEncoder

print("\nXTREME GRADIENT BOOSTING")
XgbClassifier = XGBClassifier(objective='multi:softmax',
                              num_class=4,
                              random_state=1337)
LabelEnc = LabelEncoder()
x = x.to_numpy()
y_encoded = LabelEnc.fit_transform(y)

x_train, x_test, y_train, y_test = train_test_split(x,
                                                    y_encoded,
                                                    test_size=0.2,
                                                    random_state=1337)

XgbClassifier.fit(x_train, y_train)
y_pred = XgbClassifier.predict(x_test)

accuracy = accuracy_score(y_test, y_pred)
print(f'\nAccuracy: {accuracy: .7f}')

precision, recall, F1Score, _ = precision_recall_fscore_support(y_test, y_pred)

for i, v in enumerate(['P1', 'P2', 'P3', 'P4']):
    print(f"Class {v}")
    print(f"Precision: {precision[i]: .7f}")
    print(f"Recall: {recall[i]: .7f}")
    print(f"F1 Score: {F1Score[i]: .7f}")


# Catboost classifier
print("\nCATBOOST CLASSIFIER")
CBClassifier = CatBoostClassifier(objective='MultiClass',
                                  random_state=1337,
                                  verbose=False)

CBClassifier.fit(x_train, y_train)
y_pred = CBClassifier.predict(x_test)

accuracy = accuracy_score(y_test, y_pred)
print(f'\nAccuracy: {accuracy: .7f}')

precision, recall, F1Score, _ = precision_recall_fscore_support(y_test, y_pred)

for i, v in enumerate(['P1', 'P2', 'P3', 'P4']):
    print(f"Class {v}")
    print(f"Precision: {precision[i]: .7f}")
    print(f"Recall: {recall[i]: .7f}")
    print(f"F1 Score: {F1Score[i]: .7f}")


# Light GBM Classifier
print("\nLIGHTGBM CLASSIFIER")
LgbmClassifier = LGBMClassifier(objective='multiclass',
                                random_state=1337)

LgbmClassifier.fit(x_train, y_train)
y_pred = LgbmClassifier.predict(x_test)

accuracy = accuracy_score(y_test, y_pred)
print(f'\nAccuracy: {accuracy: .7f}')

precision, recall, F1Score, _ = precision_recall_fscore_support(y_test, y_pred)

for i, v in enumerate(['P1', 'P2', 'P3', 'P4']):
    print(f"Class {v}")
    print(f"Precision: {precision[i]: .7f}")
    print(f"Recall: {recall[i]: .7f}")
    print(f"F1 Score: {F1Score[i]: .7f}")
