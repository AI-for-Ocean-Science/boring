""" Run BIG one one spectrum """

import os

import numpy as np

from matplotlib import pyplot as plt

from ihop.inference import noise

from bing.models import anw as bing_anw
from bing.models import bbnw as bing_bbnw
from bing.models import utils as model_utils
from bing import inference as bing_inf
from bing import rt as bing_rt
from bing import chisq_fit
from bing import plotting as bing_plot
from bing import priors as bing_priors

from oceancolor.satellites import modis as sat_modis
from oceancolor.satellites import pace as sat_pace
from oceancolor.satellites import seawifs as sat_seawifs

from IPython import embed

import anly_utils 

def fit_one(model_names:list, idx:int, n_cores=20, 
            nsteps:int=10000, nburn:int=1000, 
            scl_noise:float=0.02, use_chisq:bool=False,
            add_noise:bool=False,
            max_wave:float=None,
            show:bool=False,
            MODIS:bool=False,
            SeaWiFS:bool=False,
            PACE:bool=False):

    odict = anly_utils.prep_l23_data(idx, scl_noise=scl_noise,
                                     max_wave=max_wave)

    # Unpack
    wave = odict['wave']
    l23_wave = odict['true_wave']

    # Wavelenegths
    if MODIS:
        model_wave = sat_modis.modis_wave
    elif PACE:
        model_wave = sat_pace.pace_wave
        PACE_error = sat_pace.gen_noise_vector(PACE_wave)
    elif SeaWiFS:
        model_wave = sat_seawifs.seawifs_wave
    else:
        model_wave = wave

    # Models
    models = model_utils.init(model_names, model_wave)
    
    # Initialize the MCMC
    pdict = bing_inf.init_mcmc(models, nsteps=nsteps, nburn=nburn)
    
    # Gordon Rrs
    gordon_Rrs = bing_rt.calc_Rrs(odict['a'], odict['bb'])
    if add_noise:
        gordon_Rrs = noise.add_noise(gordon_Rrs, perc=scl_noise*100)

    # Internals
    if models[0].uses_Chl:
        models[0].set_aph(odict['Chl'])
    if models[1].uses_basis_params:  # Lee
        models[1].set_basis_func(odict['Y'])

    # Bricaud?
    # Interpolate
    model_Rrs = anly_utils.convert_to_satwave(l23_wave, gordon_Rrs, model_wave)
    model_anw = anly_utils.convert_to_satwave(l23_wave, odict['anw'], model_wave)
    model_bbnw = anly_utils.convert_to_satwave(l23_wave, odict['bbnw'], model_wave)

    model_varRrs = anly_utils.scale_noise(scl_noise, model_Rrs, model_wave)

    # Initial guess
    p0_a = models[0].init_guess(model_anw)
    p0_b = models[1].init_guess(model_bbnw)
    p0 = np.concatenate((np.log10(np.atleast_1d(p0_a)), 
                         np.log10(np.atleast_1d(p0_b))))

    # Chk initial guess
    ca = models[0].eval_a(p0[0:models[0].nparam])
    cbb = models[1].eval_bb(p0[models[0].nparam:])
    pRrs = bing_rt.calc_Rrs(ca, cbb)
    print(f'Initial Rrs guess: {np.mean((model_Rrs-pRrs)/model_Rrs)}')
    #embed(header='95 of fit one')
    

    # Set the items
    items = [(model_Rrs, model_varRrs, p0, idx)]

    outfile = anly_utils.chain_filename(
        model_names, scl_noise, add_noise, idx=idx,
        MODIS=MODIS, PACE=PACE, SeaWiFS=SeaWiFS)
    if not use_chisq:
        prior_dict = dict(flavor='uniform', pmin=-6, pmax=5)

        for jj in range(2):
            models[jj].priors = bing_priors.Priors(
                [prior_dict]*models[jj].nparam)

        # Fit
        chains, idx = bing_inf.fit_one(items[0], models=models, pdict=pdict, chains_only=True)

        # Save
        anly_utils.save_fits(chains, idx, outfile, 
                             extras=dict(wave=model_wave, 
                                         obs_Rrs=model_Rrs, 
                                         varRrs=model_varRrs, 
                                         Chl=odict['Chl'], 
                                         Y=odict['Y']))
    else:
        # Fit
        ans, cov, idx = chisq_fit.fit(items[0], models)
        # Show?
        if show:
            bing_plot.show_fit(models, ans, odict['Chl'], odict['Y'],
                                 Rrs_true=dict(wave=model_wave, spec=model_Rrs),
                                 anw_true=dict(wave=l23_wave, spec=odict['anw']),
                                 bbnw_true=dict(wave=l23_wave, spec=odict['bbnw'])
                                 )
            plt.show()
            
        # Save
        outfile = outfile.replace('BING', 'BING_LM')
        np.savez(outfile, ans=ans, cov=cov,
              wave=wave, obs_Rrs=gordon_Rrs, varRrs=model_varRrs,
              Chl=odict['Chl'], Y=odict['Y'])
        print(f"Saved: {outfile}")
        #
        return ans, cov


