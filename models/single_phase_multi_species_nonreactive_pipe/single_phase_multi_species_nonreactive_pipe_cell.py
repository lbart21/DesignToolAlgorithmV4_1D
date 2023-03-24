"""
Function:
Author: Luke Bartholomew
Edits:
"""
import sys
class SinglePhaseMultiSpeciesNonReactivePipeCell():
    def __init__(self, cell_id, label) -> None:
        self.geo = {}
        self.flow_state = None
        self.cell_id = cell_id
        self.label = label
        self.phase = "Single"
        self.interior_cell_flag = True

        self.cqs = {
            "mass"      : 0.0,
            "xMom"      : 0.0,
            "energy"    : 0.0
        }

        self.flow_state = None
    
    def fill_geometry(self, geometry):
        self.geo = geometry
    
    def decode_to_primative_properties(self):
        if self.interior_cell_flag:
            #print("Cell ID:", self.cell_id, "pos_x:", self.geo["pos_x"])
            #print("cqs:", self.cqs)
            new_density = self.cqs["mass"] 
            new_vel_x = self.cqs["xMom"] / self.cqs["mass"]
            new_u = self.cqs["energy"] / self.cqs["mass"] \
                                                            - 0.5 * new_vel_x ** 2.0
            self.flow_state.vel_x = new_vel_x
            self.flow_state.fluid_state.rho = new_density
            self.flow_state.fluid_state.u = new_u
            try:
                self.flow_state.fluid_state.update_thermo_from_rhou()
                self.flow_state.fluid_state.update_sound_speed()
            except:
                print("Failed to update props in conserved quanitity decoding")
                print("Cell ID:", self.cell_id, "pos_x:", self.geo["pos_x"])
                print("Conserved quantities:", self.cqs)
                print("Density:", new_density, "Velocity: ", new_vel_x, "Internal energy:", new_u)
                sys.exit(1)
    
    def initialise_conserved_quantities(self):
        self.cqs["mass"] = self.flow_state.fluid_state.rho
        self.cqs["xMom"] = self.flow_state.fluid_state.rho * self.flow_state.vel_x
        self.cqs["energy"] = self.flow_state.fluid_state.rho * \
                                                    (self.flow_state.fluid_state.u + 0.5 * self.flow_state.vel_x ** 2)

    def max_allowable_dt(self, cfl):
        return cfl * self.geo["dx"] / (abs(self.flow_state.vel_x) + self.flow_state.fluid_state.a)
    
    def complete_cell_methods(self, **kwargs):
        pass
    
    def decode_to_primative_properties_after_interface_methods(self):
        self.decode_to_primative_properties()

    def decode_to_primative_properties_after_cell_methods(self):
        pass