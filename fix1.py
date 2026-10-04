from crt import *
import pickle
m1,h1,m5=pickle.load(open('cache.pkl','rb'))
bk=Book(m1)
h4=bars(m1,240); d1=None
rows=[]
def add(name,t):
    s=summary(t); s['cfg']=name
    if len(t):
        y=pd.to_datetime(t.entry_ts).dt.year
        s['IS_avgR']=round(t.R[y<=2023].mean(),3); s['OOS_avgR']=round(t.R[y>=2024].mean(),3)
    rows.append(s)
trH1,_,_=trend_state(h1); trH4,_,_=trend_state(h4)
eH1=ema_trend(h1,200); eH4=ema_trend(h4,200)
# map H4 trend onto H1 bars (last completed H4 bar)
h4end=h4.ts+pd.Timedelta(hours=4)
idx=np.searchsorted(h4end.values, (h1.ts+pd.Timedelta(hours=1)).values, side='right')-1
h4t_on_h1=np.where(idx>=0, eH4[np.clip(idx,0,None)], 0)
for nm,hrs in [('H1 all hours',None),('H1 NY 8-9',[8,9])]:
    add(nm, classic_g(h1,bk,hours=hrs))
    add(nm+' +H1 structure trend', classic_g(h1,bk,hours=hrs,trend=trH1))
    add(nm+' +H1 EMA200 trend', classic_g(h1,bk,hours=hrs,trend=eH1))
    add(nm+' +H4 EMA200 trend', classic_g(h1,bk,hours=hrs,trend=h4t_on_h1))
    add(nm+' +strong close', classic_g(h1,bk,hours=hrs,strong=0.5))
    add(nm+' +H4 trend +strong', classic_g(h1,bk,hours=hrs,trend=h4t_on_h1,strong=0.5))
add('H4 all', classic_g(h4,bk,tf_h=4))
add('H4 +H4 EMA200 trend', classic_g(h4,bk,tf_h=4,trend=eH4))
add('H4 +structure trend', classic_g(h4,bk,tf_h=4,trend=trH4))
add('H4 +strong', classic_g(h4,bk,tf_h=4,strong=0.5))
add('H4 +trend +strong', classic_g(h4,bk,tf_h=4,trend=eH4,strong=0.5))
d=pd.DataFrame(rows); d.to_csv('fix1.csv',index=False)
print(d[['cfg','trades','win_rate','avg_R','total_R','pf','max_dd_R','avg_risk_usd','IS_avgR','OOS_avgR']].to_string(index=False))
