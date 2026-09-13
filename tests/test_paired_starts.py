import numpy as np
import pytest
import torch

from tmdlab.models import Config, build, flat
from tmdlab.paired_starts import perturb_narrow, paired_width_candidates


def learned():
    model = build(Config(width=8, depth=1), 7)
    generator = torch.Generator().manual_seed(8)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.add_(.01*torch.randn(parameter.shape, generator=generator, dtype=parameter.dtype))
    return model


def check_boundary_pair(narrow, wide):
    for name, count in (("incoming", 10), ("outgoing", 30)):
        b = torch.linspace(0, 6, count*4, dtype=torch.float64, requires_grad=True)
        fraction = torch.linspace(.01, .99, count*4, dtype=torch.float64)
        species = torch.arange(count*4) % count
        old = getattr(narrow, name).log_multiplier(b, fraction, species)
        new = getattr(wide, name).log_multiplier(b, fraction, species)
        assert torch.allclose(old, new, atol=2e-13, rtol=2e-13)
        old_d = torch.autograd.grad(old.sum(), b, retain_graph=True)[0]
        new_d = torch.autograd.grad(new.sum(), b)[0]
        assert torch.allclose(old_d, new_d, atol=2e-13, rtol=2e-13)


def test_each_seed_creates_distinct_common_narrow_and_exact_wide_partners():
    source = learned(); before = flat(source)
    candidates = paired_width_candidates(source, seeds=(101, 102, 103), target_widths=(16, 24), radius=1e-3)
    assert candidates['model_calls'] == 0 and not candidates['feasibility_verified']
    assert np.array_equal(before, flat(source))
    hashes = []
    for seed, entry in candidates['candidates'].items():
        narrow = entry['narrow']; receipt = entry['receipt']; hashes.append(receipt['candidate_parameter_sha256'])
        assert receipt['seed'] == seed and receipt['perturbation_l2'] == pytest.approx(1e-3)
        assert receipt['model_calls'] == 0 and not receipt['feasibility_verified']
        assert not np.array_equal(flat(narrow), before)
        assert receipt['candidate_parameter_sha256'] == __import__('hashlib').sha256(np.ascontiguousarray(flat(narrow), dtype=np.float64).tobytes()).hexdigest()
        for width, partner in entry['partners'].items():
            assert partner['transport']['source_width'] == 8 and partner['transport']['target_width'] == width
            check_boundary_pair(narrow, partner['model'])
            b = torch.linspace(0, 4, 17, dtype=torch.float64)
            assert torch.equal(narrow.cs(b), partner['model'].cs(b))
    assert len(set(hashes)) == 3


def test_reproducible_narrow_seed_and_rejection_of_invalid_candidate_protocol():
    source = learned()
    a, ar = perturb_narrow(source, seed=41, radius=.01)
    b, br = perturb_narrow(source, seed=41, radius=.01)
    assert np.array_equal(flat(a), flat(b)) and ar == br
    for radius in (0, -.01, .2, float('nan')):
        with pytest.raises(ValueError):
            perturb_narrow(source, seed=1, radius=radius)
    for seeds, widths in (((1,), (16,)), ((1, 1), (16,)), ((1, 2), (8,)), ((1, 2), (16, 16))):
        with pytest.raises(ValueError):
            paired_width_candidates(source, seeds=seeds, target_widths=widths, radius=.01)


def test_unrepresentable_displacements_fail_and_complete_candidate_set_is_reproducible():
    source = learned()
    with torch.no_grad():
        for parameter in source.parameters():
            parameter.fill_(1.)
    with pytest.raises(ValueError, match='representable'):
        perturb_narrow(source, seed=1, radius=1e-320)
    with torch.no_grad():
        for parameter in source.parameters():
            parameter.fill_(2.**44)
    with pytest.raises(ValueError, match='representable'):
        perturb_narrow(source, seed=41, radius=.1)
    source = learned()
    a = paired_width_candidates(source, seeds=(9, 10), target_widths=(16, 24), radius=1e-3)
    b = paired_width_candidates(source, seeds=(9, 10), target_widths=(16, 24), radius=1e-3)
    for seed in (9, 10):
        assert np.array_equal(flat(a['candidates'][seed]['narrow']), flat(b['candidates'][seed]['narrow']))
        for width in (16, 24):
            assert np.array_equal(flat(a['candidates'][seed]['partners'][width]['model']), flat(b['candidates'][seed]['partners'][width]['model']))
