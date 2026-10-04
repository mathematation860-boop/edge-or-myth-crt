from crt import *
import pickle
m1,h1,m5=pickle.load(open('cache.pkl','rb'))
bk=Book(m1); h4=bars(m1,240)
eH1=ema_trend(h1,200); eH4=ema_trend(h4,200)
rows=[]
def add(name,t):
    s=summary(t); s['cfg']=name
    if len(t):
        y=pd.to_datetime(t.entry_ts).dt.year
        s['IS']=round(t.R[y<=2023].mean(),3); s['OOS']=round(t.R[y>=2024].mean(),3); s['n_OOS']=int((y>=2024).sum())
    rows.append(s)
for tf,b,tfh,et in [('H1',h1,1,eH1),('H4',h4,4,eH4)]:
  for hrs,hn in ([(None,'all'),([8,9],'NY8-9'),([2,3],'LDN2-3')] if tf=='H1' else [(None,'all')]):
    for sm in ['mid','far']:
      for rr in [1.0,2.0]:
        for tr,tn in [(None,''),(et,' +EMA200')]:
          add(f'BREAK {tf} {hn} stop{sm} rr{rr}{tn}', crt_break(b,bk,hours=hrs,trend=tr,tf_h=tfh,rr=rr,stop_mode=sm))
d=pd.DataFrame(rows); d.to_csv('fix3.csv',index=False)
print(d[['cfg','trades','win_rate','avg_R','total_R','pf','max_dd_R','avg_risk_usd','IS','OOS','n_OOS']].to_string(index=False))
