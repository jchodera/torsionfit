import netCDF4 as netcdf
from pymc.database import base
from pymc import six
import pymc
import numpy as np
import os

__all__ = ['Trace', 'Database']


class Trace(base.Trace):

    """netCDF4 Trace class"""

    def _initialize(self, chain, length):

        if self._getfunc is None:
            self._getfunc = self.db.model._funs_to_tally[self.name]

    def tally(self, index, chain=-1):
        """ Add current value to chain
        :param index: tall index
        :param chain: int
        """

        value = self._getfunc()
        self.db.ncfile['Chain#%d' % chain].variables[self.name][index] = value


class Database(base.Database):

    """netCDF4 database"""

    def __init__(self, dbname, dbmode='w'):
        """ Open or create netCDF4 database

        :param dbname: string
            name of database file
        :param dbmode: {'a' or 'w'}
            File mode. Use 'a' to append and 'w' to overwrite an existing file

        """
        self.__name__ = 'netcdf'
        self.dbname = dbname
        self.mode = dbmode
        self.trace_names = []
        self._traces = {} # dictionary of trace objects
        self.__Trace__ = Trace

        # check if database exists
        db_exists = os.path.exists(self.dbname)

        if db_exists and self.mode == 'w':
            print('overwriting file %s' % self.dbname)
            # overwrite
            os.remove(self.dbname)

        # open netCDF4 file
        self.ncfile = netcdf.Dataset(dbname, self.mode, version= 'NETCDF4')

        # Set global attributes
        setattr(self.ncfile, 'title', self.dbname)

        # Assign to self.chain to last chain
        try:
            self.chains = int(list(self.ncfile.groups)[-1].split('#')[-1])
            print self.chains
            self._chains = range(self.chains)
            print self._chains
        except:
            self.chains = 0

    def _initialize(self, funs_to_tally, length=None):

        for name, fun in six.iteritems(funs_to_tally):
            if name not in self._traces:
                self._traces[name] = self.__Trace__(name=name, getfunc=fun, db=self)
                self._traces[name]._initialize(self.chains, length)

        i = self.chains
        self.ncfile.createGroup("Chain#%d" % i)

        # set dimensions
        if 'nsamples' not in self.ncfile['Chain#%d' %i].dimensions:
            self.ncfile['Chain#%d' % i].createDimension('nsamples', 0) # unlimited number of iterations

        # sanity check that nsamples is unlimited
        if self.ncfile['Chain#%d' % i].dimensions['nsamples'].isunlimited():
            pass

        # create variables for pymc variables
        for name, fun in six.iteritems(funs_to_tally):
            if not np.asarray(fun()).shape == () and name not in self.ncfile['Chain#%d' % i].variables:
                self.ncfile['Chain#%d' % i].createDimension(name, np.asarray(fun()).shape[0])
                self.ncfile['Chain#%d' % i].createVariable(name, np.asarray(fun()).dtype.str, ('nsamples', name))
            elif name not in self.ncfile['Chain#%d' % i].variables:
                self.ncfile['Chain#%d' % i].createVariable(name, np.asarray(fun()).dtype.str, ('nsamples',))

        self.chains += 1
        self._chains = range(self.chains)
        for chain in self._chains:
            try:
                self.trace_names.append(list(self.ncfile['Chain#%d' % chain].variables))
            except IndexError:
                self.trace_names.append(list(funs_to_tally.keys()))
        self.tally_index = len(self.ncfile['Chain#%d' % i].dimensions['nsamples'])

    def connect_model(self, model):
        """Link the Database to the Model instance.
        In case a new database is created from scratch, ``connect_model``
        creates Trace objects for all tallyable pymc objects defined in
        `model`.
        If the database is being loaded from an existing file, ``connect_model``
        restore the objects trace to their stored value.
        :Parameters:
        model : pymc.Model instance
          An instance holding the pymc objects defining a statistical
          model (stochastics, deterministics, data, ...)
        """
        # Changed this to allow non-Model models. -AP
        # We could also remove it altogether. -DH
        if isinstance(model, pymc.Model):
            self.model = model
        else:
            raise AttributeError('Not a Model instance.')

        # Restore the state of the Model from an existing Database.
        # The `load` method will have already created the Trace objects.
        if hasattr(self, '_state_'):
            names = set()
            for morenames in self.trace_names:
                names.update(morenames)
            for name, fun in six.iteritems(model._funs_to_tally):
                if name in self._traces:
                    self._traces[name]._getfunc = fun
                    names.discard(name)
            # if len(names) > 0:
            # print_("Some objects from the database have not been assigned a
            # getfunc", names)

        # Create a fresh new state.
        # We will be able to remove this when we deprecate traces on objects.
        else:
            for name, fun in six.iteritems(model._funs_to_tally):
                if name not in self._traces:
                    self._traces[name] = self.__Trace__(name=name, getfunc=fun, db=self)

    def tally(self, chain=-1):
        """Append the current value of all tallyable object.
       :Parameters:
       chain : int
         The index of the chain to append the values to. By default, the values
         are appended to the last chain.
        """

        chain = range(self.chains)[chain]
        for name in self.trace_names[chain]:
            try:
                self._traces[name].tally(self.tally_index, chain)
            except:
                cls, inst, tb = sys.exc_info()
                warnings.warn("""
Error tallying %s, will not try to tally it again this chain.
Did you make all the samevariables and step methods tallyable
as were tallyable last time you used the database file?
Error:
%s""" % (name, ''.join(traceback.format_exception(cls, inst, tb))))
                self.trace_names[chain].remove(name)

        self.tally_index += 1


def load(self, dbname, dbmode='a'):
    """ Load an existing netcdf database

    :param dbname: name of netcdf file to open
    :param dbmode: 'a': append, 'r': read-only
    :return: database
    """
    if dbmode == 'w':
        raise AttributeError("dbmode='w' not allowed for load")

    db = Database(dbname, dbmode=dbmode)

    return db




