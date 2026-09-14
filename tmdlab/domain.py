"""Typed numerical-domain failures; not input, hardware or derivative errors.

Only an explicitly registered line-search policy may reject these, and only
while evaluating a proposed candidate's forward values. They remain fatal at
replay, accepted states, derivative evaluations, and in historical policies.
"""


class NumericalDomainError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


CANDIDATE_DOMAIN_POLICY = 'reject-forward-domain-errors-v1'
