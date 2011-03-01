from .. import filt, util
from . import cosmology
import numpy as np
import math

def centre_of_mass(sim) : # shared-code names should be explicit, not short
    """Return the centre of mass of the SimSnap"""
    return np.average(sim["pos"],axis=0,weights=sim["mass"]), np.average(sim["vel"],axis=0,weights=sim["mass"])

def shrink_sphere_centre(sim, r=None, shrink_factor = 0.7, min_particles = 100, verbose=False) :
    """Return the centre according to the shrinking-sphere method
    of Power et al (2003)"""
    x = sim

    if r is None :
        # use rough estimate for a maximum radius
        # results will be insensitive to the exact value chosen
        r = (sim["x"].max()-sim["x"].min())/2 
    
    while len(x)>min_particles :
        com = centre_of_mass(x)
        r*=shrink_factor
        x = sim[filt.Sphere(r, com)]
        if verbose:
            print com,r,len(x)
    return com

def virial_radius(sim, cen=(0,0,0), overden=178, r_max=None) :
    """Calculate the virial radius of the halo centred on the given
    coordinates.

    This is here defined by the sphere centred on cen which contains a mean
    density of overden * rho_c_0 * (1+z)^3. """

    if r_max is None :
        r_max = (sim["x"].max()-sim["x"].min())
    else :
        sim = sim[filt.Sphere(r_max,cen)]

    
    r_min = 0.0

    sim["r"] = ((sim["pos"]-cen)**2).sum(axis=1)**(1,2)
    
    rho = lambda r : sim["mass"][np.where(sim["r"]<r)].sum()/(4.*math.pi*(r**3)/3)
    target_rho = overden * sim.properties["omegaM0"] * cosmology.rho_crit(sim, z=0) * (1.0+sim.properties["z"])**3
    
    return util.bisect(r_min, r_max, lambda r : target_rho-rho(r), epsilon=0, eta=1.e-3*target_rho, verbose=True)
    
                  
def potential_minimum(sim) :
    i = sim["phi"].argmin()
    return sim["pos"][i].copy()


def centre(sim, mode='pot') :
    """Determine the centre of mass using the specified mode
    and recentre the particles accordingly

    Accepted values for mode are
      'pot': potential minimum
      'com': centre of mass
      'ssc': shrink sphere centre
    or a function returning the COM."""
    
    try:
	fn = {'pot': potential_minimum,
	      'com': centre_of_mass,
	      'ssc': shrink_sphere_centre}[mode]
    except KeyError :
	fn = mode

    cen = fn(sim)
    sim["pos"]-=cen
    