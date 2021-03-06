import pytest
import scipy as sp
import numpy as np
import numpy.testing as npt
import jax
from jax import jit, grad, vmap

import split_normal as sn


def test_pdf():
    x = np.linspace(-5., 5., 40)
    params_split_norm = dict(
        loc=0,
        scale_1=1,
        scale_2=1
    )
    params_norm = dict(
        loc=0,
        scale=1
    )
    actual = sn.jax.pdf(x, **params_split_norm)
    expected = sp.stats.norm.pdf(x, **params_norm)
    npt.assert_almost_equal(actual, expected)

    x = np.array([-2., -0.5, 0., 1., 2., 3., 4.])
    params_split_norm = dict(
        loc=1,
        scale_1=1,
        scale_2=2
    )
    actual = sn.jax.pdf(x, **params_split_norm)
    expected = [
        0.00295457,
        0.08634506,
        0.16131382,
        0.26596152,
        0.23471022,
        0.16131382,
        0.08634506
    ]
    npt.assert_almost_equal(actual, expected)


def test_cdf():
    x = np.array([-1.96, 1.96])
    actual = sn.jax.cdf(x, 0, 1, 1)
    expected = [0.025, 0.975]
    npt.assert_almost_equal(actual, expected, decimal=2)

    expected = np.array([-2.43953147, 2.43953147])
    params = dict(
        loc=np.array([-1, 1]),
        scale_1=np.array([1, 2]),
        scale_2=np.array([2, 1])
    )
    p = sn.jax.cdf(expected, **params)
    print(type(p))
    actual = sn.jax.ppf(p, **params)
    npt.assert_almost_equal(actual, expected, decimal=5)


def test_ppf():
    p = np.array([0.025, 0.975])
    actual = sn.jax.ppf(p, 0, 1, 1)
    expected = [-1.96, 1.96]
    npt.assert_almost_equal(actual, expected, decimal=2)

    expected = np.array([0.05, 0.95])
    params = dict(
        loc=np.array([-1, 1]),
        scale_1=np.array([1, 2]),
        scale_2=np.array([2, 1])
    )
    x = sn.jax.ppf(expected, **params)
    actual = sn.jax.cdf(x, **params)
    npt.assert_almost_equal(actual, expected)


def test_invalid_params():
    """
    If it make sense, invalid input values are handled similarly as in Numpy or SciPy.
    Deviations from behaviour of `pdf()`, `cdf()` and `ppf()` in `jax.scipy.stats.norm`:

    * If parameters `scale_1` or `scale_2` are negative, `numpy.nan` is returned as a result.
    """
    x = np.array([1, 1, 1, 1])
    params_split_norm = dict(
        loc=1,
        scale_1=np.array([1, -1, 1, -1]),
        scale_2=np.array([2, 2, -2, -2])
    )

    expected = [0.26596152, np.nan, np.nan, np.nan]
    actual = sn.jax.pdf(x, **params_split_norm)
    npt.assert_almost_equal(actual, expected)

    expected = [0.3333333, np.nan, np.nan, np.nan]
    actual = sn.jax.cdf(x, **params_split_norm)
    npt.assert_almost_equal(actual, expected)

    p = np.array([0.5, 0.5, 0.5, 0.5, 0., 1., -2, 2])
    params_split_norm = dict(
        loc=1,
        scale_1=np.array([1, -1, 1, -1, 1, 1, 1, 1]),
        scale_2=np.array([2, 2, -2, -2, 2, 2, 2, 2])
    )
    expected = [1.6372787, np.nan, np.nan, np.nan, -np.inf, np.inf, np.nan, np.nan]
    actual = sn.jax.ppf(p, **params_split_norm)
    npt.assert_almost_equal(actual, expected)

    # testing behaviour if `None` present (mimicking behaviour of `jax.scipy.stats.norm`)
    x = np.array([1, 1, 1, 1])
    params_split_norm = dict(
        loc=1,
        scale_1=np.array([1, -1, 1, None]),
        scale_2=np.array([2, 2, -2, -2])
    )
    with pytest.raises(Exception) as e:
        _ = sn.jax.pdf(x, **params_split_norm)
    assert str(e.value) == "Dtype object is not supported by JAX"


def test_pdf_grads():
    """
    Tests if PDF function is differentiable.
    """
    x = np.array([-1.96, 0., 1.96])
    params_split_norm = dict(
        loc=0,
        scale_1=1,
        scale_2=1
    )

    # split normal distribution
    grad_sn_pdf = jit(grad(sn.jax.pdf, argnums=(0, )), static_argnums=(1, 2, 3))
    batched_grad_sn_pdf = vmap(grad_sn_pdf, in_axes=(0, None, None, None))
    x_sn_grads = batched_grad_sn_pdf(x, params_split_norm['loc'], params_split_norm['scale_1'], params_split_norm['scale_2'])

    # normal distribution
    grad_n_pdf = jit(grad(jax.scipy.stats.norm.pdf, argnums=(0,)), static_argnums=(1, 2))
    batched_grad_n_pdf = vmap(grad_n_pdf, in_axes=(0, None, None))
    x_n_grads = batched_grad_n_pdf(x, 0, 1)

    npt.assert_almost_equal(x_sn_grads, x_n_grads)


def test_cdf_grads():
    """
    Tests if CDF function is differentiable.
    """
    x = 1.96
    params_split_norm = dict(
        loc=0,
        scale_1=1,
        scale_2=1
    )

    grad_cdf = jit(grad(sn.jax.cdf, argnums=(0, )), static_argnums=(1, 2, 3))
    x_grads = grad_cdf(x, params_split_norm['loc'], params_split_norm['scale_1'], params_split_norm['scale_2'])
    expected = sp.stats.norm.pdf(x, 0, 1)
    npt.assert_almost_equal(x_grads, expected)

    x = np.array([-1.96, 1.96])
    batched_grad_cdf = vmap(grad_cdf, in_axes=(0, None, None, None))
    x_grads = batched_grad_cdf(x, params_split_norm['loc'], params_split_norm['scale_1'], params_split_norm['scale_2'])
    expected = sp.stats.norm.pdf(x, 0, 1)
    npt.assert_almost_equal(x_grads[0], expected)


def test_ppf_grads():
    """
    Tests if CDF function is differentiable.
    """
    p = np.array([0.01, 0.5, 0.99])
    params_split_norm = dict(
        loc=0,
        scale_1=1,
        scale_2=1
    )

    # split normal distribution
    grad_ppf = jit(grad(sn.jax.ppf, argnums=(0, )), static_argnums=(1, 2, 3))
    batched_grad_ppf = vmap(grad_ppf, in_axes=(0, None, None, None))
    p_sn_grads = batched_grad_ppf(p, params_split_norm['loc'], params_split_norm['scale_1'], params_split_norm['scale_2'])
    print(p_sn_grads)

    # normal distribution
    grad_n_ppf = jit(grad(jax.scipy.stats.norm.ppf, argnums=(0,)), static_argnums=(1, 2))
    batched_grad_n_ppf = vmap(grad_n_ppf, in_axes=(0, None, None))
    p_n_grads = batched_grad_n_ppf(p, 0, 1)

    npt.assert_almost_equal(p_sn_grads, p_n_grads, decimal=4)
