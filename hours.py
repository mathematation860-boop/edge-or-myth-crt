from crt import *
import pickle
m1,h1,m5=pickle.load(open('cache.pkl','rb'))
rows=[]; alltr=[]
for sm in ['real','zero']:
    bk=Book(m1,sm)
    for hr in range(24):
        a=classic(m1,h1,bk,hour=hr); s=summary(a); s.update(hour=hr,spread=sm)
        if len(a): s['avg_rr']=round((a.reward_planned/a.risk).median(),2)
        rows.append(s)
        if sm=='real': a['spread']=sm; alltr.append(a)
d=pd.DataFrame(rows); d.to_csv('hours.csv',index=False)
pd.concat(alltr).to_csv('A_allhours.csv.gz',index=False)
print(d[d.spread=='real'][['hour','trades','win_rate','avg_R','total_R','pf','max_dd_R','avg_risk_usd','avg_rr']].to_string(index=False))
print(d[d.spread=='zero'][['hour','trades','win_rate','avg_R','pf']].to_string(index=False))
