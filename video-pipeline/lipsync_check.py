import numpy as np, sys
s=sys.argv[1]; W,H=48,86
a=np.fromfile(s+r'\gv.raw',np.uint8).reshape(-1,H,W).astype(float); b=np.fromfile(s+r'\sv.raw',np.uint8).reshape(-1,H,W).astype(float)
au=np.fromfile(s+r'\src.raw',np.float32); hop=16000//24; n=len(au)//hop
env=np.sqrt((au[:n*hop].reshape(n,hop)**2).mean(1))
def lag(x,y,rng=10):
    n=min(len(x),len(y)); x=x[:n]-x[:n].mean(); y=y[:n]-y[:n].mean()
    c={L:np.dot(x[max(0,L):n+min(0,L)],y[max(0,-L):n-max(0,L)])/(n-abs(L)) for L in range(-rng,rng+1)}
    L=max(c,key=c.get); y0,y1,y2=c.get(L-1,0),c[L],c.get(L+1,0); den=(y0-2*y1+y2); d=0.5*(y0-y2)/den if den else 0
    return round((L+d)/24*1000)
for name,(r0,r1,c0,c1) in {'lower face':(35,60,22,46),'winston half':(20,86,20,48)}.items():
    ma=np.abs(np.diff(a[:,r0:r1,c0:c1],axis=0)).mean((1,2)); mb=np.abs(np.diff(b[:,r0:r1,c0:c1],axis=0)).mean((1,2))
    print(name,'| src mouth-vs-audio',lag(mb,env[1:]),'ms | gen mouth-vs-audio',lag(ma,env[1:]),'ms')
