from crt import *
import pickle, time
m1,h1,m5=pickle.load(open('cache.pkl','rb'))
bk=Book(m1)
t=time.time(); a=classic(m1,h1,bk,hour=8); print('A 08 NY', summary(a), round(time.time()-t,1))
t=time.time(); b=trend_crt(m1,h1,m5,bk); print('B all hours', summary(b), round(time.time()-t,1))
print(b.reason.value_counts().to_dict() if len(b) else '')
a.to_csv('A08.csv',index=False); b.to_csv('B.csv',index=False)
