#!/usr/env/python

"""
Short description.

flow_accum_to_n.py: Implementation a route-to-multiple drainage stack alorithm.


Algorithm for route to multiple (N) flow accumulation. Inspiration for data
structures and attempting O(n) efficiency taken from Braun and Willet(2013).

Algorithm constructs drainage area and (optionally) water discharge. Can
handle the case in which each node has more than one downstream receiver.

Computationally, for a grid of the same size this algorithm will take about
    1.5*(avg number of downstream nodes per cell)
        *(duration of flow_accum_bw for same grid using route-to-one method)

So under route-to-one direction schemes, using the Braun and Willet method is
recommended.

If water discharge is calculated, the result assumes steady flow (that is,
hydrologic equilibrium).

The main public function is:

    a, q, s = flow_accumulation_to_n(r, p)

which takes the following inputs:

    r, an (np, q) array of receiver-node IDs, where np is the total number of
    nodes and q is the maximum number of receivers any node in the grid has.
    This array would be returned by the flow_routing component.

    p, an (np, q) array that identifies the proportion of flow going to each
    receiver. For each q elements along the np axis, sum(p(i, :)) must equal
    1. This array would be returned by the flow_routing component.

It returns Numpy arrays with the drainage area (a) and discharge (q) at each
node, along with an array (s) that contains the IDs of the nodes in downstream-
to-upstream order.

If you simply want the ordered list by itself, use::

    s = make_ordered_node_array_to_n(r, p, b)

Created: KRB Oct 2016 (modified from flow_accumu_bw)
"""
import numpy
from six.moves import range

class _DrainageStack_to_n():

    """
    Implementation of the DrainageStack_to_n class.

    The _DrainageStack_to_n() class implements a set based approach to
    constructing a stack with similar properties to the stack constructed by
    Braun & Willet (2013). It constructs an list, s, of all nodes in the grid
    such that a given node is always located earlier in the list than all
    upstream nodes that contribute to it.

    It is used by the make_ordered_node_array_to_n() function.
    """


    def __init__(self, delta, D):

        """
        Creates the stack array s and stores references to delta and D.

        Initialization of the _DrainageStack_to_n() class including storing
        delta and D.
        """

        self.s = list()
        self.delta = delta
        self.D = D


    def construct__stack(self, l):
        """
        Function to construct the drainage stack.

        Function to add all nodes upstream of a set of base level nodes given
        by list l in an order
        such that downstream nodes always occur before upstream nodes.

        This function contains the major algorithmic difference between the
        route to 1 method of Braun and Willet (2013) and the route to N method
        presented here.

        Rather than recursively moving up the tributary tree this method uses
        sets test that a node is downstream and add it to the stack. Both
        methods are functionally depth first searches. The method that Braun
        and Willet (2013) implement is optimized given that each node only has
        one receiver. This method is optimized to visit more than one vertex/
        node of the graph at a time.

        An important note: Since sets are un-ordered, we cannot expect the
        stack to be exactly the same each time. It will always put nodes that
        are downstream before those that are upstream, but because it will move
        up multiple branches at the same time, it may put three nodes into the
        stack at the same time that are on different branches of the flow
        network. Because these nodes are in different parts of the network,
        the relative order of them does not matter.

        For example, in the example below, the nodes 1 and 7 must be added
        after 5 but before 2 and 6.

        Examples
        --------
        >>> import numpy as np
        >>> from landlab.components.flow_accum.flow_accum_to_n import(
        ... _DrainageStack_to_n)
        >>> delta = np.array([0, 0, 2, 4, 4, 8, 12, 14, 17, 18, 18])
        >>> D = np.array([0, 2, 0, 3, 1, 4, 5, 7, 6, 1, 2, 7, 3, 8, 9, 6, 8, 9])
        >>> ds = _DrainageStack_to_n(delta, D)
        >>> ds.construct__stack(4)
        >>> ds.s[0] == 4
        True
        >>> ds.s[1] == 5
        True
        >>> ds.s[9] == 9
        True
        >>> len(set([1, 7])-set(ds.s[2:4]))
        0
        >>> len(set([2, 6])-set(ds.s[4:6]))
        0
        >>> len(set([0, 3, 8])-set(ds.s[6:9]))
        0
        """

        # create base nodes set
        try:
            base = set(l)
        except:
            base = set([l])

        # instantiate the time keeping variable i, and a variable to keep track
        # of the visit time. Using visit time allows us to itterate through
        # the entire graph and make sure that only put a node in the stack 
        # the last time it is visited. 
        i = 0
        visit_time = -1*numpy.ones((self.delta.size-1))
        
        #create the upstream set by adding all nodes that flow into the base
        # nodes.
        upstream = set()
        for node_i in base:
            upstream.update(self.D[self.delta[node_i]:self.delta[
                    node_i+1]])

        # set the visit time for the first nodes.
        visit_time[list(base)]=i

        # then set the base to upstream-base
        base = upstream-base  # only need to do this here.

        # march topologically upstream, identifing the itteration time when
        # each node is visited.
        # if a node sends flow to m nodes, it will be visited m times. 
        
        while len(upstream) > 0:
            
            # add to the time counter. 
            i+=1
            
            # construct the nodes upstream of the current set of nodes. 
            upstream = set([])
            for node_i in base:
                
                # add nodes that are upstream of base nodes into the upstream
                # stack
                upstream.update(self.D[self.delta[node_i]:self.delta[
                    node_i+1]])
            
            # select the nodes that have been visited and record their visit 
            # time. 
            visited = base-upstream
            visit_time[list(visited)] = i
    
            # update the base. 
            base = base-visited
            base.update(upstream)
    
        # the stack is the argsort of visit time. 
        self.s = numpy.argsort(visit_time)

