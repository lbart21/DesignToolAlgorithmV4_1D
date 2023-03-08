"""
Function:
Author: Luke Bartholomew
Edits:
"""
from Algorithms.DT_1D_V4.flux_calculators.fluid_fluxes import AUSMPlusupORIGINAL, AUSMPlusupPAPER
from Algorithms.DT_1D_V4.reconstruction.reconstruction import get_reconstruction
from Algorithms.DT_1D_V4.reconstruction.reconstruction_hierarchy \
            import LEFT_RECONSTRUCTION_HIERARCHY, RIGHT_RECONSTRUCTION_HIERARCHY
from Algorithms.DT_1D_V4.reconstruction.locate_neighbouring_cell_indices import find_idx_of_cell_recursively

class SinglePhaseMultiSpeciesNonUniformMassfInterface():
    def __init__(self, interface_id, nL, nR, flux_scheme, recon_scheme, \
                        limiter, recon_props, update_from) -> None:
        self.interface_id = interface_id
        self.nL = nL
        self.nR = nR

        self.flux_scheme = flux_scheme
        self.flux_flag = True
        self.recon_scheme = recon_scheme
        self.limiter = limiter
        self.recon_props = recon_props
        self.update_from = update_from
        self.stencil_been_formed = False

        self.lft_state = None
        self.rght_state = None

        self.boundary_fluxes = {}
    
    def fill_geometry(self, geometry):
        self.geo = geometry
    
    def complete_interface_methods(self, **kwargs):
        cell_array = kwargs["cell_array"]
        interface_array = kwargs["interface_array"]
        map_cell_id_to_west_interface_idx = kwargs["map_cell_id_to_west_interface_idx"]
        map_cell_id_to_east_interface_idx = kwargs["map_cell_id_to_east_interface_idx"]
        map_interface_id_to_west_cell_idx = kwargs["map_interface_id_to_west_cell_idx"]
        map_interface_id_to_east_cell_idx = kwargs["map_interface_id_to_east_cell_idx"]
        dt_inv = kwargs["dt_inv"]

        if self.flux_flag:
            if not self.stencil_been_formed:
                self.form_lists_of_stencil_indices(map_cell_id_to_west_interface_idx = map_cell_id_to_west_interface_idx, \
                                                map_cell_id_to_east_interface_idx = map_cell_id_to_east_interface_idx, \
                                                map_interface_id_to_west_cell_idx = map_interface_id_to_west_cell_idx, \
                                                map_interface_id_to_east_cell_idx = map_interface_id_to_east_cell_idx, \
                                                cell_array = cell_array, interface_array = interface_array)
                self.stencil_been_formed = True

            self.reconstruct_states(cell_array = cell_array)
            self.calculate_fluxes()
            self.update_neighbouring_cells_cqs(dt_inv = dt_inv, cell_array = cell_array)
    
    def reconstruct_states(self, cell_array):
        if self.flux_flag is True: #Do reconstruction
            #print("\n")
            #print("ID: ", self.interface_id)
            #print("Recon scheme", self.recon_scheme)
            #print("lft_stencil_idxs: ", self.lft_stencil_idxs)
            #print("rght_stencil_idxs: ", self.rght_stencil_idxs)
            for prop in self.recon_props:
                qL_stencil, dxL_stencil, \
                qR_stencil, dxR_stencil = self.get_stencils(prop = prop, cell_array = cell_array)
                #print(qL_stencil, dxL_stencil, qR_stencil, dxR_stencil)
                if prop == "massf":
                    qL_stencil = list(map(list, zip(*qL_stencil)))
                    qR_stencil = list(map(list, zip(*qR_stencil)))
                    #print("qL_stencil in massf: ", qL_stencil)
                    #print("qR_stencil in massf: ", qR_stencil)
                    n_species = len(qL_stencil)
                    lft_reconstructed_massf = [None] * n_species
                    rght_reconstructed_massf = [None] * n_species
                    
                    for species_idx, massf_species in enumerate(qL_stencil): 
                        #print("Left species mass fractions: ", qL_stencil[species_idx])
                        #print("Right species mass fractions: ", qR_stencil[species_idx])
                        lft_prop, rght_prop = get_reconstruction(reconstruction = self.recon_scheme[0], limiter = self.limiter, \
                                                        qL_stencil = qL_stencil[species_idx], dxL_stencil = dxL_stencil, \
                                                        qR_stencil = qR_stencil[species_idx], dxR_stencil = dxR_stencil)
                        lft_reconstructed_massf[species_idx] = lft_prop
                        rght_reconstructed_massf[species_idx] = rght_prop

                    setattr(self.lft_state.fluid_state, prop, lft_reconstructed_massf)
                    setattr(self.rght_state.fluid_state, prop, rght_reconstructed_massf)

                elif prop == "vel_x":
                    lft_prop, rght_prop = get_reconstruction(reconstruction = self.recon_scheme[0], limiter = self.limiter, \
                                                        qL_stencil = qL_stencil, dxL_stencil = dxL_stencil, \
                                                        qR_stencil = qR_stencil, dxR_stencil = dxR_stencil)
                    self.lft_state.vel_x = lft_prop
                    self.rght_state.vel_x = rght_prop
                else:
                    lft_prop, rght_prop = get_reconstruction(reconstruction = self.recon_scheme[0], limiter = self.limiter, \
                                                        qL_stencil = qL_stencil, dxL_stencil = dxL_stencil, \
                                                        qR_stencil = qR_stencil, dxR_stencil = dxR_stencil)
                    setattr(self.lft_state.fluid_state, prop, lft_prop)
                    setattr(self.rght_state.fluid_state, prop, rght_prop)

            if self.update_from == "pT":
                self.lft_state.fluid_state.update_thermo_from_pT()
                self.rght_state.fluid_state.update_thermo_from_pT()
    
    def calculate_fluxes(self):
        if self.flux_flag is True:
            #print(self.LftStencilIdxs, self.RghtStencilIdxs)
            if self.flux_scheme == "AUSMPlusUPOriginal":
                self.boundary_fluxes = AUSMPlusupORIGINAL(lft_flow_state = self.lft_state, rght_flow_state = self.rght_state, \
                                                            multi_phase = False, multi_species_flux = True).fluxes

            elif self.flux_scheme == "AUSMPlusUPPaper":
                self.boundary_fluxes = AUSMPlusupPAPER(  a_L_forMa = self.lft_state.fluid_state.a,  a_L = self.lft_state.fluid_state.a, \
                                                        p_L = self.lft_state.fluid_state.p,        u_L = self.lft_state.fluid_state.u, \
                                                        rho_L = self.lft_state.fluid_state.rho,    vel_x_L = self.lft_state.vel_x, \
                                                        a_R_forMa = self.rght_state.fluid_state.a, a_R = self.rght_state.fluid_state.a, \
                                                        p_R = self.rght_state.fluid_state.p,       u_R = self.rght_state.fluid_state.u, \
                                                        rho_R = self.rght_state.fluid_state.rho,   vel_x_R = self.rght_state.vel_x).fluxes
        
        else:
            pass
    
    def update_neighbouring_cells_cqs(self, dt_inv, cell_array):
        if self.flux_flag is True:
            west_cell = cell_array[self.lft_stencil_idxs[0]]
            if west_cell.interior_cell_flag: # Check if cell is a ghost cell as we don't want to update the conserved properties of ghost cells
                #print(dt_inv, self.geo["A"], self.boundaryFluxes["mass"], westCell.geo["dV"])
                west_cell.cqs["mass"] -= dt_inv * self.geo["A"] * self.boundary_fluxes["mass"] / west_cell.geo["dV"]
                west_cell.cqs["xMom"] -= dt_inv * self.geo["A"] * self.boundary_fluxes["xMom"] / west_cell.geo["dV"]
                west_cell.cqs["xMom"] -= dt_inv * west_cell.geo["A_c"] * self.boundary_fluxes["p"] / west_cell.geo["dV"]
                west_cell.cqs["energy"] -= dt_inv * self.geo["A"] * self.boundary_fluxes["energy"] / west_cell.geo["dV"]
                n_species = len(self.boundary_fluxes["massf"])
                for species in range(n_species):
                    west_cell.cqs["spcs_mass"][species] -= dt_inv * self.geo["A"] * self.boundary_fluxes["massf"][species] / west_cell.geo["dV"]

            east_cell = cell_array[self.rght_stencil_idxs[0]]
            if east_cell.interior_cell_flag: # Check if cell is a ghost cell as we don't want to update the conserved properties of ghost cells
                east_cell.cqs["mass"] += dt_inv * self.geo["A"] * self.boundary_fluxes["mass"] / east_cell.geo["dV"]
                east_cell.cqs["xMom"] += dt_inv * self.geo["A"] * self.boundary_fluxes["xMom"] / east_cell.geo["dV"]
                east_cell.cqs["xMom"] += dt_inv * east_cell.geo["A_c"] * self.boundary_fluxes["p"] / east_cell.geo["dV"]
                east_cell.cqs["energy"] += dt_inv * self.geo["A"] * self.boundary_fluxes["energy"] / east_cell.geo["dV"]
                n_species = len(self.boundary_fluxes["massf"])
                for species in range(n_species):
                    east_cell.cqs["spcs_mass"][species] += dt_inv * self.geo["A"] * self.boundary_fluxes["massf"][species] / east_cell.geo["dV"]
        else:
            pass
    
    def get_stencils(self, prop, cell_array):
        ### Fill left stencil
        qL_stencil = [None] * len(self.lft_stencil_idxs)
        dxL_stencil = [None] * len(self.lft_stencil_idxs)
        for ind, lft_cell_idx in enumerate(self.lft_stencil_idxs):
            cell_L = cell_array[lft_cell_idx]
            if prop == "vel_x":
                qL_stencil[ind] = cell_L.flow_state.vel_x
            else:
                qL_stencil[ind] = getattr(cell_L.flow_state.fluid_state, prop)
            dxL_stencil[ind] = cell_L.geo["dx"]

        ### Fill right stencil
        qR_stencil = [None] * len(self.rght_stencil_idxs)
        dxR_stencil = [None] * len(self.rght_stencil_idxs)
        for ind, rght_cell_idx in enumerate(self.rght_stencil_idxs):
            cell_R = cell_array[rght_cell_idx]
            if prop == "vel_x":
                qR_stencil[ind] = cell_R.flow_state.vel_x
            else:
                qR_stencil[ind] = getattr(cell_R.flow_state.fluid_state, prop)
            dxR_stencil[ind] = cell_R.geo["dx"]
            
        return qL_stencil, dxL_stencil, qR_stencil, dxR_stencil
    
    def form_lists_of_stencil_indices(self, map_cell_id_to_west_interface_idx, map_cell_id_to_east_interface_idx, \
                                        map_interface_id_to_west_cell_idx, map_interface_id_to_east_cell_idx, cell_array, interface_array):
        #print("")
        #print("interface_id: ", self.interface_id)
        self.lft_stencil_idxs = [None] * self.recon_scheme[1][0]
        self.rght_stencil_idxs = [None] * self.recon_scheme[1][1]
        #print("Expected number of cells to the left:", self.recon_scheme[1][0])
        #print("Expected number of cells to the right:", self.recon_scheme[1][1])
        for lft_stencil_idx in range(self.recon_scheme[1][0]):
            cell_idx, hit_bad_interface_left = find_idx_of_cell_recursively(interface_id = self.interface_id, recursion_depth = lft_stencil_idx + 1, \
                                                direction = "West", map_interface_id_to_east_cell_idx = map_interface_id_to_east_cell_idx, \
                                                cell_array = cell_array, map_cell_id_to_east_interface_idx = map_cell_id_to_east_interface_idx, \
                                                map_interface_id_to_west_cell_idx = map_interface_id_to_west_cell_idx, \
                                                map_cell_id_to_west_interface_idx = map_cell_id_to_west_interface_idx, \
                                                interface_array = interface_array)
            #print("Left side: cell_idx: ", cell_idx, "hit_bad_interface_left: ", hit_bad_interface_left)
            if hit_bad_interface_left:
                current_reconstruction_indx_lft = LEFT_RECONSTRUCTION_HIERARCHY.index(self.recon_scheme)
                new_reconstruction_indx = current_reconstruction_indx_lft + 1
                print("Reconstruction scheme being changed:")
                print("Original scheme:", self.recon_scheme)
                self.recon_scheme = LEFT_RECONSTRUCTION_HIERARCHY[new_reconstruction_indx]
                print("New scheme:", self.recon_scheme)
                break
                
            else:
                self.lft_stencil_idxs[lft_stencil_idx] = cell_idx #In order of [L_Idx0, L_Idx1, ...]
        if hit_bad_interface_left:
            print("Redoing form_lists_of_stencil_indices function call due to left direction error")
            self.form_lists_of_stencil_indices(map_cell_id_to_west_interface_idx = map_cell_id_to_west_interface_idx, \
                                                map_cell_id_to_east_interface_idx = map_cell_id_to_east_interface_idx, \
                                                map_interface_id_to_west_cell_idx = map_interface_id_to_west_cell_idx, \
                                                map_interface_id_to_east_cell_idx = map_interface_id_to_east_cell_idx, \
                                                cell_array = cell_array, interface_array = interface_array)
            return
        
        for rght_stencil_idx in range(self.recon_scheme[1][1]):
            cell_idx, hit_bad_interface_right = find_idx_of_cell_recursively(interface_id = self.interface_id, recursion_depth = rght_stencil_idx + 1, \
                                                direction = "East", map_interface_id_to_east_cell_idx = map_interface_id_to_east_cell_idx, \
                                                cell_array = cell_array, map_cell_id_to_east_interface_idx = map_cell_id_to_east_interface_idx, \
                                                map_interface_id_to_west_cell_idx = map_interface_id_to_west_cell_idx, \
                                                map_cell_id_to_west_interface_idx = map_cell_id_to_west_interface_idx, \
                                                interface_array = interface_array)
            #print("Right side: cell_idx: ", cell_idx, "hit_bad_interface_right: ", hit_bad_interface_right)
            if hit_bad_interface_right:
                current_reconstruction_indx_rght = RIGHT_RECONSTRUCTION_HIERARCHY.index(self.recon_scheme)
                new_reconstruction_indx = current_reconstruction_indx_rght + 1
                print("Reconstruction scheme being changed:")
                print("Original scheme:", self.recon_scheme)
                self.recon_scheme = RIGHT_RECONSTRUCTION_HIERARCHY[new_reconstruction_indx]
                print("New scheme:", self.recon_scheme)
                break
                
            else:
                self.rght_stencil_idxs[rght_stencil_idx] = cell_idx #In order of [R_Idx0, R_Idx1, ...]
        
        if hit_bad_interface_right:
            print("Redoing form_lists_of_stencil_indices function call due to right direction error")
            self.form_lists_of_stencil_indices(map_cell_id_to_west_interface_idx = map_cell_id_to_west_interface_idx, \
                                                map_cell_id_to_east_interface_idx = map_cell_id_to_east_interface_idx, \
                                                map_interface_id_to_west_cell_idx = map_interface_id_to_west_cell_idx, \
                                                map_interface_id_to_east_cell_idx = map_interface_id_to_east_cell_idx, \
                                                cell_array = cell_array, interface_array = interface_array)
            return
        
            