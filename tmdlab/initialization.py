"""Function-preserving width transport; not an executable trial start route.

New features remain seeded and nonzero, but initially have zero connections
into the retained channels and output head. No depth or physics changes occur.
Every scientific use still needs a registered start and all-row replay proof.
"""
from dataclasses import replace
import torch
from .models import build,schema

def widen(source,width,*,seed):
    cfg=source.config; cfg.validate()
    if type(width) is not int or width<cfg.width:
        raise ValueError('width transport cannot shrink the source')
    if any(p.device.type!='cpu' or p.dtype!=torch.float64 for p in source.parameters()):
        raise ValueError('width transport requires a CPU float64 saved model')
    if any(not torch.isfinite(p).all() for p in source.parameters()):
        raise ValueError('width transport source must be finite')
    target=build(replace(cfg,width=width),seed); old=cfg.width
    with torch.no_grad():
        target.cs.load_state_dict(source.cs.state_dict())
        for name in ('incoming','outgoing'):
            a,b=getattr(source,name),getattr(target,name)
            b.raw_widths.copy_(a.raw_widths)
            for key in ('flavor','condition','delta_width_head'):
                getattr(b,key).load_state_dict(getattr(a,key).state_dict())
            if a.is_outgoing:b.hadron.load_state_dict(a.hadron.state_dict())
            b.radial.weight[:old].copy_(a.radial.weight)
            b.radial.bias[:old].copy_(a.radial.bias)
            for x,y in zip(a.blocks,b.blocks):
                for key in ('linear1','linear2'):
                    src,dst=getattr(x,key),getattr(y,key)
                    dst.weight[:old].zero_()
                    dst.weight[:old,:old].copy_(src.weight)
                    dst.bias[:old].copy_(src.bias)
                # FiLM stores ALL gamma rows before ALL beta rows; a simple
                # top-left copy would silently put old beta in new gamma rows.
                for src_slice,dst_slice in ((slice(0,old),slice(0,old)),
                    (slice(old,2*old),slice(width,width+old))):
                    y.modulation.weight[dst_slice].copy_(x.modulation.weight[src_slice])
                    y.modulation.bias[dst_slice].copy_(x.modulation.bias[src_slice])
            b.shape_head.weight.zero_()
            b.shape_head.weight[:,:old].copy_(a.shape_head.weight)
            b.shape_head.bias.copy_(a.shape_head.bias)
    return target,dict(schema='tmd-width-transport-v1',source_width=old,target_width=width,
        depth=cfg.depth,seed=seed,source_parameters=sum(p.numel() for p in source.parameters()),
        target_parameters=sum(p.numel() for p in target.parameters()),
        target_parameter_schema=schema(target),new_features_seeded=True,
        initial_new_to_retained_connections_zero=True,initial_new_output_weights_zero=True,
        full_observable_replay_required=True,model_calls=0)
