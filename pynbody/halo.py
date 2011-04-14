import numpy as np
import weakref
import os.path
import glob
import re
import copy
from . import snapshot, util, config

class Halo(snapshot.IndexedSubSnap) :
    def __init__(self, halo_id, halo_catalogue, *args) :
        super(Halo, self).__init__(*args)
        self._halo_catalogue = halo_catalogue
        self._halo_id = halo_id
        self._descriptor = "halo_"+str(halo_id)
        self.properties = copy.copy(self.properties)
        self.properties['halo_id'] = halo_id

    def is_subhalo(self, otherhalo):
        return self._halo_catalogue.is_subhalo(self._halo_id, otherhalo._halo_id)
        
class HaloCatalogue(object) :
    def __init__(self) :
        self._halos = {}

    def __getitem__(self, i) :
        if self._halos.has_key(i) :  # and self._halos[i]() is not None :
            return self._halos[i] # ()
        else :
            h = self._get_halo(i)
            self._halos[i] = h # weakref.ref(h)
            return h

    def is_subhalo(self,childid,parentid) :
        if (childid in self._halos[parentid].properties['children']) :
            return True
        else : return False

    def contains(self,haloid):
        if (haloid in self._halos) : return True
        else: return False

    def _can_load(self):
        return False

    def _can_run(self):
        return False

