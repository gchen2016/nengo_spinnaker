import nengo
import numpy as np

from .builder import Model, ObjectPort, spec
from .model import ReceptionParameters, InputPort, OutputPort

try:
    from xxhash import xxh64 as fast_hash
except ImportError:
    from hashlib import md5 as fast_hash


@Model.source_getters.register(nengo.base.NengoObject)
def generic_source_getter(model, conn):
    obj = model.object_operators[conn.pre_obj]
    return spec(ObjectPort(obj, OutputPort.standard))


@Model.sink_getters.register(nengo.base.NengoObject)
def generic_sink_getter(model, conn):
    obj = model.object_operators[conn.post_obj]
    return spec(ObjectPort(obj, InputPort.standard))


@Model.reception_parameter_builders.register(nengo.base.NengoObject)
@Model.reception_parameter_builders.register(nengo.connection.LearningRule)
@Model.reception_parameter_builders.register(nengo.ensemble.Neurons)
def build_generic_reception_params(model, conn):
    """Build parameters necessary for receiving packets that simulate this
    connection.
    """
    # Just extract the synapse from the connection.
    return ReceptionParameters(conn.synapse, conn.post_obj.size_in,
                               conn.learning_rule)


class TransmissionParameters(object):
    """Parameters describing generic connections."""
    def __init__(self, transform):
        # Determine the pre- and post-sizes
        self._size_out, self._size_in = transform.shape

        # Determine the pre- and post-slices
        self._slice_in = tuple(
            i for i, include in enumerate(np.any(transform != 0, axis=0))
            if include
        )
        self._slice_out = tuple(
            i for i, include in enumerate(np.any(transform != 0, axis=1))
            if include
        )

        # Store the residual portion of the transform
        self._transform = np.zeros((len(self._slice_out),
                                    len(self._slice_in)))

        row_transform = transform[self._slice_out, :]
        self._transform[:, :] = row_transform[:, self._slice_in]

        # The residual portion of the transform must be read-only
        self._transform.flags['WRITEABLE'] = False

    @property
    def transform(self):
        # Construct the full transform
        transform = np.zeros((self._size_out, self._size_in))

        # Copy the values back into the transform
        row_transform = np.zeros_like(transform[self._slice_out, :])
        row_transform[:, self._slice_in] = self._transform
        transform[self._slice_out, :] = row_transform

        return transform

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        # Equivalent if the same type
        if type(self) is not type(other):
            return False

        # and the transforms are equivalent
        if not (self._size_in == other._size_in and
                self._size_out == other._size_out and
                self._slice_in == other._slice_in and
                self._slice_out == other._slice_out and
                np.array_equal(self._transform, other._transform)):
            return False

        return True

    @property
    def _hashables(self):
        return (type(self), self._slice_in, self._slice_out, self._size_in,
                self._size_out, fast_hash(self.transform).hexdigest())

    def __hash__(self):
        return hash(self._hashables)


class EnsembleTransmissionParameters(TransmissionParameters):
    """Transmission parameters for a connection originating at an Ensemble.

    Attributes
    ----------
    transform : array
        Decoders to use for the connection (n_dims x n_neurons)
    """
    def __init__(self, transform, learning_rule):
        super(EnsembleTransmissionParameters, self).__init__(transform)

        # Cache learning rule
        self.learning_rule = learning_rule

    def __ne__(self, other):
        return not (self == other)

    def __eq__(self, other):
        # Equal iff. neither connection has a learning rule
        if self.learning_rule is not None or other.learning_rule is not None:
            return False

        return super(EnsembleTransmissionParameters, self).__eq__(other)

    def __hash__(self):
        return hash(
            super(EnsembleTransmissionParameters, self)._hashables +
            (self.learning_rule, )
        )


class PassthroughNodeTransmissionParameters(TransmissionParameters):
    """Parameters describing connections which originate from pass through
    Nodes.
    """


class NodeTransmissionParameters(PassthroughNodeTransmissionParameters):
    """Parameters describing connections which originate from Nodes."""
    def __init__(self, pre_slice, function, transform):
        # Store the parameters
        super(NodeTransmissionParameters, self).__init__(transform)
        self.pre_slice = pre_slice
        self.function = function

    def __hash__(self):
        # Hash by ID
        return hash(id(self))

    def __eq__(self, other):
        # Parent equivalence
        if not super(NodeTransmissionParameters, self).__eq__(other):
            return False

        # Equivalent if the pre_slices are exactly the same
        if self.pre_slice != other.pre_slice:
            return False

        # Equivalent if the functions are the same
        if self.function is not other.function:
            return False

        return True

    @property
    def _hashables(self):
        return (super(NodeTransmissionParameters, self)._hashables +
                (self.function, ))
