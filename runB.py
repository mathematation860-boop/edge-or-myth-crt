from crt import *
import pickle
m1,h1,m5=pickle.load(open('cache.pkl','rb'))
bk=Book(m1); rows=[]
for st in ['fvg','sweep']:
  for hrs,hn in [(None,'all'),([8,9],'NY8-9')]:
    t=trend_crt(m1,h1,m5,bk,hours=hrs,stop_at=st); s=summary(t); s['cfg']=f'B stop@{st} {hn}'
    if len(t):
        y=pd.to_datetime(t.entry_ts).dt.year; s['IS']=round(t.R[y<=2023].mean(),3); s['OOS']=round(t.R[y>=2024].mean(),3)
        s['be_or_better']=round(100*(t.R>=-0.01).mean(),1)
        t.to_csv(f'B_{st}_{hn}.csv',index=False)
    rows.append(s)
d=pd.DataFrame(rows); d.to_csv('B_summary.csv',index=False); print(d.to_string(index=False))
