import math, numpy as np

from .. import units

def _a_dot(a, h0, om_m, om_l) :
    om_k = 1.0-om_m-om_l
    return h0*a*np.sqrt(om_m*(a**-3) + om_k*(a**-2) + om_l)

def _a_dot_recip(*args) :
    return 1./_a_dot(*args)

def age(f, z=None, unit='Gyr') :
    """Calculate the age of the universe in the snapshot f
    by integrating the Friedmann equation.

    The output is given in the specified units. If a redshift
    z is specified, it is used in place of the redshift in the
    output f."""

    import scipy, scipy.integrate
    
    if z is None :
        z = f.properties['z']
        
    a = 1.0/(1.0+z)
    h0 = f.properties['h']
    omM = f.properties['omegaM0']
    omL = f.properties['omegaL0']

    conv = units.Unit("0.01 s Mpc km^-1").ratio(unit, **f.conversion_context())
    
    age = scipy.integrate.quad(_a_dot_recip,0,a, (h0, omM, omL))[0]

    return age*conv