"""Observe existing optimization calculations without dispatching model calls."""
from collections import Counter
import json
from pathlib import Path

import numpy as np

from .io import write


def number(value):
    value = float(value)
    return value if np.isfinite(value) else None


def norm(vector):
    scale = float(np.max(np.abs(vector)))
    return number(scale * np.linalg.norm(vector / scale)) if scale else 0.


def cosine(left, right):
    a, b = norm(left), norm(right)
    return number((left / a) @ (right / b)) if a and b else None


def gradient_blocks(gradient, parameter_schema):
    result = {}; offset = 0
    for item in parameter_schema:
        size = int(np.prod(item['shape']))
        block = gradient[offset:offset + size]
        result[item['name']] = dict(parameters=size, l2=norm(block),
                                   maximum=number(np.max(np.abs(block))))
        offset += size
    if offset != gradient.size:
        raise ValueError('diagnostic parameter inventory mismatch')
    return result


class OptimizationDiagnostics:
    """Record rejected rows, step geometry and 32-update saved-value reviews.

    Candidate verdicts describe feasibility/Armijo checks; only the accepted
    checkpoint and step record assert that an optimizer update was committed.
    Every violating row is retained, even when many rows fail together.
    """
    def __init__(self, out, metric, parameter_schema, interval=32):
        self.out = Path(out); self.metric = metric; self.parameter_schema = parameter_schema
        self.ids = list(metric.info['ids']); self.interval = interval
        self.violations = Counter(); self.verdicts = Counter(); self.reviews = []
        self.previous_review = None; self.last_accepted = None
        write(self.out/'diagnostic-rows.json', dict(schema='tmd-diagnostic-rows-v1',
            row_index_base=0, observation_ids=self.ids, fixed_sigma=metric.sigma.tolist(),
            positivity_floor_T_over_sigma=1e-8))

    def append(self, name, record):
        with (self.out/name).open('a') as handle:
            handle.write(json.dumps(record, sort_keys=True, allow_nan=False) + '\n')

    def begin(self, point, counts, prior, elapsed):
        self.previous_review = dict(q=point['q_per_measurement'], counts=dict(counts),
                                    elapsed=elapsed)
        write(self.out/'diagnostic-initial.json', dict(
            schema='tmd-optimization-initial-v1', model_calls=0,
            accepted_updates_before=prior['accepted_updates'],
            preflight_counters=dict(counts), q_per_measurement=point['q_per_measurement'],
            penalized_gradient_max=point['gradient_max'], penalized_gradient_l2=norm(point['gradient']),
            gradient_blocks=gradient_blocks(point['gradient'], self.parameter_schema),
            endpoint_diagnostics=self.metric.describe(point['values'])))

    def step(self, point, direction, history, gdot, fallback, counts, prior, elapsed):
        pairs = [dict(sTy=number(s@y), cosine=cosine(s,y)) for s,y,_ in history]
        gamma = 1.
        if history:
            s,y,_ = history[-1]
            gamma = max(min(float(s@y)/max(float(y@y),1e-300),1e6),1e-12)
        record = dict(schema='tmd-optimization-step-start-v1',
            next_segment_update=counts['accepted_updates']+1,
            next_cumulative_update=prior['accepted_updates']+counts['accepted_updates']+1,
            elapsed_seconds=elapsed, q_per_measurement=point['q_per_measurement'],
            objective=point['objective'], penalized_gradient_max=point['gradient_max'],
            penalized_gradient_l2=norm(point['gradient']), direction_l2=norm(direction),
            directional_derivative=number(gdot), descent_cosine=cosine(-point['gradient'],direction),
            steepest_descent_fallback=fallback, history_pairs=len(history),
            history_curvature=pairs, lbfgs_initial_inverse_hessian_scale=gamma)
        self.append('optimization-steps.ndjson', record)
        return record

    def candidate(self, context, values, score, alpha, attempt, armijo_bound, counts, prior, elapsed):
        with np.errstate(over='ignore', invalid='ignore'):
            ratios = values/self.metric.sigma
        invalid = np.flatnonzero(ratios <= 1e-8)
        minimum = int(np.argmin(ratios))
        verdict = ('infeasible' if score is None else
                   'armijo_passed' if score['objective'] <= armijo_bound else 'armijo_rejected')
        self.verdicts[verdict] += 1
        self.violations.update(map(int, invalid))
        self.append('line-search.ndjson', dict(schema='tmd-line-search-candidate-v1',
            next_segment_update=context['next_segment_update'],
            next_cumulative_update=context['next_cumulative_update'],
            attempt=attempt, alpha=alpha, verdict=verdict, elapsed_seconds=elapsed,
            forwards=counts['forwards'], full_calls=counts['full_calls'],
            cumulative_forwards=prior['forwards']+counts['forwards'],
            cumulative_full_calls=prior['full_calls']+counts['full_calls'],
            counters_sampled_after_candidate_forward=True,
            armijo_bound=number(armijo_bound),
            q_per_measurement=None if score is None else score['q_per_measurement'],
            objective=None if score is None else score['objective'],
            minimum_row_index=minimum, minimum_observation_id=self.ids[minimum],
            minimum_T_over_sigma=number(ratios[minimum]),
            minimum_margin=number(ratios[minimum]-1e-8),
            violating_row_count=len(invalid), violating_row_indices=invalid.tolist(),
            violating_T_over_sigma=[number(ratios[i]) for i in invalid],
            violating_margins=[number(ratios[i]-1e-8) for i in invalid]))

    def accepted(self, before, point, alpha, gdot, counts, prior, elapsed, plateau):
        s = point['theta']-before['theta']; y = point['gradient']-before['gradient']
        sy = float(s@y)
        record = dict(schema='tmd-optimization-accepted-v1',
            accepted_updates=counts['accepted_updates'],
            cumulative_accepted_updates=prior['accepted_updates']+counts['accepted_updates'],
            elapsed_seconds=elapsed, alpha=alpha, parameter_step_l2=norm(s),
            q_per_measurement=point['q_per_measurement'],
            q_improvement=before['q_per_measurement']-point['q_per_measurement'],
            objective=point['objective'], objective_improvement=before['objective']-point['objective'],
            predicted_linear_improvement=number(-alpha*gdot),
            penalized_gradient_max=point['gradient_max'], penalized_gradient_l2=norm(point['gradient']),
            gradient_blocks=gradient_blocks(point['gradient'], self.parameter_schema),
            sTy=number(sy), curvature_cosine=cosine(s,y),
            curvature_pair_retained=sy>1e-12 and bool(np.isfinite(sy)),
            min_T_over_sigma=point['min_T_over_sigma'], plateau=plateau)
        self.append('optimization-accepted.ndjson', record)
        self.last_accepted = record
        if counts['accepted_updates'] % self.interval == 0:
            report = self.review(point,counts,prior,elapsed,plateau)
            name = f"diagnostic-review-{counts['accepted_updates']:04d}.json"
            write(self.out/name, report)
            self.reviews.append(name)
            self.previous_review = dict(q=point['q_per_measurement'], counts=dict(counts), elapsed=elapsed)

    def review(self, point, counts, prior, elapsed, plateau):
        previous = self.previous_review
        delta = {key:counts[key]-previous['counts'][key] for key in counts}
        gain = previous['q']-point['q_per_measurement']
        return dict(schema='tmd-optimization-review-v1', model_calls=0,
            segment_counters=dict(counts),
            trajectory_counters={key:prior[key]+counts[key] for key in counts},
            elapsed_seconds=elapsed, interval_counters=delta,
            interval_elapsed_seconds=elapsed-previous['elapsed'], interval_q_improvement=gain,
            interval_q_improvement_per_100_forwards=None if not delta['forwards'] else 100*gain/delta['forwards'],
            candidate_verdicts=dict(self.verdicts),
            violating_row_counts={self.ids[i]:n for i,n in self.violations.most_common()},
            penalized_gradient_l2=norm(point['gradient']),
            endpoint_diagnostics=self.metric.describe(point['values']), plateau=plateau,
            last_accepted_diagnostics=self.last_accepted)

    def finish(self, point, counts, prior, elapsed, plateau, status, reason):
        report = self.review(point,counts,prior,elapsed,plateau)
        report.update(worker_status=status, stop_reason=reason, review_files=self.reviews,
                      diagnostic_scope='existing forwards, gradients and saved arrays only')
        write(self.out/'diagnostic-summary.json',report)
