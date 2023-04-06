"""
Function:
Author: Luke Bartholomew
Edits:
"""
import numpy as np
class SinglePhaseMultiSpeciesFiniteRateReactivePipeCell():
    def __init__(self, cell_id, label) -> None:
        self.geo = {}
        self.flow_state = None
        self.reactor_model = None
        self.cell_id = cell_id
        self.label = label
        self.phase = "Single"
        self.interior_cell_flag = True

        self.dt_suggest = 1e-11

        self.cqs = {
            "mass"      : 0.0,
            "xMom"      : 0.0,
            "energy"    : 0.0,
            "spcs_mass" : []
        }
    
    def fill_geometry(self, geometry):
        self.geo = geometry
    
    def decode_to_primative_properties(self):
        if self.interior_cell_flag:
            print("species mass at start of decoding:", self.cqs["spcs_mass"])
            print("Mass fractions at start of decoding:", self.flow_state.fluid_state.massf)
            rho = self.cqs["mass"]
            d_inv = 1.0 / rho
            rho_tol = 1e-6
            
            for ind, spcs_mass in enumerate(self.cqs["spcs_mass"]):
                if spcs_mass < 0.0:
                    self.cqs["spcs_mass"][ind] = 0.0
            rho_sum = sum(self.cqs["spcs_mass"])
            if abs(rho - rho_sum) > rho_tol:
                print("Too large of an error between conserved quantity mass and sum of species mass")
            for ind, spcs_mass in enumerate(self.cqs["spcs_mass"]):
                self.cqs["spcs_mass"][ind] *= rho / rho_sum
            

            massf = (np.array(self.cqs["spcs_mass"]) * d_inv).tolist()
            
            self.flow_state.fluid_state.massf = massf
            print("Mass fractions at end of decoding:", self.flow_state.fluid_state.massf)
            self.flow_state.fluid_state.rho = rho
            vel_x = self.cqs["xMom"] * d_inv
            self.flow_state.vel_x = vel_x
            u = self.cqs["energy"] * d_inv
            u -= 0.5 * vel_x ** 2.0
            self.flow_state.fluid_state.u = u
            #print("Printing fluid state props before prop update, after decoding")
            #print("rho: ", self.flow_state.fluid_state.rho, "p: ", self.flow_state.fluid_state.p, \
                        #"T: ", self.flow_state.fluid_state.T, "massf: ", self.flow_state.fluid_state.massf)
            self.flow_state.fluid_state.update_thermo_from_rhou()
            #print("Printing fluid state props after prop update, after decoding")
            #print("rho: ", self.flow_state.fluid_state.rho, "p: ", self.flow_state.fluid_state.p, \
                        #"T: ", self.flow_state.fluid_state.T, "massf: ", self.flow_state.fluid_state.massf)
            self.flow_state.fluid_state.update_sound_speed()
        
    def initialise_conserved_quantities(self):
        self.cqs["mass"] = self.flow_state.fluid_state.rho
        self.cqs["xMom"] = self.flow_state.fluid_state.rho * self.flow_state.vel_x
        self.cqs["energy"] = self.flow_state.fluid_state.rho * \
                                                    (self.flow_state.fluid_state.u + 0.5 * self.flow_state.vel_x ** 2)
        self.cqs["spcs_mass"] = (self.flow_state.fluid_state.rho * np.array(self.flow_state.fluid_state.massf)).tolist()

    def max_allowable_dt(self, cfl):
        return cfl * self.geo["dx"] / (abs(self.flow_state.vel_x) + self.flow_state.fluid_state.a)

    def complete_cell_methods(self, **kwargs):
        if self.interior_cell_flag:
            print("Species mass at start of cell method:", self.cqs["spcs_mass"])
            print("Mass fractions at start of cell method:", self.flow_state.fluid_state.massf)
            dt_inv = kwargs["dt_inv"]
            
            #print("Printing fluid state props before reactor time stepping")
            #print("rho: ", self.flow_state.fluid_state.rho, "p: ", self.flow_state.fluid_state.p, \
                    #"T: ", self.flow_state.fluid_state.T, "massf: ", self.flow_state.fluid_state.massf)
            self.dt_suggest = self.reactor_model.update_state(gstate = self.flow_state.fluid_state, \
                                                                t_interval = dt_inv, dt_suggest = self.dt_suggest)
            #print("massf:", self.flow_state.fluid_state.massf)
            #print("Printing fluid state props after reactor time stepping")
            #print("rho: ", self.flow_state.fluid_state.rho, "p: ", self.flow_state.fluid_state.p, \
                    #"T: ", self.flow_state.fluid_state.T, "massf: ", self.flow_state.fluid_state.massf)
            self.reinitialise_massf_conserved_quantity()
            print("Species mass at end of cell method:", self.cqs["spcs_mass"])
            print("Mass fractions at end of cell method:", self.flow_state.fluid_state.massf)
        
    def decode_to_primative_properties_after_interface_methods(self):
        self.decode_to_primative_properties()

    def decode_to_primative_properties_after_cell_methods(self):
        self.decode_to_primative_properties()
    
    def reinitialise_massf_conserved_quantity(self):
        self.cqs["spcs_mass"] = (self.flow_state.fluid_state.rho * np.array(self.flow_state.fluid_state.massf)).tolist()