def _make_number_of_donors_array_to_n(r, p):

    """Number of donors for each node.

    Creates and returns an array containing the number of donors for each node.

    Parameters
    ----------
    r : ndarray size (np, q) where r[i,:] gives all receivers of node i. Each
        node recieves flow fom up to q donors.

    p : ndarray size (np, q) where p[i,v] give the proportion of flow going
        from node i to the receiver listed in r[i,v].

    Returns
    -------
    ndarray size (np)
        Number of donors for each node.

    Examples
    --------

    >>> import numpy as np
    >>> from landlab.components.flow_accum.flow_accum_to_n import(
    ... _make_number_of_donors_array_to_n)
    >>> r = np.array([[ 1,  2],
    ...               [ 4,  5],
    ...               [ 1,  5],
    ...               [ 6,  2],
    ...               [ 4, -1],
    ...               [ 4, -1],
    ...               [ 5,  7],
    ...               [ 4,  5],
    ...               [ 6,  7],
    ...               [ 7,  8]])
    >>> p = np.array([[ 0.6,   0.4 ],
    ...               [ 0.85,  0.15],
    ...               [ 0.65,  0.35],
    ...               [ 0.9,   0.1 ],
    ...               [ 1.,    0.  ],
    ...               [ 1.,    0.  ],
    ...               [ 0.75,  0.25],
    ...               [ 0.55,  0.45],
    ...               [ 0.8,   0.2 ],
    ...               [ 0.95,  0.05]])
    >>> nd = _make_number_of_donors_array_to_n(r, p)
    >>> nd
    array([0, 2, 2, 0, 4, 4, 2, 3, 1, 0])
    """

    # Vectorized, DEJH, 5/20/14
#    np = len(r)
#    nd = numpy.zeros(np, dtype=int)
#    for i in range(np):
#        nd[r[i]] += 1

    # modified by KRB 10/31/2016 to support route to multiple.

    nd = numpy.zeros(r.shape[0], dtype=int)
    max_index = numpy.amax(r)

    # filter r based on p and flatten
    r_filter_flat = r.flatten()[p.flatten() > 0]

    nd[:(max_index + 1)] = numpy.bincount(r_filter_flat)
    return nd


def _make_delta_array_to_n(nd):
    r"""
    Function to create the delta array.

    Creates and returns the "delta" array, which is a list containing, for each
    node, the array index where that node's donor list begins.

    Parameters
    ----------
    nd : ndarray of int
        Number of donors for each node

    Returns
    -------
    ndarray of int
        Delta array

    Examples
    --------

    >>> import numpy as np
    >>> from landlab.components.flow_accum.flow_accum_to_n import(
    ... _make_delta_array_to_n)
    >>> nd = np.array([0, 2, 2, 0, 4, 4, 2, 3, 1, 0])
    >>> delta = _make_delta_array_to_n(nd)
    >>> delta
    array([ 0,  0,  2,  4,  4,  8,  12,  14, 17, 18, 18])
    >>> sum(nd) == max(delta)
    True
    """
    # np = len(nd)
    # delta = numpy.zeros(np+1, dtype=int)
    # delta[np] = np   # not np+1 as in B&W because here we number from 0
    # for i in range(np-1, -1, -1):
    #     delta[i] = delta[i+1] - nd[i]
    # return delta

    # DEJH efficient delooping (only a small gain)

    nt = sum(nd)
    np = len(nd)
    delta = numpy.zeros(np+1, dtype=int)
    delta.fill(nt)
    delta[-2::-1] -= numpy.cumsum(nd[::-1])

    return delta