def main(flg):
    flg = int(flg)

    # Testing
    if flg == 1:
        odict = anly_utils.prep_l23_data(170)

    # First one
    if flg == 2:
        fit_one(['Exp', 'Pow'], idx=170, nsteps=10000, nburn=1000) 

    # Fit 170
    if flg == 3:
        idx = 170
        #fit_one(['Cst', 'Cst'], idx=idx, nsteps=80000, nburn=8000) 
        #fit_one(['Exp', 'Cst'], idx=idx, nsteps=80000, nburn=8000) 
        #fit_one(['Exp', 'Pow'], idx=idx, nsteps=10000, nburn=1000) 
        fit_one(['ExpBricaud', 'Pow'], idx=idx, nsteps=10000, nburn=1000) 

    # chisq fits
    if flg == 4:
        #fit_one(['Cst', 'Cst'], idx=170, use_chisq=True)
        #fit_one(['Exp', 'Cst'], idx=170, use_chisq=True)
        #fit_one(['Exp', 'Pow'], idx=170, use_chisq=True)
        #fit_one(['ExpBricaud', 'Pow'], idx=170, use_chisq=True)
        fit_one(['ExpNMF', 'Pow'], idx=170, use_chisq=True)

    # GIOP
    if flg == 5:
        fit_one(['GIOP', 'Lee'], idx=0, use_chisq=True, show=True)

    # Bayes on GSM with SeaWiFS noise
    if flg == 6:
        fit_one(['GSM', 'GSM'], idx=170, SeaWiFS=True,
                use_chisq=False, show=True, nburn=5000,
                nsteps=50000, scl_noise='SeaWiFS')
        fit_one(['GSM', 'GSM'], idx=1032, SeaWiFS=True,
                use_chisq=False, show=True, nburn=5000,
                nsteps=50000, scl_noise='SeaWiFS')

    # Bayes on GIOP with MODIS noise
    if flg == 7:
        fit_one(['GIOP', 'Lee'], idx=170, SeaWiFS=True,
                use_chisq=False, show=True, nburn=5000,
                nsteps=50000)
        fit_one(['GIOP', 'Lee'], idx=1032, SeaWiFS=True,
                use_chisq=False, show=True, nburn=5000,
                nsteps=50000)
    # Debug
    if flg == 99:
        fit_one(['GSM', 'GSM'], idx=170, 
                use_chisq=True, show=True, max_wave=700.)
        #fit_one(['ExpNMF', 'Pow'], idx=1067, 
        #        use_chisq=True, show=True, max_wave=700.)

    # Develop SeaWiFS
    if flg == 100:
        fit_one(['Exp', 'Cst'], idx=170, 
                use_chisq=True, show=True, max_wave=700.,
                SeaWiFS=True)

    # Bayes development
    if flg == 101:
        pass
        #fit_one(['GSM', 'GSM'], idx=170, 
        #        use_chisq=False, show=True, max_wave=700.)
        #fit_one(['GSM', 'GSM'], idx=170, SeaWiFS=True,
        #        use_chisq=False, show=True, scl_noise='SeaWiFS')

    # Bayes on GIOP
    if flg == 102:
        #fit_one(['GIOP', 'Lee'], idx=170, MODIS=True,
        #        use_chisq=False, show=True, scl_noise='MODIS_Aqua')
        fit_one(['GIOP', 'Lee'], idx=1032, MODIS=True,
                use_chisq=False, show=True, scl_noise='MODIS_Aqua')


# Command line execution
if __name__ == '__main__':
    import sys

    if len(sys.argv) == 1:
        flg = 0
        #flg += 2 ** 0  # 1 -- Testing
        #flg += 2 ** 1  # 2 -- No priors
        #flg += 2 ** 2  # 4 -- bb_water

    else:
        flg = sys.argv[1]

    main(flg)