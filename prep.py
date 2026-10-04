from crt import *
import pickle, time
t=time.time(); m1=load_m1(); print(len(m1), m1.ts.min(), m1.ts.max(), time.time()-t)
h1=bars(m1,60); m5=bars(m1,5)
pickle.dump((m1,h1,m5),open('cache.pkl','wb'))
print(len(h1),len(m5), 'spread median', (m1.ask_close-m1.bid_close).median())