def _make_array_of_donors_to_n(r, p, delta):

    """
    Creates and returns an array containing the IDs of donors for each node.

    Essentially, the array is a series of lists (not in the Python list object
    sense) of IDs for each node. See Braun & Willett (2012) for details.

    The example below is from Braun & Willett (2012), and produces D_i in their
    Table 1 (except that here the ID numbers are one less, because we number
    indices from zero).

    Vectorized - inefficiently! - DEJH, 5/20/14

    Examples
    --------
    >>> import numpy as np
    >>> from landlab.components.flow_accum.flow_accum_to_n import(
    ... _make_array_of_donors_to_n)
    >>> r = np.array([[ 1,  2],
    ...               [ 4,  5],
    ...               [ 1,  5],
    ...               [ 6,  2],
    ...               [ 4, -1],
    ...               [ 4, -1],
    ...               [ 5,  7],
    ...               [ 4,  5],
    ...               [ 6,  7],
    ...               [ 7,  8]])
    >>> p = np.array([[ 0.6,   0.4 ],
    ...               [ 0.85,  0.15],
    ...               [ 0.65,  0.35],
    ...               [ 0.9,   0.1 ],
    ...               [ 1.,    0.  ],
    ...               [ 1.,    0.  ],
    ...               [ 0.75,  0.25],
    ...               [ 0.55,  0.45],
    ...               [ 0.8,   0.2 ],
    ...               [ 0.95,  0.05]])
    >>> delta = np.array([ 0,  0,  2,  4,  4,  8,  12,  14, 17, 18, 18])
    >>> D = _make_array_of_donors_to_n(r, p, delta)
    >>> D
    array([0, 2, 0, 3, 1, 4, 5, 7, 6, 1, 2, 7, 3, 8, 9, 6, 8, 9])
    """
    np = r.shape[0]
    q = r.shape[1]
    nt = delta[-1]

    w = numpy.zeros(np, dtype=int)
    D = numpy.zeros(nt, dtype=int)
    for v in range(q):
        for i in range(np):
            ri = r[i, v]
            if p[i, v] > 0:
                ind = delta[ri]+w[ri]
                D[ind] = i
                w[ri] += 1

    return D

    # DEJH notes that for reasons he's not clear on, this looped version is
    # actually much slower!
    # D = numpy.zeros(np, dtype=int)
    # wri_fin = numpy.bincount(r)
    # wri_fin_nz = wri_fin.nonzero()[0]
    # wri_fin_nz_T = wri_fin_nz.reshape((wri_fin_nz.size,1))
    # logical = numpy.tile(r,(wri_fin_nz.size,1))==wri_fin_nz_T
    # cum_logical = numpy.cumsum(logical, axis=1)
    # wri = numpy.sum(numpy.where(logical, cum_logical-1,0) ,axis=0)
    # D_index = delta[r] + wri
    # D[D_index] = numpy.arange(r.size)
    # return D


