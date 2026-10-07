"""Direct action distillation on the unchanged v2 cross-asset representation."""
import torch
from torch import nn
from modules.transformer_v2.model import CrossAssetTransformer,masked_average,pairwise_rank_loss

class OraclePolicyTransformer(CrossAssetTransformer):
    def __init__(self,features,**kwargs):
        super().__init__(features,**kwargs)
        self.policy=nn.Linear(self.utility.in_features,3)
        self.direction30=nn.Linear(self.utility.in_features,1)
    def forward(self,x,feature_mask,asset_available):
        out=super().forward(x,feature_mask,asset_available)
        out['policy_logits']=self.policy(out['asset_state'])
        out['direction30_logits']=self.direction30(out['asset_state']).squeeze(-1)
        return out

def policy_objective(out,utility,utility_valid,relative,relative_valid,regime,regime_valid,
                     experts,expert_valid,direction_return,direction_valid,gap_scale):
    safe=torch.where(expert_valid[...,None],experts,0.)
    sorted_u=safe.sort(-1).values;best=safe.argmax(-1)
    gap=sorted_u[...,-1]-sorted_u[...,-2]
    weight=(gap/gap_scale).clamp(0.,5.)*expert_valid
    logits=out['policy_logits'];target=best[:,None].expand(logits.shape[:-1])
    ce=torch.nn.functional.cross_entropy(logits.reshape(-1,3),target.reshape(-1),reduction='none').reshape_as(target)
    # Normalize by valid examples, so nearly tied decisions have low gradient.
    primary=masked_average(ce*weight[:,None],expert_valid[:,None].expand_as(ce))
    action_regret=((safe.max(-1).values[...,None]-safe)/gap_scale).clamp(0.,5.)
    expected_regret=(logits.softmax(-1)*action_regret[:,None]).sum(-1)
    regret=masked_average(expected_regret,expert_valid[:,None].expand_as(expected_regret))
    target_u=utility[:,None].expand_as(out['utility']);um=utility_valid[:,None].expand_as(target_u)
    auxiliary=masked_average(torch.nn.functional.smooth_l1_loss(out['utility'],target_u,reduction='none'),um)
    ranks=torch.stack([pairwise_rank_loss(out['relative'][:,pool,:,h],relative[:,:,h],relative_valid[:,:,h]) for pool in range(3) for h in range(3)]).mean()
    direction=(direction_return>0).to(logits.dtype)[:,None].expand_as(out['direction30_logits'])
    dm=(direction_valid&(direction_return!=0))[:,None].expand_as(direction)
    directional=masked_average(torch.nn.functional.binary_cross_entropy_with_logits(out['direction30_logits'],direction,reduction='none'),dm)
    r=regime[:,None].expand_as(out['regime']);rm=regime_valid[:,None].expand_as(r)
    regime_loss=masked_average(torch.nn.functional.smooth_l1_loss(out['regime'],r,reduction='none'),rm)
    return primary+.1*regret+.1*auxiliary+.2*ranks+.1*directional+.1*regime_loss
