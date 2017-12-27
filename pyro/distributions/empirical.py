from __future__ import absolute_import, division, print_function

import numpy as np
import torch
from torch.autograd import Variable

from pyro.distributions.distribution import Distribution
from pyro.distributions.util import copy_docs_from
import pyro.poutine as poutine
import pyro.util as util


def _eq(x, y):
    """
    Equality comparison for nested data structures with tensors.
    """
    if type(x) is not type(y):
        return False
    elif isinstance(x, dict):
        if set(x.keys()) != set(y.keys()):
            return False
        return all(_eq(x_val, y[key]) for key, x_val in x.items())
    elif isinstance(x, (np.ndarray, torch.Tensor)):
        return (x == y).all()
    elif isinstance(x, torch.autograd.Variable):
        return (x.data == y.data).all()
    else:
        return x == y


def _index(seq, value):
    """
    Find position of ``value`` in ``seq`` using ``_eq`` to test equality.
    Returns ``-1`` if ``value`` is not in ``seq``.
    """
    for i, x in enumerate(seq):
        if _eq(x, value):
            return i
    return -1


@copy_docs_from(Distribution)
class Empirical(Distribution):
    """
    Abstract Histogram distribution of equality-comparable values.
    Should only be used inside Marginal.
    """
    enumerable = True

    def __init__(self, values, logits=None, *args, **kwargs):
        super(Empirical, self).__init__(*args, **kwargs)
        self.values = list(values)
        if logits is None:
            logits = torch.zeros(len(self.values))

        if not isinstance(logits, torch.autograd.Variable):
            logits = Variable(logits)
        logprobs = logits - util.log_sum_exp(logits)
        self._categorical = Categorical(logits=logprobs)

    def batch_shape(self, x=None):
        if x is not None:
            raise NotImplementedError
        return torch.Size()

    def event_shape(self):
        return self.values[0].size()

    def sample(self):
        ix = self._categorical.sample().data[0] 
        return self.values[ix]

    def log_pdf(self, x):
        ix = _index(self.values, x)
        return self._categorical.log_pdf(Variable(torch.Tensor([ix])))

    def batch_log_pdf(self, x):
        ix = _index(self.values, x)
        return self._categorical.batch_log_pdf(Variable(torch.Tensor([ix])))

    def enumerate_support(self):
        return self.values[:]

