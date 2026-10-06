import torch
from torch import nn

def causal_mask(length,device=None):
    return torch.triu(torch.ones(length,length,dtype=torch.bool,device=device),diagonal=1)

class CrossAssetTransformer(nn.Module):
    """Shared temporal encoder, followed by attention across the ten named assets.

    Missing numeric slots are computational placeholders paired with feature masks;
    unobserved assets never enter an attention denominator or portfolio allocation.
    Three simultaneous readouts compare CLS, attention pooling and last state.
    The final candidate always averages the three predictions, never selects a pool.
    """
    def __init__(self,features,assets=10,length=256,patch=1,width=128,heads=4):
        super().__init__()
        assert length%patch==0 and width%heads==0
        self.features,self.assets,self.length,self.patch=features,assets,length,patch
        self.projection=nn.Linear(features*2*patch,width)
        self.asset=nn.Parameter(torch.empty(1,assets,width))
        self.position=nn.Parameter(torch.empty(1,length//patch+1,width))
        self.cls=nn.Parameter(torch.empty(1,1,width));self.null=nn.Parameter(torch.empty(1,1,width));self.pool_query=nn.Parameter(torch.empty(width))
        for p in (self.asset,self.position,self.cls,self.null,self.pool_query):nn.init.normal_(p,std=.02)
        def layer():return nn.TransformerEncoderLayer(width,heads,width*2,.1,batch_first=True,norm_first=True)
        self.temporal=nn.TransformerEncoder(layer(),3,enable_nested_tensor=False)
        self.cross=nn.TransformerEncoder(layer(),1,enable_nested_tensor=False)
        self.utility=nn.Linear(width,2);self.relative=nn.Linear(width,3);self.regime=nn.Linear(width,3)
    def forward(self,x,feature_mask,asset_available):
        assert x.ndim==4 and x.shape[1:3]==(self.length,self.assets)
        assert x.shape==feature_mask.shape and asset_available.shape==x.shape[:-1]
        assert torch.isfinite(x[feature_mask]).all()
        b,t,a,f=x.shape;assert f==self.features
        values=torch.where(feature_mask,x,0.)
        z=torch.cat([values,feature_mask.to(x.dtype)],-1).permute(0,2,1,3)
        z=z.reshape(b*a,t//self.patch,self.patch*f*2)
        valid=asset_available.permute(0,2,1).reshape(b*a,t//self.patch,self.patch).any(-1)
        # Append an unmasked CLS slot: even an entirely unobserved asset remains finite.
        z=torch.cat([self.projection(z),self.cls.expand(b*a,1,-1)],1)+self.position
        padding=torch.cat([~valid,torch.zeros(b*a,1,dtype=torch.bool,device=x.device)],1)
        # A causal query in an unobserved prefix otherwise has no valid key and
        # softmax(-inf,...,-inf) is NaN. A learned NULL key is explicitly nonprice.
        z[:,0]=torch.where(valid[:,0,None],z[:,0],self.null[:,0].expand(b*a,-1))
        padding[:,0]=False
        z=self.temporal(z,mask=causal_mask(z.shape[1],x.device),src_key_padding_mask=padding)
        history=z[:,:-1];safe=torch.nan_to_num(history)
        score=(safe*self.pool_query).sum(-1)/safe.shape[-1]**.5
        score=score.masked_fill(~valid,-1e4)
        attention=(score.softmax(-1).unsqueeze(-1)*safe*valid.unsqueeze(-1)).sum(1)
        index=torch.arange(valid.shape[1],device=x.device).expand_as(valid).masked_fill(~valid,-1).max(1).values
        last=safe[torch.arange(b*a,device=x.device),index.clamp_min(0)]
        readouts=torch.stack([z[:,-1],attention,last],1).reshape(b,a,3,-1).permute(0,2,1,3)
        ready=asset_available[:,-1];assert ready.any(1).all(),'No currently observed asset'
        cross=self.cross((readouts+self.asset.unsqueeze(1)).reshape(b*3,a,-1),
                         src_key_padding_mask=(~ready).unsqueeze(1).expand(b,3,a).reshape(b*3,a))
        cross=cross.reshape(b,3,a,-1)
        market=(cross*ready[:,None,:,None]).sum(2)/ready.sum(1)[:,None,None]
        return dict(utility=self.utility(cross),relative=self.relative(cross),regime=self.regime(market),
                    asset_available=ready,market_state=market,asset_state=cross)

def masked_average(values,mask):
    assert values.shape==mask.shape
    return torch.where(mask,values,0.).sum()/mask.sum().clamp_min(1)

def pairwise_rank_loss(scores,future,valid):
    # Equal returns supply no directional ordering; never invent tied pair labels.
    delta=future.unsqueeze(-1)-future.unsqueeze(-2)
    use=valid.unsqueeze(-1)&valid.unsqueeze(-2)&(delta.abs()>1e-9)
    predicted=scores.unsqueeze(-1)-scores.unsqueeze(-2)
    return masked_average(torch.nn.functional.softplus(-delta.sign()*predicted),use)

def objective(output,utility,utility_valid,relative,relative_valid,regime,regime_valid,multitask):
    u=utility[:,None].expand_as(output['utility']);um=utility_valid[:,None].expand_as(u)
    total=masked_average(torch.nn.functional.smooth_l1_loss(output['utility'],u,reduction='none'),um)
    if multitask:
        rank=[]
        for pool in range(3):
            for h in range(3):rank.append(pairwise_rank_loss(output['relative'][:,pool,:,h],relative[:,:,h],relative_valid[:,:,h]))
        r=regime[:,None].expand_as(output['regime']);rm=regime_valid[:,None].expand_as(r)
        total=total+.2*torch.stack(rank).mean()+.1*masked_average(torch.nn.functional.smooth_l1_loss(output['regime'],r,reduction='none'),rm)
    return total
