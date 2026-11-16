"""Causal recurrent conditional VAE with an explicit sufficient-model-state API.

The hidden state is learned statistical memory, not a validated physiological state.
No future sequence encoder is present. The posterior is training-only.
"""
import torch
from torch import nn


class StateCVAE(nn.Module):
    def __init__(self, features=8, hidden=16, latent=4):
        super().__init__()
        self.features, self.hidden, self.latent = features, hidden, latent
        self.prior = nn.Sequential(nn.Linear(hidden+features+1,32),nn.Tanh(),nn.Linear(32,latent*2))
        self.posterior = nn.Sequential(nn.Linear(hidden+features+2,32),nn.Tanh(),nn.Linear(32,latent*2))
        self.decoder = nn.Sequential(nn.Linear(hidden+features+latent+1,32),nn.Tanh(),nn.Linear(32,2))
        self.memory = nn.GRUCell(features+latent+1,hidden)

    def initial(self, batch):
        p=next(self.parameters())
        return torch.zeros(batch,self.hidden,device=p.device),torch.zeros(batch,1,device=p.device)

    def step(self, x, state, epsilon=None, observed=None):
        """Update one five-minute bin. observed must be None during forecasting."""
        h,last=state; context=torch.cat([h,x,last],-1)
        pm,pl=self.prior(context).chunk(2,-1);pl=pl.clamp(-6,3)
        if observed is None: qm,ql=pm,pl
        else:
            qm,ql=self.posterior(torch.cat([context,observed],-1)).chunk(2,-1);ql=ql.clamp(-6,3)
        if epsilon is None:epsilon=torch.randn_like(qm)
        z=qm+torch.exp(.5*ql)*epsilon
        residual,logsd=self.decoder(torch.cat([context,z],-1)).chunk(2,-1)
        mean=last+residual;logsd=logsd.clamp(-4,2)
        value=mean if observed is None else observed
        new=self.memory(torch.cat([x,value,z],-1),h)
        kl=.5*(pl-ql+(ql.exp()+(qm-pm).square())/pl.exp()-1).sum(-1)
        return mean,logsd,(new,value),kl

    def warm(self,x,y):
        state=self.initial(len(x))
        # Assimilate measured past only, posterior mean to avoid random history noise.
        for k in range(x.shape[1]):
            _,_,state,_=self.step(x[:,k],state,torch.zeros(len(x),self.latent,device=x.device),y[:,k:k+1])
        return state

    def forecast(self,x,state,epsilon):
        values=[]
        for k in range(x.shape[1]):
            m,_,state,_=self.step(x[:,k],state,epsilon[:,k]);values.append(m)
        return torch.stack(values,1),state