class AHFCatalogue(HaloCatalogue) :
    def __init__(self, sim) :
        import os.path
        if not self._can_load(sim) :
            self._run_ahf(sim)
        self._base = weakref.ref(sim)
        HaloCatalogue.__init__(self)
        #try:
        f = util.open_((util.cutgz(glob.glob(sim._filename+'*z*halos*')[0])))
        for i, l in enumerate(f):
            pass
        self._nhalos=i
        f.close()
        if config['verbose']: print "Loading particles"
        self._load_ahf_particles(util.cutgz(glob.glob(self.base._filename+'*z*particles*')[0]))
        if config['verbose']: print "Loading halos"
        self._load_ahf_halos(util.cutgz(glob.glob(sim._filename+'*z*halos*')[0]))
        if config['verbose']: print "Loading substructure"
        self._load_ahf_substructure(util.cutgz(glob.glob(sim._filename+'*z*substructure*')[0]))
        try:
            if config['verbose']: print "Setting grp"
            for halo in self._halos.values():
                halo['grp'][:] = halo._halo_id
        except KeyError:
            print "Failed grp load: "+str(KeyError)
            pass
        #except IndexError:
        #    print "IndexError"+str(IndexError)

    def _get_halo(self, i) :
        if self.base is None :
            raise RuntimeError, "Parent SimSnap has been deleted"

        # XXX how do we lazy load particles (and only do it once)?
        # in other words, WHEN do we lazy load particles?
        #if (not self._particles_loaded) :
        #    self._particles_loaded = True
            
        #x = self.base[self._halos[i]]
        x = self._halos[i]
        x._descriptor = "halo_"+str(i)
        return x

    @property
    def base(self) :
        return self._base()

    def _load_ahf_particles(self,filename) :
        f = util.open_(filename)
        if filename.split("z")[0][-1] is "." : self.isnew = True
        else : self.isnew = False
        # tried readlines, which is fast, but the time is spent in the
        # for loop below, so sticking with this (hopefully) more readable 
        if self.isnew:
            nhalos=int(f.readline())
        else: 
            nhalos = self._nhalos
        ng = len(self.base.gas)
        nds = len(self.base.dark) + len(self.base.star)
        for h in xrange(nhalos) :
            nparts = int(f.readline())
            keys = {}
            # wow,  AHFstep has the audacity to switch the id order to dark,star,gas
            # switching back to gas, dark, star
            for i in xrange(nparts) : 
                if self.isnew:
                    key,value=f.readline().split()
                    if (value == '0'): key=int(key)-nds
                    else: key=int(key)+ng
                else :
                    key=f.readline()
                    value = 0
                keys[int(key)]=int(value)
            self._halos[h+1] = Halo( h+1, self, self.base, sorted(keys.keys()))
        f.close()

    def _load_ahf_halos(self,filename) :
        f = util.open_(filename)
        # get all the property names from the first, commented line
        # remove (#)
        keys = [re.sub('\([0-9]*\)','',field)
                for field in f.readline().split()]
        # provide translations
        for i,key in enumerate(keys) :
            if self.isnew:
                if(key == '#npart') : keys[i] = 'npart'
            else: 
                if(key == '#') : keys[i] = 'dumb'
            if(key == 'a') : keys[i] = 'a_axis'
            if(key == 'b') : keys[i] = 'b_axis'
            if(key == 'c') : keys[i] = 'c_axis'
            if(key == 'Mvir') : keys[i] = 'mass'
        for h, line in enumerate(f) :
            values = [float(x) for x in line.split()]
            # XXX Unit issues!  AHF uses distances in Mpc/h, possibly masses as well
            for i,key in enumerate(keys) :
                if self.isnew:
                    self._halos[h+1].properties[key] = values[i]
                else :
                    self._halos[h+1].properties[key] = values[i-1]
        f.close()

    def _load_ahf_substructure(self,filename) :
        f = util.open_(filename)
        nhalos = int(f.readline())  # number of halos?  no, some crazy number
                                    # that we will ignore
        for i in xrange(len(self._halos)) :
            try:
                haloid, nsubhalos = [int(x) for x in f.readline().split()]
                self._halos[haloid+1].properties['children'] = [int(x)+1 for x in f.readline().split()]
            except ValueError:
                break
        f.close()

    @staticmethod
    def _can_load(sim) :
        for file in glob.glob(sim._filename+'*z*particles*') :
            if os.path.exists(file) :
                return True
        return False

    def _run_ahf(self, sim) :
        # if (sim is pynbody.tipsy.TipsySnap) :
        import pynbody.units as units
        #build units file
        f = open('tipsy.info','w')
        f.write(str(sim.properties['omegaM0'])+"\n")
        f.write(str(sim.properties['omegaL0'])+"\n")
        f.write(str(sim['pos'].units.ratio(units.kpc,a=1)/1000.0 * sim.properties['h'])+"\n")
        f.write(str(sim['vel'].units.ratio(units.km/units.s))+"\n")
        f.write(str(sim['mass'].units.ratio(units.Msol))+"\n")
        f.close()
        typecode='90'
        #elif (sim is pynbody.gadget.GadgetSnap):
        #   typecode = '60' or '61'
        # make input file
        f = open('AHFstep.in','w')
        f.write(sim._filename+" "+typecode+" 1\n")
        f.write(sim._filename+"\n256\n5\n5\n0\n0\n0\n0\n")
        f.close()

        if (not os.path.exists(sim._filename)):
            os.system("gunzip "+sim._filename+".gz")
        # determine parallel possibilities
        # find AHFstep
        for directory in os.environ["PATH"].split(os.pathsep) :
            groupfinder = os.path.join(directory,"AHFstep")
            if os.path.exists(groupfinder) :
                # run it
                os.system(groupfinder+" AHFstep.in")
                return

    @staticmethod
    def _can_run(sim) :
        for directory in os.environ["PATH"].split(os.pathsep) :
            if os.path.exists(os.path.join(directory,"AHFstep")) :
                return True
        return False

class AmigaGrpCatalogue(HaloCatalogue) :
    def __init__(self, sim) :
        sim['amiga.grp'] # trigger lazy-loading and/or kick up a fuss if unavailable
        self._base = weakref.ref(sim)
        self._halos = {}
        HaloCatalogue.__init__(self)

    def _get_halo(self, i) :
        if self.base is None :
            raise RuntimeError, "Parent SimSnap has been deleted"

        x = Halo(i, self, self.base, np.where(self.base['amiga.grp']==i))
        x._descriptor = "halo_"+str(i)
        return x

    @property
    def base(self) :
        return self._base()

    @staticmethod
    def _can_load(sim) :
        try :
            sim['amiga.grp']
            return True
        except KeyError :
            return False


# AmigaGrpCatalogue MUST be scanned first, because if it exists we probably
# want to use it, but an AHFCatalogue will probably be on-disk too.

_halo_classes = [AmigaGrpCatalogue, AHFCatalogue]
_runable_halo_classes = [AHFCatalogue]

