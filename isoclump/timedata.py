'''
This module contains the Experiment superclass and all corresponding subclasses.
'''

#for python 2 compatibility
from __future__ import(
	division,
	print_function,
	)

__docformat__ = 'restructuredtext en'
__all__ = ['HeatingExperiment']

#import modules
import matplotlib.pyplot as plt
import numpy as np
import warnings

#import exceptions
from .exceptions import(
	ArrayError,
	ScalarError,
	)

#import helper functions
from .core_functions import(
	assert_len
	)

from .plotting_helper import(
	_rem_dup_leg,
	)

# from .summary_helper import()
from .model_helper import(
	_calc_fihat
	)

# from .timedata_helper import ()

class TimeData(object):
	'''
	Class to store time-dependent data. Intended for subclassing, do not call
	directly.
	'''

	def __init__(self, t, T, fi = None, fi_std = None, T_std = None):
		'''
		Initialize the superclass.

		Parameters
		----------
		t : array-like
			Array of experimental time points, in seconds. Length `nt`.

		T : scalar or array-like
			Array of experimental temperature, in Kelvin. Length `nt`. If
			scalar, assumes constant temperature experiment.

		fi : array-like or None
			The fractional abundance of each isotopologue at each experimental
			time point. Shape `nt` x `ni`.

		fi_std : array-like or None
			The analytical standard deviation of the fractional abundance of
			each isotopologue. If 1d array of length `ni`, assumes constant
			uncertainty with time; if 2d array, then length `nt` x `ni`; if
			`None`, then assumes no uncertainty. Defaults to `None`.

		T_std : array-like or None
			The standard deviation of `T`, with length `nt`, in Kelvin. If
			scalar, assumes constant temperature uncertainty. Defaults to
			`None`.
		'''

		#store time-temperature attributes
		nt = len(t)
		_, ni = np.shape(fi)
		self.nt = nt
		self.ni = ni

		self.t = assert_len(t, nt) #s
		self.T = assert_len(T, nt) #K

		if T_std is not None:

			#only store T_std if it exists (None for now, keep for future use)
			self.T_std = assert_len(T_std, nt) #K

		#check if fi and store
		if fi is not None:

			#assert fi values remain between 0 and 1
			if np.max(fi) > 1 or np.min(fi) < 0:
				raise ArrayError(
					'fi must remain between 0 and 1 (fractional abundances)')

			self.fi = assert_len(fi, nt) #fractional

			#check if fi_std exists and store
			if fi_std is not None:

				#assert shape
				nstd, mstd = np.shape(fi_std)

				if nstd != nt or mstd != ni:
					raise ArrayError(
						'If not `None`, fi_std must have same shape as fi.')

				self.fi_std = assert_len(fistd, nt)

	#define class method for creating instance directly from .csv file
	@classmethod
	def from_csv(cls, file):
		raise NotImplementedError

	#define method for forward-modeling rate data using a given model
	def forward_model(self, model, ratedata):
		'''
		Forward-models clumped isotope values for a given time-temperature
		history and a given model type.

		Parameters
		----------
		model : ci.Model
			``ci.Model`` instance used to calculate the forward model.

		ratedata : ci.RateData
			``ci.RateData`` instance used to calculate the forward model.

		Warnings
		--------
		UserWarning
			If the time-temperature data in the ``ci.Model`` isntance do not
			match the time-temperature data in the ``ci.TimeData`` isntance.

		UserWarning
			If the ``ci.RateData`` instance was generated using a different
			type of model than the ``ci.Model`` instance.
		'''

		#extract instance types
		td_type = type(self).__name__
		mod_type = type(model).__name__
		rd_type = type(ratedata).__name__

		#warn if self and model t and T arrays do not match
		if (self.t != model.t).any() or (self.T != model.T).any():
			warnings.warn(
				'ci.TimeData instance of class %s and ci.Model instance of'
				' class %s do not contain matching time-temperature arrays.'
				' Check that the model does not correspond to a different'
				' ci.TimeData instance' %(dt_type, mod_type), UserWarning)

		#warn if model and ratedata types do not match
		if model.mod_type != ratedata.mod_type:
			warnings.warn(
				'ci.Model instance of class %s and ci.RateData instance of'
				' class %s do not correspond to the same model type (i.e.,'
				' PH12, Hea14, SE15, or HH20). Check that this model does not'
				' correspond to a different ci.RateData instance'
				%(mod_type, rd_type), UserWarning)

		#calculate forward-modelled fi estimate, fihat
		fihat = _calc_fihat(self, model, ratedata)

		#populate with modeled data
		self.input_estimated(fihat)

	#define method for inputting estimated results from a model fit
	def input_estimated(self, fihat):
		'''
		Method to input model estimated data into ``ci.TimeData`` isntance and
		to calculate corresponding statistics.

		Parameters
		----------
		fihat : array-like
			Array of estimated fractional isotoplogue abundances at each time
			step. Length `nt`.
		'''

		#ensure type and size
		nt = self.nt
		self.fihat = assert_len(fihat, nt)

		#store RMSE if the model has true data, fi
		if hasattr(self, 'fi'):

			resid = norm(self.g - ghat)/nt**0.5
			self.resid = resid

	#define plotting method
	def plot(self, ax = None, labs = None, md = None, rd = None):
		'''
		Method for plotting ``ci.TimeData`` instance data.

		Parameters
		----------
		ax : matplotlib.axis or None
			Axis handle to plot on. Defaults to `None`.

		labs : tuple
			Tuple of axis labels, in the form (x_label, y_label).
			Defaults to `None`.

		md : tuple or None
			Tuple of modelled data, in the form  (x_data, y_data). Defaults
			to `None`.

		rd : tuple
			Tuple of real (observed) data, in the form (x_data, y_data). 
			Defaults to `None`.

		Returns
		-------
		ax : matplotlib.axis
			Updated axis handle containing data.
		'''

		#create axis if necessary and label
		if ax is None:
			_, ax = plt.subplots(1, 1)

		#label axes if labels exist
		if labs is not None:
			ax.set_xlabel(labs[0])
			ax.set_ylabel(labs[1])

		#add real data if it exists
		if rd is not None:
			ax.scatter(
				rd[0], 
				rd[1],
				marker = 'o',
				s = 20,
				c = 'k',
				ec = 'w',
				label = 'Observed Data')

			#set limits
			ax.set_xlim([0, 1.1*np.max(rd[0])])
			ax.set_ylim([0, 1.1*np.max(rd[1])])
			
		#add model-estimated data if it exists
		if md is not None:

			#plot the model-estimated total
			ax.plot(
				md[0], 
				md[1],
				linewidth = 2,
				color = [0.5, 0.5, 0.5],
				label = 'Model-estimated data')

			#(re)set limits
			ax.set_xlim([0, 1.1*np.max(md[0])])
			ax.set_ylim([0, 1.1*np.max(md[1])])

		#remove duplicate legend entries
		han_list, lab_list = _rem_dup_leg(ax)
		
		ax.legend(
			han_list,
			lab_list, 
			loc = 'best',
			frameon = False)

		#make tight layout
		plt.tight_layout()

		return ax


class D47Experiment(TimeData):
	__doc__='''
	Class for inputting and storing reordering experiment true (observed)
	and estimated (forward-modelled) carbonate clumped isotope data,
	calculating goodness of fit statistics, and reporting summary tables.

	Parmeters
	---------

	Warnings
	--------

	Notes
	-----

	See Also
	--------

	Examples
	--------

	**Attributes**


	'''

	# def __init__(self, t, T, fi = None, fi_std = None, T_std = None):




















