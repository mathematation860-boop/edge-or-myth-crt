from crt import *
import pickle
m1,h1,m5=pickle.load(open('cache.pkl','rb'))
h4=bars(m1,240); eH1=ema_trend(h1,200)
for sm in ['real','zero','fixed:0.20','fixed:0.60']:
    bk=Book(m1,sm)
    a=crt_break(h4,bk,tf_h=4,rr=1.0,stop_mode='far'); b=crt_break(h1,bk,hours=[8,9],trend=eH1,tf_h=1,rr=2.0,stop_mode='far')
    c=classic(m1,h1,bk,hour=8)
    print(sm,'| H4 break', summary(a)['avg_R'], summary(a)['pf'],'| H1 NY break', summary(b)['avg_R'], summary(b)['pf'],'| classic NY8', summary(c)['avg_R'], summary(c)['pf'])
    if sm=='real':
        a.to_csv('FIX_H4break.csv',index=False); b.to_csv('FIX_H1NYbreak.csv',index=False); c.to_csv('ORIG_classic_NY8.csv',index=False)
        for nm,t in [('H4',a),('H1NY',b),('orig',c)]:
            y=pd.to_datetime(t.entry_ts).dt.year
            print(nm, t.groupby(y).R.agg(['count','mean','sum']).round(2).T.to_string())
        print('H4 break by range hour (NY):'); print(a.groupby('hour').R.agg(['count','mean']).round(3).T.to_string())
