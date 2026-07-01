import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.cm import ScalarMappable

NAVY="#1B2559"; CYAN="#22A7B8"; AMBER="#EBA13A"; RED="#C64B4B"
GREYTX="#5B6486"; LIGHT="#EAF3F5"; GRAY="#B8BEC9"
CMAP=plt.get_cmap("RdBu_r"); GAPMAX=3.6
CLASSICAL={"Normal":2.526,"Moderate":5.158,"Severe":7.789}
THEME={"Normal":CYAN,"Moderate":AMBER,"Severe":RED}

DATA={
 "Normal":{"B":[(21,1453.255/60,4.421,24),(23,1243.951/60,2.421,24),(25,652.274/60,2.632,23)],
           "p":[(2,1284.213979/60,2.421,24),(4,2132.13/60,3.833,24),(6,2947.328059/60,4.842,24)],"p_fixedB":23},
 "Moderate":{"B":[(19,1340.505/60,4.000,24),(22,1237.505/60,4.632,24),(25,643.056/60,2.632,23)],
             "p":[(2,1237.505/60,4.632,24),(4,2108.202/60,3.667,24),(6,2940.836/60,8.298,24)],
             "p_fixedB":22},
 "Severe":{"B":[(14,1323.660/60,7.368,24),(16,1323.660/60,5.053,24),(18,1326.258/60,9.474,24),
                (20,1124.312/60,4.211,24),(25,139.406/60,5.263,21)],
           "p":[(2,1326.258/60,9.474,24),(4,2202.059/60,7.579,24),(6,3175.507/60,7.579,24)],
           "p_fixedB":18},
}
OUTDIR=os.environ.get("OUTDIR",".")
os.makedirs(OUTDIR,exist_ok=True)

def style_axes(ax):
    ax.set_facecolor("white")
    for s in ax.spines.values(): s.set_color(NAVY); s.set_linewidth(1.3)
    ax.tick_params(colors=NAVY,labelsize=10)
    ax.grid(True,color="#CBD3E1",linewidth=0.7,alpha=0.7); ax.set_axisbelow(True)

def draw(scenario,axis,points,fixedB=None):
    opt=CLASSICAL[scenario]
    fig,ax=plt.subplots(figsize=(6.4,4.7),dpi=200); style_axes(ax)
    norm=Normalize(vmin=-GAPMAX,vmax=GAPMAX)
    if not points:
        ax.text(0.5,0.5,"p-sweep pending\n(no runs yet)",ha="center",va="center",
                transform=ax.transAxes,fontsize=15,color=GREYTX,style="italic")
        ax.set_ylim(0,60)
        if axis=="p": ax.set_xlim(1,7); ax.set_xticks([2,4,6])
    else:
        xs=[p[0] for p in points]; ys=[p[1] for p in points]
        ax.plot(xs,ys,color=THEME[scenario],linewidth=2.2,alpha=0.55,zorder=1)
        for (x,t,nwwd,q) in points:
            if nwwd is None: fc=GRAY; ec=THEME[scenario]
            else: fc=CMAP(norm(nwwd-opt)); ec=NAVY
            ax.scatter([x],[t],s=170,facecolor=fc,edgecolor=ec,linewidth=1.4,zorder=3)
            lbl=f"{q}q" if nwwd is not None else f"{q}q\nNWWD n/a"
            ax.annotate(lbl,(x,t),textcoords="offset points",xytext=(0,12),
                        ha="center",fontsize=9.5,fontweight="bold",color=NAVY)
        pad=(max(ys)-min(ys))*0.18+1.5
        ax.set_ylim(max(0,min(ys)-pad),max(ys)+pad+2)
    if axis=="B":
        ax.set_xlabel("block size  B  (hm³ per bit)   — smaller = finer",fontsize=11,color=NAVY)
        if points:
            bx=sorted(p[0] for p in points); ax.set_xticks(bx)
            span=max(bx)-min(bx); pad=span*0.16+1.2
            ax.set_xlim(max(bx)+pad,min(bx)-pad)
        else: ax.invert_xaxis()
        sub="runtime vs. block size  (p = 2)"
    else:
        ax.set_xlabel("QAOA depth  p",fontsize=11,color=NAVY)
        sub=f"runtime vs. depth  (B = {fixedB})" if fixedB else "runtime vs. depth"
        if points: ax.set_xticks([p[0] for p in points])
    ax.set_ylabel("runtime  (minutes, total wall)",fontsize=11,color=NAVY)
    ax.set_title(f"{scenario} — {sub}",fontsize=14,fontweight="bold",color=NAVY,pad=10)
    ax.text(0.015,0.975,f"classical NWWD = {opt:.3f}",transform=ax.transAxes,ha="left",va="top",
            fontsize=9,color=GREYTX,bbox=dict(boxstyle="round,pad=0.3",fc=LIGHT,ec=THEME[scenario],lw=1))
    sm=ScalarMappable(norm=norm,cmap=CMAP); sm.set_array([])
    cbar=fig.colorbar(sm,ax=ax,pad=0.02,fraction=0.046)
    cbar.set_label("QAOA NWWD − classical  (↑ more unmet)",fontsize=9,color=NAVY)
    cbar.ax.tick_params(colors=NAVY,labelsize=8); cbar.outline.set_edgecolor(NAVY)
    fig.tight_layout()
    fname=f"runtime_{axis}_{scenario.lower()}.png"
    fig.savefig(os.path.join(OUTDIR,fname),bbox_inches="tight",facecolor="white")
    plt.close(fig); return fname

made=[]
for sc in ("Normal","Moderate","Severe"):
    made.append(draw(sc,"B",DATA[sc]["B"]))
    made.append(draw(sc,"p",DATA[sc]["p"],DATA[sc].get("p_fixedB")))
print("wrote:"," ".join(made))
