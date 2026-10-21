import pandas as pd, numpy as np, warnings; warnings.filterwarnings("ignore")
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import accuracy_score, f1_score, classification_report
d=pd.read_csv("data/notices_labeled.csv",encoding="utf-8-sig")
d=d.drop_duplicates("title").reset_index(drop=True)
print("중복 제거 후",len(d))
d["body"]=d.body.fillna("")
X={"제목만":d.title,"본문만":d.body.str[:1500],"제목+본문":d.title+" "+d.title+" "+d.body.str[:1500]}
y=d.label
cv=StratifiedKFold(5,shuffle=True,random_state=0)
def mk(): return make_pipeline(TfidfVectorizer(analyzer="char_wb",ngram_range=(2,3),min_df=2,max_features=30000,sublinear_tf=True),
                               LogisticRegression(C=10,max_iter=2000,class_weight="balanced"))
res={}
for k,x in X.items():
    p=cross_val_predict(mk(),x,y,cv=cv); res[k]=p
    print(f"{k:8s} acc={accuracy_score(y,p):.3f} macroF1={f1_score(y,p,average='macro'):.3f}")
p=res["제목+본문"]
print(classification_report(y,p,zero_division=0))
w=d[p!=y]
print("틀린",len(w),"건")
for t,a,b in zip(w.title,w.label,p[p!=y]): print(f" 정답={a} 예측={b} | {t[:55]}")
