""" Run stats on the MCMC chains or LM fits """
import numpy as np

from big import evaluate as big_eval

from IPython import embed

def calc_chisq(model_Rrs:np.ndarray, gordon_Rrs:np.ndarray, scl_noise:float):

    # Generate the model Rrs
    ichi2 = ((model_Rrs - gordon_Rrs) / (scl_noise * gordon_Rrs))**2

    # Return
    if model_Rrs.ndim == 1:
        return np.sum(ichi2)
    else:
        return np.sum(ichi2, axis=1)


def calc_BICs(gordon_Rrs:np.ndarray, models:list, params:np.ndarray, 
              scl_noise:float, use_LM:bool=False,
              debug:bool=False, Chl:np.ndarray=None):
    """ Calculate the Bayesian Information Criterion """
    
    if use_LM:
        model_Rrs, _, _ = big_eval.reconstruct_chisq_fits(
            models, params, Chl=Chl)
    else:
        raise ValueError("Not ready for MCMC yet")

    # Calculate the chisq
    chi2 = calc_chisq(model_Rrs, gordon_Rrs, scl_noise)

            
    nparm = np.sum([model.nparam for model in models])
    BICs = nparm * np.log(model_Rrs.shape[1]) + chi2 

    if debug and np.isclose(scl_noise, 0.5):
        embed(header='calc_BICs 38')

    # Return
    return BICs