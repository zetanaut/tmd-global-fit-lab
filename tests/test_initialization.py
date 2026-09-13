import numpy as np
import pytest
import torch
from tmdlab.models import build,Config,flat
from tmdlab.initialization import widen

def learned(width=8,depth=1):
    model=build(Config(width=width,depth=depth),31)
    rng=torch.Generator().manual_seed(93)
    with torch.no_grad():
        for p in model.parameters():p.add_(.03*torch.randn(p.shape,generator=rng,dtype=p.dtype))
    return model

@pytest.mark.parametrize('width',[8,16,24])
@pytest.mark.parametrize('depth',[1,2,3])
def test_width_embedding_preserves_nonzero_boundary_cs_and_b_derivatives(width,depth):
    source=learned(depth=depth); before=flat(source)
    target,proof=widen(source,width,seed=17)
    for name,count in (('incoming',10),('outgoing',30)):
        b=torch.linspace(0,8,count*11,dtype=torch.float64,requires_grad=True)
        fraction=torch.linspace(.001,.99,count*11,dtype=torch.float64)
        species=torch.arange(count*11)%count
        old=getattr(source,name).log_multiplier(b,fraction,species)
        new=getattr(target,name).log_multiplier(b,fraction,species)
        assert torch.allclose(old,new,atol=2e-13,rtol=2e-13)
        g=torch.autograd.grad(old.sum(),b,retain_graph=True)[0]
        h=torch.autograd.grad(new.sum(),b)[0]
        assert torch.allclose(g,h,atol=2e-13,rtol=2e-13)
        assert torch.equal(source.cs(b),target.cs(b))
        assert old[0].item()==new[0].item()==0.
    assert np.array_equal(flat(source),before)
    assert proof['full_observable_replay_required'] and proof['model_calls']==0
    if depth==1:assert proof['target_parameters']=={8:1570,16:2882,24:4706}[width]

def test_new_features_are_seeded_not_dead_and_output_can_learn():
    source=learned(); a,_=widen(source,16,seed=17); b,_=widen(source,16,seed=18)
    assert not torch.equal(a.incoming.radial.weight[8:],b.incoming.radial.weight[8:])
    assert torch.count_nonzero(a.incoming.radial.weight[8:])>0
    assert torch.count_nonzero(a.incoming.shape_head.weight[:,8:])==0
    coordinates=torch.linspace(.1,4,50,dtype=torch.float64)
    loss=a.incoming.log_multiplier(coordinates,torch.full_like(coordinates,.2),torch.arange(50)%10).sum()
    loss.backward()
    assert torch.count_nonzero(a.incoming.shape_head.weight.grad[:,8:])>0
    # Initially insulated feature internals become trainable once output
    # weights move; claiming they already have nonzero gradients would be false.
    assert torch.count_nonzero(a.incoming.radial.weight.grad[8:])==0

def test_width_transport_refuses_shrinking_and_invalid_parameters():
    source=learned()
    for width in (4,8.5,True):
        with pytest.raises(ValueError):widen(source,width,seed=1)
    with torch.no_grad():source.incoming.raw_widths[0]=float('nan')
    with pytest.raises(ValueError,match='finite'):widen(source,16,seed=1)