def make_ordered_node_array_to_n(receiver_nodes,
                                 receiver_proportion):

    """Create an array of node IDs.

    Creates and returns an array of node IDs that is arranged in order from
    downstream to upstream.

    The lack of a leading underscore is meant to signal that this operation
    could be useful outside of this module!

    Examples
    --------
    >>> import numpy as np
    >>> from landlab.components.flow_accum.flow_accum_to_n import(
    ... make_ordered_node_array_to_n)
    >>> r = np.array([[ 1,  2],
    ...               [ 4,  5],
    ...               [ 1,  5],
    ...               [ 6,  2],
    ...               [ 4, -1],
    ...               [ 4, -1],
    ...               [ 5,  7],
    ...               [ 4,  5],
    ...               [ 6,  7],
    ...               [ 7,  8]])
    >>> p = np.array([[ 0.6,   0.4 ],
    ...               [ 0.85,  0.15],
    ...               [ 0.65,  0.35],
    ...               [ 0.9,   0.1 ],
    ...               [ 1.,    0.  ],
    ...               [ 1.,    0.  ],
    ...               [ 0.75,  0.25],
    ...               [ 0.55,  0.45],
    ...               [ 0.8,   0.2 ],
    ...               [ 0.95,  0.05]])
    >>> s = make_ordered_node_array_to_n(r, p)
    >>> s[0] == 4
    True
    >>> s[1] == 5
    True
    >>> s[9] == 9
    True
    >>> len(set([1, 7])-set(s[2:4]))
    0
    >>> len(set([2, 6])-set(s[4:6]))
    0
    >>> len(set([0, 3, 8])-set(s[6:9]))
    0
    """
    node_id = numpy.arange(receiver_nodes.shape[0])
    baselevel_nodes = numpy.where(node_id==receiver_nodes[:,0])[0]
    nd = _make_number_of_donors_array_to_n(receiver_nodes, receiver_proportion)
    delta = _make_delta_array_to_n(nd)
    D = _make_array_of_donors_to_n(receiver_nodes, receiver_proportion, delta)
    dstack = _DrainageStack_to_n(delta, D)
    construct_it = dstack.construct__stack

    construct_it(baselevel_nodes)  # don't think this is a bottleneck, so no C++
    return dstack.s



def find_drainage_area_and_discharge_to_n(s, r, p, node_cell_area=1.0,
                                          runoff=1.0, boundary_nodes=None):

    """Calculate the drainage area and water discharge at each node.

    Parameters
    ----------
    s : ndarray of int
        Ordered (downstream to upstream) array of node IDs
    r : ndarray size (np, q) where r[i, :] gives all receivers of node i. Each
        node recieves flow fom up to q donors.
    p : ndarray size (np, q) where p[i, v] give the proportion of flow going
        from node i to the receiver listed in r[i, v].
    node_cell_area : float or ndarray
        Cell surface areas for each node. If it's an array, must have same
        length as s (that is, the number of nodes).
    runoff : float or ndarray
        Local runoff rate at each cell (in water depth per time). If it's an
        array, must have same length as s (that is, the number of nodes).

    Returns
    -------
    tuple of ndarray
        drainage area and discharge

    Notes
    -----
    -  If node_cell_area not given, the output drainage area is equivalent
       to the number of nodes/cells draining through each point, including
       the local node itself.
    -  Give node_cell_area as a scalar when using a regular raster grid.
    -  If runoff is not given, the discharge returned will be the same as
       drainage area (i.e., drainage area times unit runoff rate).
    -  If using an unstructured Landlab grid, make sure that the input
       argument for node_cell_area is the cell area at each NODE rather than
       just at each CELL. This means you need to include entries for the
       perimeter nodes too. They can be zeros.

    Examples
    --------
    >>> import numpy as np
    >>> from landlab.components.flow_accum.flow_accum_to_n import(
    ... find_drainage_area_and_discharge_to_n)
    >>> r = np.array([[ 1,  2],
    ...               [ 4,  5],
    ...               [ 1,  5],
    ...               [ 6,  2],
    ...               [ 4, -1],
    ...               [ 4, -1],
    ...               [ 5,  7],
    ...               [ 4,  5],
    ...               [ 6,  7],
    ...               [ 7,  8]])
    >>> p = np.array([[ 0.6,   0.4 ],
    ...               [ 0.85,  0.15],
    ...               [ 0.65,  0.35],
    ...               [ 0.9,   0.1 ],
    ...               [ 1.,    0.  ],
    ...               [ 1.,    0.  ],
    ...               [ 0.75,  0.25],
    ...               [ 0.55,  0.45],
    ...               [ 0.8,   0.2 ],
    ...               [ 0.95,  0.05]])
    >>> s = np.array([4, 5, 1, 7, 2, 6, 0, 8, 3, 9])
    >>> a, q = find_drainage_area_and_discharge_to_n(s, r, p)
    >>> a
    array([  1.    ,   2.575 ,   1.5   ,   1.    ,  10.    ,   5.2465,
             2.74  ,   2.845 ,   1.05  ,   1.    ])
    >>> q
    array([  1.    ,   2.575 ,   1.5   ,   1.    ,  10.    ,   5.2465,
             2.74  ,   2.845 ,   1.05  ,   1.    ])
    """
    # Number of points
    np = r.shape[0]
    q = r.shape[1]

    # Initialize the drainage_area and discharge arrays. Drainage area starts
    # out as the area of the cell in question, then (unless the cell has no
    # donors) grows from there. Discharge starts out as the cell's local runoff
    # rate times the cell's surface area.
    drainage_area = numpy.zeros(np) + node_cell_area
    discharge = numpy.zeros(np) + node_cell_area*runoff

    # Optionally zero out drainage area and discharge at boundary nodes
    if boundary_nodes is not None:
        drainage_area[boundary_nodes] = 0
        discharge[boundary_nodes] = 0

    # Iterate backward through the list, which means we work from upstream to
    # downstream.
    for i in range(np-1, -1, -1):
        donor = s[i]
        for v in range(q):
            recvr = r[donor, v]
            proportion = p[donor, v]
            if proportion > 0:
                if donor != recvr:
                    drainage_area[recvr] += proportion*drainage_area[donor]
                    discharge[recvr] += proportion*discharge[donor]

