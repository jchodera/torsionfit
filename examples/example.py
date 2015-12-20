# opemm imports
import simtk.openmm as mm

# ParmEd imports
from parmed.charmm import CharmmParameterSet
#import cProfile
#import pstats
#import StringIO
import torsionfit.TorsionScanSet as TorsionScanSet
import torsionfit.TorsionFitModel as TorsionFitModel
import glob
from pymc import MCMC
import torsionfit.netcdf4 as db
#from memory_profiler import profile

param = CharmmParameterSet('../charmm_ff/top_all36_cgenff.rtf', '../charmm_ff/par_all36_cgenff.prm')
stream = ['pyrrole/pyrrol.str', 'pyrrole-2/methyl-pyrrol.str']
structure = ['pyrrole/pyrrol.psf', 'pyrrole-2/methyl-pyrrol.psf']
scan = glob.glob('pyrrole/torsion-scan/*.log')
pyrrol_scan = TorsionScanSet.read_scan_logfile(scan, structure[0])
pyrrol_opt = pyrrol_scan.extract_geom_opt()
pyrrol_2_scan = TorsionScanSet.read_scan_logfile(glob.glob('pyrrole-2/torsion-scan/*.log'), structure[1])
pyrrol_2_opt = pyrrol_2_scan.extract_geom_opt()
frags = [pyrrol_opt, pyrrol_2_opt]
#create pymc model
platform = mm.Platform.getPlatformByName('Reference')
model = TorsionFitModel.TorsionFitModel(param, stream, frag, platform=platform)
#update param with missing parameters
model.add_missing(param)
sampler = MCMC(model.pymc_parameters, db=db, dbname='/Users/sternc1/src/ChayaSt/Torsions/examples/test.nc', verbose=5)

sampler.sample(iter=10)

#cProfile.run('sampler.sample(iter=50)', 'statfile')
#sampler.db.close()
#stream = StringIO.StringIO()
#pstats.print_stats()

#print(stream.getvalue())