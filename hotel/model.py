import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier, VotingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss, log_loss, f1_score, accuracy_score
from .data import NUM, CAT

class RateBaseline(ClassifierMixin, BaseEstimator):
    def __init__(self, segmented=False):
        self.segmented = segmented
    def fit(self, X, y):
        self.classes_ = np.array([0,1])
        self.rate_ = float(np.mean(y))
        frame = X[['hotel','market_segment']].copy()
        frame['y'] = np.asarray(y)
        g = frame.groupby(['hotel','market_segment']).y.agg(['sum','count'])
        self.rates_ = ((g['sum']+50*self.rate_)/(g['count']+50)).to_dict()
        return self
    def predict_proba(self, X):
        p = np.array([self.rates_.get(tuple(row), self.rate_) for row in X[['hotel','market_segment']].to_numpy()]) if self.segmented else np.full(len(X),self.rate_)
        return np.column_stack([1-p,p])

def candidates():
    def pipe(est):
        pre = ColumnTransformer([
            ('numeric',Pipeline([('impute',SimpleImputer(strategy='median')),('scale',StandardScaler())]),NUM),
            ('category',Pipeline([('impute',SimpleImputer(strategy='most_frequent')),('encode',OneHotEncoder(handle_unknown='ignore',min_frequency=25,sparse_output=False))]),CAT)])
        return Pipeline([('preprocess',pre),('classifier',est)])
    rf = RandomForestClassifier(n_estimators=220,max_depth=24,min_samples_leaf=3,class_weight='balanced_subsample',n_jobs=-1,random_state=42)
    hgb = HistGradientBoostingClassifier(max_iter=220,max_leaf_nodes=31,min_samples_leaf=30,l2_regularization=5.0,learning_rate=0.05,early_stopping=False,random_state=42)
    ensemble = VotingClassifier([('rf',rf),('hgb',hgb)],voting='soft',weights=[2,1])
    return {'Genel oran':RateBaseline(), 'Otel ve kanal oranı':RateBaseline(True),
            'Lojistik regresyon':pipe(LogisticRegression(C=0.5,max_iter=1000,random_state=42)),
            'Rastgele orman':pipe(rf),
            'Gradient boosting':pipe(hgb),
            'Hibrit Topluluk (RF + GBDT)':pipe(ensemble)}

def metrics(y,p):
    y=np.asarray(y); p=np.clip(np.asarray(p),1e-8,1-1e-8)
    pred_bin = (p >= 0.5).astype(int)
    return {'rows':len(y),'events':int(y.sum()),'event_rate':float(y.mean()),
        'accuracy':float(accuracy_score(y, pred_bin)),
        'roc_auc':float(roc_auc_score(y,p)) if len(np.unique(y))>1 else None,
        'average_precision':float(average_precision_score(y,p)) if y.sum() else None,
        'f1':float(f1_score(y, pred_bin, zero_division=0)),
        'brier':float(brier_score_loss(y,p)), 'log_loss':float(log_loss(y,p,labels=[0,1]))}

def queue_metrics(frame,p,k):
    d=frame[['hotel','decision_date','reservation_id','is_canceled']].copy()
    d['p']=p
    # Each property has its own daily capacity. Ties use ID, never outcome.
    d=d.sort_values(['p','reservation_id'],ascending=[False,True],kind='stable')
    selected=d.groupby(['hotel','decision_date'],sort=False).head(k)
    groups=d.groupby(['hotel','decision_date']).is_canceled.agg(['sum','count'])
    expected=float((groups['sum']/groups['count']*groups['count'].clip(upper=k)).sum())
    found=int(selected.is_canceled.sum())
    return {'capacity_per_hotel_day':k,'reviewed':len(selected),'found_events':found,
            'precision':float(selected.is_canceled.mean()),'recall':found/int(d.is_canceled.sum()) if d.is_canceled.sum() else 0,
            'random_expected_events':expected,'lift_over_random':found/expected if expected else None}

def reliability(y,p):
    d=pd.DataFrame({'actual':np.asarray(y),'predicted':p})
    d['bin']=pd.qcut(d.predicted,10,duplicates='drop')
    if d['bin'].isna().all():
        return [{'predicted':float(d.predicted.mean()),'actual':float(d.actual.mean()),'count':len(d)}]
    return d.groupby('bin',observed=True).agg(predicted=('predicted','mean'),actual=('actual','mean'),count=('actual','size')).to_dict('records')
