#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""

In these convergence tests, we set up a displacement field, evaluate stress 
intensity factors (by the displacement correlation method) and compare against 
the analytical solution. The test is performed in two and three dimensions for 
cartesian and simplex grids. 
The domain contains a single immersed through-the-thickness fracture. For the 
simplex grid, inclination axis is described by the angle beta. A normal 
traction of sigma is applied on two sides. Thanks to symmetry, only half of the 
original domain needs to be simulated. 
The test case is described in more detail as case (i) in section 6.1 of 
Nejati et al., On the use of quarter-point tetrahedral finite elements in 
linear elastic fracture mechanics, 2015. 
 
A simplified test version is found in the integration test 
test_displacement_correlation_sif_computation.py. There, the tests are run for 
only a single (rather coarse) mesh. 
""" 
 
import scipy.sparse as sps 
import numpy as np 
import matplotlib.pyplot as plt 
 
import porepy as pp 
 
from test.integration.setup_mixed_dimensional_grids import set_bc_mech_tension_sneddon 
 
from porepy.numerics.linalg.linsolve import Factory as LSFactory 
 
 
 
# -----cartesian_2d-----------------------------------------------------------# 
def cartesian_2d(n_cells, length, height, a, kw={}, fracture=True): 
    # Make grid bucket and assign data 
 
    gb = pp.meshing.cart_grid(fracture_2d(length, height, a, beta, fracture), 
                              n_cells, physdims=[length, height]) 
 
    print('lower-dim cartesian cells ', gb.grids_of_dimension(1)[0].num_cells) 
    print('higher-dim cartesian cells ', gb.grids_of_dimension(2)[0].num_cells) 
    # Discretize, solve and evaluate sifs. 
 
    # Analytical solution and error evaluation. 
    return gb 
 
 
# -----simplex_2d-------------------------------------------------------------# 
 
def simplex_2d(h, length, height, a, beta, folder_name, from_gmsh=False, 
               fracture=True, kw={}): 
    # Make grid bucket and assign data 
 
    box = {'xmin': 0, 'ymin': 0, 'xmax': length, 'ymax': height} 
    mesh_kwargs = {} 
    h_ideal = np.array([h, h, h, h, h / 3]) 
    fn = folder_name + '/nc_equals_'# + str(int(h)) 
    mesh_kwargs = {'mesh_mode': 'weighted', 'h_ideal': h_ideal, 
                                'h_min': 1 / 199 * h, 
                                'file_name': fn, 'from_gmsh': from_gmsh} 
    f = fracture_2d(length, height, a, beta, fracture) 
    gb = pp.meshing.simplex_grid(f, box, **mesh_kwargs) 
#    gb = simplex.triangle_grid_from_gmsh(fn) 
 
    return gb 
 
def fracture_2d(length, height, a, beta, fracture): 
    if fracture: 
        y_0 = height / 2 - a * np.cos(beta) 
        x_0 = length / 2 - a * np.sin(beta) 
 
        y_1 = height / 2 + a * np.cos(beta) 
        x_1 = length / 2 + a * np.sin(beta) 
        f = [np.array([[x_0, x_1], 
                      [y_0, y_1]])] 
    else: 
        f = [] 
    return f 
def fracture_3d(beta, t): 
 
    z_0 = height / 2 - a * np.cos(beta) 
    x_0 = length / 2 - a * np.sin(beta) 
 
    z_1 = height / 2 + a * np.cos(beta) 
    x_1 = length / 2 + a * np.sin(beta) 
    f = np.array([[x_0, x_1, x_1, x_0], 
                  [0, 0, 2 * t, 2 * t], 
                  [z_0, z_1, z_1, z_0]]) 
    return [f] 
 
def fracture_penny(beta, t, n_points): 
    """ 
    Penny-shaped fracture at the center of the domain. 
    """ 
    major_axis = a 
    minor_axis = a 
    major_axis_angle = 0 
    strike_angle = 0 
    dip_angle = 0 
    f = pp.EllipticFracture(center, major_axis, minor_axis, 
                                  major_axis_angle, strike_angle, dip_angle, 
                                  num_points=n_points) 
    def PolyArea(x,y): 
        return 0.5*np.abs(np.dot(x,np.roll(y,1))-np.dot(y,np.roll(x,1))) 
    AA = PolyArea(f.p[0], f.p[1]) 
    print('Area ratio ', AA / (np.power(a, 2) * np.pi)) 
    return [f] 
 
# -----simplex_3d-------------------------------------------------------------# 
 
def simplex_3d(h, a, sigma, beta, t, kw={}): 
    # Make grid bucket and assign data 
    box = {'xmin': 0, 'ymin': 0, 'zmin': 0, 
           'xmax': length, 'ymax': 2 * t, 'zmax': height} 
    mesh_kwargs = {} 
    fn = folder_name + '/h_equals_' + str(h) 
    mesh_kwargs = {'h_ideal': h, 'h_min': 1e-3 * h, 'file_name': fn} 
 
    gb = pp.meshing.simplex_grid(fracture_3d(beta, t), box, **mesh_kwargs) 
    assign_parameters(gb, t) 
 
    return gb 
 
def simplex_3d_penny(h, a, sigma, beta, t, kw={}): 
    # Make grid bucket and assign data 
 
    box = {'xmin': 0, 'ymin': 0, 'zmin': 0, 
           'xmax': length, 'ymax': length, 'zmax': height} 
    mesh_kwargs = {} 
    fn = folder_name + '/h_equals_' + str(h) 
    mesh_kwargs = {'h_ideal': h, 'h_min': 1e-3 * h, 'file_name': fn} 
    npoints = 16 
 
    gb = pp.meshing.simplex_grid(fracture_penny(beta, t, npoints), box, **mesh_kwargs) 
    assign_parameters(gb, t) 
 
    return gb 
 
# -----analytical-------------------------------------------------------------# 
 
def analytical_displacements(gb, a, sigma=1): 
    """ 
    Analytical stress intensity factors for the through-the-thickness crack 
    problem in question. 
    """ 
    dim_h = gb.dim_max() 
    g_h = gb.grids_of_dimension(dim_h)[0] 
    d_h = gb.node_props(g_h) 
    mu = d_h['shear_modulus'] 
    nu = d_h['Poisson'] 
 
    last_ind = dim_h - 1 # pull in y direction for 2d, z in 3d 
    eta = compute_eta(g_h) 
 
    cons = (1 - nu) / mu * p0 * a * 2 
    if penny: 
        cons *= 2/np.pi 
    apertures = cons * np.sqrt(1 - np.power(eta / a, 2) ) 
 
    n_f = g_h.num_cells * dim_h 
    frac_ind_1 = np.arange(n_f + last_ind, n_f + g_h.frac_pairs.shape[1] * dim_h, dim_h) 
    frac_ind_2 = np.arange(last_ind + n_f + g_h.frac_pairs.shape[1] * dim_h, 
                           last_ind + n_f + g_h.frac_pairs.size * dim_h,  dim_h) 
    if not np.isclose(beta, np.pi / 2): 
        x_ind_1 = np.arange(n_f, n_f + g_h.frac_pairs.shape[1] * dim_h, dim_h) 
        x_ind_2 = np.arange(n_f + g_h.frac_pairs.shape[1] * dim_h, 
                            n_f + g_h.frac_pairs.size * dim_h,  dim_h) 
        frac_ind_1 = np.array([frac_ind_1, x_ind_1]) 
        frac_ind_2 = np.array([frac_ind_2, x_ind_2]) 
    frac_ind = np.array([frac_ind_1, frac_ind_2]) 
#    print('eta', eta) 
#    print('face area', g_h.face_areas[g_h.frac_pairs[0, -10:]]) 
#    print('face center', g_h.face_centers[:, g_h.frac_pairs[0, -10:]]) 
 
    return apertures, frac_ind, eta 
 
 
# -----utility functions------------------------------------------------------# 
 
def assign_parameters(gb, t=None): 
    """ 
    Utility function to assign the parameters to the node data of the grid 
    bucket. 
    """ 
    gb.add_node_props(['param']) 
    for g, d in gb: 
        param = pp.Parameters(g) 
        d['param'] = param 
 
    set_bc_mech_tension_sneddon(gb, p0=p0, height=height, length=length, 
                                beta = beta, t=t, penny=penny) 
 
 
def solve(gb, dim_h, kw={}): 
    """ 
    Discretize and solve mechanical problem, and evaluate stress intensity 
    factors by displacement correlation method. 
    """ 
    discr = pp.FracturedMpsa(given_traction=True) 
    g_h = gb.grids_of_dimension(dim_h)[0] 
    d_h = gb.node_props(g_h) 
 
    lhs, rhs = discr.matrix_rhs(g_h, d_h) 
#    ls = LSFactory() 
#    slv = ls.gmres(lhs) 
#    u, info = slv(rhs, maxiter=10000, restart=1500, tol=1e-8) 
    u = sps.linalg.spsolve(lhs, rhs) 
    aperture_analytical, dof_ind, eta = analytical_displacements(gb, a) 
    if np.isclose(beta, np.pi / 2): 
        aperture = np.absolute(np.diff(u[dof_ind], axis=0))[0] 
    elif np.isclose(beta, np.pi / 4): 
 
        u_right = u[dof_ind[0]] 
        u_left = u[dof_ind[1]] 
        d_u = u_right - u_left 
        aperture = np.linalg.norm(d_u, axis=0) 
    return aperture, aperture_analytical, u, eta 
 
 
 
def compute_eta(g_h): 
#    if not penny: 
#        return (g_h.face_centers[0, g_h.frac_pairs[0]] - length/2) 
#    else: 
    return cg.dist_point_pointset(g_h.face_centers[:, g_h.frac_pairs[0]], 
                                      center) 
def L2_norm(val, area): 
    return np.sqrt(np.sum(np.multiply(area, np.square(val)))) 
     
 
def L2_error(v_ref, v_approx, area): 
    enum = L2_norm(v_approx - v_ref, area) 
    denom = L2_norm(v_ref, area)  
    return enum / denom 
 
 
def run_multiple_and_plot(nc, function): 
    errors = [] 
    errors_I = [] 
    errors_max = [] 
    errors_el = [] 
    apertures = [] 
    apertures_a = [] 
    fracture_cells = [] 
    for item in nc: 
        gb = function(item) 
        g_h = gb.grids_of_dimension(gb.dim_max())[0] 
        assign_parameters(gb) 
        aperture, aperture_a, u, eta = solve(gb, gb.dim_max()) 
        assert np.all(aperture > 0) 
        areas = g_h.face_areas[g_h.frac_pairs[0]] 
        e = np.absolute(aperture_a - aperture)/np.max(aperture_a) 
         
         
        errors.append(L2_error(aperture_a, aperture, areas))#np.sqrt(np.sum(np.power(e, 2)) / np.sum(areas))) 
        errors_I.append(L2_norm(aperture_a - aperture, areas) / (np.sum(areas) * np.max(aperture_a))) 
        errors_max.append(np.max(e)) 
        i =  eta<(.9*a) 
        errors_el.append(L2_error(aperture_a[i], aperture[i], areas[i])) 
        apertures.append(aperture) 
        apertures_a.append(aperture_a) 
        fracture_cells.append(gb.grids_of_dimension(gb.dim_min())[0].num_cells) 
        if plot: 
            plot_against_eta(e, eta) 
            print('errors', errors) 
    errors = np.array(errors) 
    errors_el = np.array(errors_el) 
    errors_max = np.array(errors_max) 
    errors_I = np.array(errors_I) 
    if plot: 
        plt.figure() 
        plt.xlabel('Fracture cells') 
        plt.ylabel('E') 
        plt.title('Mean aperture error') 
 
        plt.loglog(fracture_cells, errors) 
        plt.loglog(fracture_cells, errors_max) 
        plt.loglog(fracture_cells, errors_el) 
        plt.loglog(fracture_cells, errors_I) 
        v = errors_el[0] * .4 
        i = 0 
        nc1 = fracture_cells[i] 
        nc2 = fracture_cells[i + 1] 
        f = nc2 / nc1 
        x = np.array([nc1, nc2, nc1, nc1]) 
        plt.loglog(x, [v, v/f, v/f, v], ls=':') 
        v = errors_el[1] * .4 
        i = 1 
        nc1 = fracture_cells[i] 
        nc2 = fracture_cells[i + 1] 
        f = np.power(nc2 / nc1, 2) 
        x = np.array([fracture_cells[i], fracture_cells[i+1], fracture_cells[i], fracture_cells[i]]) 
        plt.loglog(x, [v, v/f, v/f, v], ls=':') 
        plt.legend(['L2', 'Max', 'El', 'I', 'First order', 'Second order']) 
         
 
    save(gb, u, e, file_name, folder_name, export=export) 
    return errors, errors_max, errors_el, apertures, apertures_a, u, gb, e 
 
 
def plot_against_eta(e, eta): 
    plt.figure() 
    plt.title('Absolute aperture error along fracture') 
    aa = plt.gca() 
    aa.set_yscale('log') 
    aa.scatter(eta, e) 
    aa.set_xlabel('$\eta$') 
    aa.set_ylabel('E') 
     
     
def save(gb, u, errors, file_name, folder_name, export=True, sort_error=True): 
    if not export: 
        return 
    from porepy.viz import exporter 
    for g, d in gb: 
        if g.dim == gb.dim_max(): 
            disp = u[:g.dim * g.num_cells].reshape((g.dim, g.num_cells), 
                                                   order='F') 
            disp = np.append(disp, np.zeros(((3-g.dim), g.num_cells)), axis=0) 
            d['displacement'] = disp 
            d['error'] = np.zeros(g.num_cells) 
            n_digits = 10 
            cell_map = sm.ismember_rows( 
                    np.around(gb.grids_of_dimension(g.dim-1)[0].cell_centers, 
                              n_digits), 
                    np.around(g.face_centers[:, g.frac_pairs[0]], n_digits), 
                    sort=False, simple_version=True)[1] 
        else: 
            if sort_error: 
                d['error'] = errors[cell_map] 
            else: 
                d['error'] = errors 
            u_left = u[-gb.dim_max() * 2 * g.num_cells:-gb.dim_max() * g.num_cells] 
            u_right = u[-gb.dim_max() * g.num_cells:] 
            # only y component 
            u_left = u_left[np.arange(g.dim, u_left.size, gb.dim_max())] 
            u_right = u_right[np.arange(g.dim, u_right.size, gb.dim_max())] 
            u_f = np.array([u_right, u_left])[:, cell_map] 
            u_f = np.append(u_f, -np.diff(u_f, axis=0), axis=0) 
            d['displacement'] = u_f 
    e = exporter.Exporter(gb, file_name, folder_name) 
    e.write_vtk(data=['displacement', 'error']) 
 
 
if __name__ == '__main__': 
    plt.close('all') 
    penny = False 
    plot = True 
    export = False 
    file_name = 'displacement_and_aperture_error' 
    folder_name = 'aperture/sneddon/simplex_2d' 
    from_gmsh = True 
    # Geometry 
    height = 50 
    length = 50 
    center = np.array([length / 2, length / 2, 0]) 
    beta = np.pi / 2  # inclination from vertical axis 
    a = 3  # fracture radius 
    t = 5 # domain thickness 
    # Driving force 
    p0 = 1e-5 
 
 
    sigma = 1 
 
    # Number of cells, Cartesian case. 
    n_cells = np.array([40, 80, 160]) 
    n_cells = np.array([25, 50, 100, 200]) 
    # Cell size, simplex case. 
    h = np.array([4, 2, 1]) 
#    h = np.array([20, 11, 6]) 
    h = np.array([11, 4, 2]) 
#    h = np.array([2, .8]) 
    h = np.array([3, 2.2, 1.3, .65, .52, .36]) 
#    h = np.array([3, 2.2, .8]) 
#    h = np.array([14, 11, 11]) 
#    h = np.array([.65, .52]) 
    def cartesian_2d_of_nc(nc): 
        return cartesian_2d([2*nc, nc], length, height, a) 
    def simplex_2d_of_h(h): 
        return simplex_2d(h, length, height, a, beta, folder_name) 
    errors, errors_max, errors_el, apertures, apertures_a, u, gb, last_errors \ 
         = run_multiple_and_plot(h, simplex_2d_of_h) 
          
    save(gb, u, last_errors, file_name, folder_name, export=True, sort_error=True) 
#    errors, errors_max, apertures, apertures_a = run_multiple_and_plot(n_cells, cartesian_2d_of_nc) 
#    def simplex_3d_of_h(ms): 
#        if penny: 
#            return simplex_3d_penny(ms, a, sigma, beta, t) 
#        else: 
#            return simplex_3d(ms, a, sigma, beta, t) 
#    center = np.array([length / 2, length / 2, height / 2]) 
#    a = 2 
#    folder_name = 'aperture/sneddon/simplex_3d' 
#    h = np.array([8, 4]) # Factor 5 
##    e_3d, e_max_3d, apertures_3d, apertures_a_3d, u_3d \ 
##        = run_multiple_and_plot(h, simplex_3d_of_h) 
#    # Penny: 
#    penny = True 
#    a = 3 
#    h = np.array([14, 7]) # Factor 8 
#    folder_name = 'aperture/sneddon/simplex_3d_penny' 
##    e_pe, e_max_pe, apertures_pe, apertures_a_pe, u_pe \ 
##        = run_multiple_and_plot(h, simplex_3d_of_h) 