#        donors = s[i]
#        #print donors
#        recvrs = r[donors, :].flatten()
#
#        if (set(donors)-set(recvrs[recvrs!=-1]))==set(donors):
#            recvrs = r[donors, :].flatten()
#
#            unique_recvrs=numpy.unique(recvrs)
#
#            proportions = p[donors, :].flatten()
#
#            new_da=proportions*numpy.repeat(drainage_area[donors], q)
#            new_di=proportions*numpy.repeat(discharge[donors], q)
#
#            for u_r in unique_recvrs:
#                ur_ind=np.where(recvrs==u_r)
#
#                drainage_area[u_r] += numpy.sum(new_da[ur_ind])
#                discharge[u_r] += numpy.sum(new_di[ur_ind])

    return drainage_area, discharge


def flow_accumulation_to_n(receiver_nodes,
                           receiver_proportions,
                           node_cell_area=1.0,
                           runoff_rate=1.0,
                           boundary_nodes=None):

    """Calculate drainage area and (steady) discharge.

    Calculates and returns the drainage area and (steady) discharge at each
    node, along with a downstream-to-upstream ordered list (array) of node IDs.

    Examples
    --------
    >>> import numpy as np
    >>> from landlab.components.flow_accum.flow_accum_to_n import(
    ... flow_accumulation_to_n)
    >>> r = np.array([[ 1,  2],
    ...               [ 4,  5],
    ...               [ 1,  5],
    ...               [ 6,  2],
    ...               [ 4, -1],
    ...               [ 4, -1],
    ...               [ 5,  7],
    ...               [ 4,  5],
    ...               [ 6,  7],
    ...               [ 7,  8]])
    >>> p = np.array([[ 0.6,   0.4 ],
    ...               [ 0.85,  0.15],
    ...               [ 0.65,  0.35],
    ...               [ 0.9,   0.1 ],
    ...               [ 1.,    0.  ],
    ...               [ 1.,    0.  ],
    ...               [ 0.75,  0.25],
    ...               [ 0.55,  0.45],
    ...               [ 0.8,   0.2 ],
    ...               [ 0.95,  0.05]])
    >>> a, q, s = flow_accumulation_to_n(r, p)
    >>> a
    array([  1.    ,   2.575 ,   1.5   ,   1.    ,  10.    ,   5.2465,
             2.74  ,   2.845 ,   1.05  ,   1.    ])
    >>> q
    array([  1.    ,   2.575 ,   1.5   ,   1.    ,  10.    ,   5.2465,
             2.74  ,   2.845 ,   1.05  ,   1.    ])
    >>> s[0] == 4
    True
    >>> s[1] == 5
    True
    >>> s[9] == 9
    True
    >>> len(set([1, 7])-set(s[2:4]))
    0
    >>> len(set([2, 6])-set(s[4:6]))
    0
    >>> len(set([0, 3, 8])-set(s[6:9]))
    0
    """

    assert receiver_nodes.shape == receiver_proportions.shape, \
        'r and p arrays are not the same shape'

    s = make_ordered_node_array_to_n(receiver_nodes, receiver_proportions)
    # Note that this ordering of s DOES INCLUDE closed nodes. It really
    # shouldn't!
    # But as we don't have a copy of the grid accessible here, we'll solve this
    # problem as part of route_flow_dn.

    a, q = find_drainage_area_and_discharge_to_n(
        s, receiver_nodes, receiver_proportions, node_cell_area, runoff_rate,
        boundary_nodes)

    return a, q, s


if __name__ == '__main__':
    import doctest
    doctest.testmod()
