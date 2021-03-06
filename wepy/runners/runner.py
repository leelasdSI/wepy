"""Abstract Base classes implementing the Runner interface.

Runner Interface
----------------

All a runner needs to implement is the 'run_segment' method which
should accept a walker and a spec for the length of the segment to run
(e.g. number of dynamics steps).

Additionally, any number of optional key word arguments should be given.

As a matter of convention, classes accessory to a runner (such as
State, Walker, Worker, etc.) should also be put in the same module as
the runner.

See the openmm.py module for an example.

"""

import logging

class Runner(object):
    """Abstract base class for the Runner interface."""

    def run_segment(self, walker, segment_length, **kwargs):
        """Run dynamics for the walker.

        Parameters
        ----------
        walker : object implementing the Walker interface
            The walker for which dynamics will be propagated.
        segment_length : int or float
            The numerical value that specifies how much dynamics are to be run.

        Returns
        -------
        new_walker : object implementing the Walker interface
            Walker after dynamics was run, only the state should be modified.

        """

        raise NotImplementedError

class NoRunner(Runner):
    """Stub Runner that just returns the walkers back with the same state.

    May be useful for testing.
    """

    def run_segment(self, walker, segment_length):
        # documented in superclass
        return walker
