from crt import *
import pickle
m1,h1,m5=pickle.load(open('cache.pkl','rb'))
h4=bars(m1,240); e4=ema_trend(h4,200); e4_50=ema_trend(h4,50)
bk=Book(m1,'real')
for nm,tr in [('none',None),('ema200',e4),('ema50',e4_50)]:
    a=crt_break(h4,bk,tf_h=4,rr=1.0,stop_mode='far',trend=tr)
    y=pd.to_datetime(a.entry_ts).dt.year
    s=summary(a); print(nm,s, 'IS',round(a[y<=2023].R.mean(),3),'OOS',round(a[y>=2024].R.mean(),3))
    print('  side',a.groupby('side').R.agg(['count','mean']).round(3).to_dict())
    if nm=='ema200': a.to_csv('FIX_H4break_ema200.csv',index=False)
